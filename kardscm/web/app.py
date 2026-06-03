"""FastAPI app for the local kardscm webUI."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
import webbrowser
from collections.abc import Mapping
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

from kardscm.commands import apply_sync_changes, export_collection, fetch_and_compute_diff
from kardscm.config import LanguageConfig, get_language_config
from kardscm.constants import (
    DEFAULT_DB_PATH,
    KNOWN_ABILITIES,
    KNOWN_EXTRA_ABILITIES,
    RARITY_MAX_QUANTITY,
)
from kardscm.diff import is_empty
from kardscm.helpers import extract_locale
from kardscm.storage.backup import backup_database
from kardscm.storage.database import (
    get_card_quantity_by_id,
    get_connection,
    initialize_schema,
    update_card_admin,
    update_card_quantity_by_id,
)
from kardscm.web.constants import (
    _ADMIN_FORM_FIELDS,
    EDIT_MODE_COOKIE,
    EXPORT_MIME_TYPES,
    FACTIONS,
    KREDITS_RANGE,
    RARITIES,
    SETS,
    TYPES,
)
from kardscm.web.deps import (
    SyncSession,
    _decoded_locale_value,
    _fetch_card,
    _is_edit_mode,
    _open_conn,
    _total_card_count,
    card_filters_dep,
)
from kardscm.web.queries import ALLOWED_SORT_COLUMNS, CardFilters, query_cards
from kardscm.web.translate import to_view

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


def create_app(
    db_path: str | Path,
    lang_config: LanguageConfig | None = None,
    *,
    admin: bool = False,
    backup_path: Path | None = None,
) -> FastAPI:
    """Build a FastAPI app bound to the given DB path and language config.

    Args:
        db_path: Path to the SQLite collection database.
        lang_config: Active language configuration; defaults to English.
        admin: If True, register admin-only edit routes and force edit_mode on.
        backup_path: Path of the auto-backup created before admin start;
            displayed in the admin banner. Pass when admin=True.
    """
    cfg = lang_config or get_language_config()
    db_path_resolved = Path(db_path)
    edit_snapshot: dict[str, int] = {}
    sync_sessions: dict[str, SyncSession] = {}

    app = FastAPI(title="kardscm webUI", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals["fallback_warnings"] = cfg.fallback_warnings
    templates.env.globals["admin"] = admin
    templates.env.globals["backup_path"] = str(backup_path) if backup_path else ""
    templates.env.globals["rarity_max_quantity"] = RARITY_MAX_QUANTITY
    templates.env.filters["card_title"] = lambda raw: extract_locale(
        raw, cfg.locale_key, default=str(raw or ""), en_fallback=True
    )

    def render_table(
        request: Request,
        filters: CardFilters,
        sort: str,
        direction: str,
        template: str,
    ) -> HTMLResponse:
        edit_mode = _is_edit_mode(request, admin=admin)
        with closing(_open_conn(db_path_resolved)) as conn:
            rows = query_cards(conn, filters, sort, direction, cfg.locale_key)
            total = _total_card_count(conn)
        cards = [to_view(row, cfg) for row in rows]
        return templates.TemplateResponse(
            request,
            template,
            {
                "cards": cards,
                "shown": len(cards),
                "total": total,
                "sort": sort if sort in ALLOWED_SORT_COLUMNS else "faction",
                "direction": "desc" if direction.lower() == "desc" else "asc",
                "filters": filters,
                "facets": {
                    "factions": [(f, cfg.faction_names.get(f, f)) for f in FACTIONS],
                    "types": [(t, cfg.type_names.get(t, t)) for t in TYPES],
                    "rarities": [(r, cfg.rarity_names.get(r, r)) for r in RARITIES],
                    "sets": [(s, cfg.set_names.get(s, s)) for s in SETS],
                    "kredits": KREDITS_RANGE,
                    "abilities": [(a, cfg.ability_names.get(a, a)) for a in KNOWN_ABILITIES],
                    "extra_abilities": [
                        (a, cfg.extra_ability_names.get(a, a)) for a in KNOWN_EXTRA_ABILITIES
                    ],
                },
                "headers": cfg.export_headers,
                "ui": cfg.ui_strings,
                "lang": cfg.code,
                "edit_mode": edit_mode,
            },
        )

    @app.get("/", response_class=HTMLResponse)
    def index(
        request: Request,
        filters: CardFilters = Depends(card_filters_dep),
        sort: str = Query(default="faction"),
        direction: str = Query(default="asc"),
    ) -> HTMLResponse:
        return render_table(request, filters, sort, direction, "index.html")

    @app.get("/cards", response_class=HTMLResponse)
    def cards_partial(
        request: Request,
        filters: CardFilters = Depends(card_filters_dep),
        sort: str = Query(default="faction"),
        direction: str = Query(default="asc"),
    ) -> HTMLResponse:
        return render_table(request, filters, sort, direction, "_table.html")

    @app.post("/start-edit")
    def start_edit(request: Request) -> Response:
        with closing(_open_conn(db_path_resolved)) as conn:
            rows = conn.execute("SELECT cardId, quantity FROM cards").fetchall()
        edit_snapshot.clear()
        edit_snapshot.update({row[0]: row[1] for row in rows})
        target = request.headers.get("HX-Current-URL") or request.headers.get("referer") or "/"
        response = Response(content="", status_code=200)
        response.set_cookie(EDIT_MODE_COOKIE, "1", samesite="lax", httponly=False)
        response.headers["HX-Redirect"] = target
        return response

    @app.post("/request-save", response_class=HTMLResponse)
    def request_save(request: Request) -> Response:
        with closing(_open_conn(db_path_resolved)) as conn:
            rows = conn.execute("SELECT cardId, title, quantity FROM cards").fetchall()
        target = request.headers.get("HX-Current-URL") or "/"
        if not edit_snapshot:
            response = Response(content="", status_code=200)
            response.set_cookie(EDIT_MODE_COOKIE, "0", samesite="lax", httponly=False)
            response.headers["HX-Redirect"] = target
            return response
        changes = []
        for row in rows:
            card_id, title_raw, current_qty = row[0], row[1], row[2]
            original_qty = edit_snapshot.get(card_id)
            if original_qty is None or current_qty == original_qty:
                continue
            title = extract_locale(title_raw, cfg.locale_key, default=card_id)
            changes.append({"title": title, "qty_before": original_qty, "qty_after": current_qty})
        if not changes:
            response = Response(content="", status_code=200)
            response.set_cookie(EDIT_MODE_COOKIE, "0", samesite="lax", httponly=False)
            response.headers["HX-Redirect"] = target
            return response
        return templates.TemplateResponse(
            request, "_save_modal.html", {"changes": changes, "ui": cfg.ui_strings}
        )

    @app.post("/confirm-save")
    def confirm_save(request: Request) -> Response:
        edit_snapshot.clear()
        target = request.headers.get("HX-Current-URL") or request.headers.get("referer") or "/"
        response = Response(content="", status_code=200)
        response.set_cookie(EDIT_MODE_COOKIE, "0", samesite="lax", httponly=False)
        response.headers["HX-Redirect"] = target
        return response

    @app.post("/undo-save")
    def undo_save(request: Request) -> Response:
        if edit_snapshot:
            with closing(_open_conn(db_path_resolved)) as conn:
                for card_id, qty in edit_snapshot.items():
                    update_card_quantity_by_id(conn, card_id, qty)
                conn.commit()
        edit_snapshot.clear()
        target = request.headers.get("HX-Current-URL") or request.headers.get("referer") or "/"
        response = Response(content="", status_code=200)
        response.set_cookie(EDIT_MODE_COOKIE, "0", samesite="lax", httponly=False)
        response.headers["HX-Redirect"] = target
        return response

    @app.post("/close-save-modal", response_class=HTMLResponse)
    def close_save_modal() -> HTMLResponse:
        return HTMLResponse("")

    @app.post("/cards/{card_id}/quantity", response_class=HTMLResponse)
    def update_quantity(
        request: Request,
        card_id: str,
        quantity: int = Form(...),
    ) -> HTMLResponse:
        if quantity < 0:
            quantity = 0
        with closing(_open_conn(db_path_resolved)) as conn:
            row = conn.execute("SELECT rarity FROM cards WHERE cardId = ?", (card_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="card not found")
            rarity_raw = row[0] or ""
            max_qty = RARITY_MAX_QUANTITY.get(rarity_raw, 4)
            quantity = min(quantity, max_qty)
            update_card_quantity_by_id(conn, card_id, quantity)
            conn.commit()
            persisted = get_card_quantity_by_id(conn, card_id)
        edit_mode = _is_edit_mode(request, admin=admin)
        return templates.TemplateResponse(
            request,
            "_qty_cell.html",
            {
                "card": {"cardId": card_id, "quantity": persisted, "rarity_raw": rarity_raw},
                "edit_mode": edit_mode,
            },
        )

    @app.get("/cards/{card_id}", response_class=HTMLResponse)
    def card_modal(request: Request, card_id: str) -> HTMLResponse:
        with closing(_open_conn(db_path_resolved)) as conn:
            row = _fetch_card(conn, card_id)
        if row is None:
            raise HTTPException(status_code=404, detail="card not found")
        card = to_view(row, cfg)
        return templates.TemplateResponse(
            request, "_modal.html", {"card": card, "ui": cfg.ui_strings}
        )

    if admin:

        @app.get("/admin/cards/{card_id}/edit", response_class=HTMLResponse)
        def admin_edit_form(request: Request, card_id: str) -> HTMLResponse:
            with closing(_open_conn(db_path_resolved)) as conn:
                row = _fetch_card(conn, card_id)
            if row is None:
                raise HTTPException(status_code=404, detail="card not found")
            row["title_localized"] = _decoded_locale_value(row.get("title"), cfg.locale_key)
            row["text_localized"] = _decoded_locale_value(row.get("text"), cfg.locale_key)
            return templates.TemplateResponse(
                request,
                "_admin_form.html",
                {
                    "card": row,
                    "ui": cfg.ui_strings,
                    "lang": cfg.code,
                    "locale_key": cfg.locale_key,
                    "abilities": KNOWN_ABILITIES,
                    "extra_abilities": KNOWN_EXTRA_ABILITIES,
                    "factions": FACTIONS,
                    "types": TYPES,
                    "rarities": RARITIES,
                    "sets": SETS,
                    "ability_labels": cfg.ability_names,
                    "extra_ability_labels": cfg.extra_ability_names,
                    "faction_labels": cfg.faction_names,
                    "type_labels": cfg.type_names,
                    "rarity_labels": cfg.rarity_names,
                    "set_labels": cfg.set_names,
                },
            )

        @app.post("/admin/cards/{card_id}", response_class=HTMLResponse)
        async def admin_save(request: Request, card_id: str) -> HTMLResponse:
            form = await request.form()
            try:
                fields = _parse_admin_form(form)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            with closing(_open_conn(db_path_resolved)) as conn:
                try:
                    update_card_admin(conn, card_id, fields, cfg.locale_key)
                except KeyError as exc:
                    raise HTTPException(status_code=404, detail=str(exc)) from exc
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc
                conn.commit()
                row = _fetch_card(conn, card_id)
            assert row is not None
            card = to_view(row, cfg)
            return templates.TemplateResponse(
                request,
                "_table_row.html",
                {
                    "card": card,
                    "edit_mode": True,
                    "admin": True,
                    "include_oob_modal_clear": True,
                },
            )

    @app.get("/sync/modal", response_class=HTMLResponse)
    def sync_confirm_modal(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "_sync_confirm.html", {"ui": cfg.ui_strings})

    @app.post("/sync/start", response_class=HTMLResponse)
    async def sync_start(request: Request) -> HTMLResponse:
        report, new_cards, timestamp = await asyncio.to_thread(
            fetch_and_compute_diff, str(db_path_resolved), cfg
        )
        if is_empty(report):
            await asyncio.to_thread(
                apply_sync_changes,
                str(db_path_resolved),
                new_cards,
                report,
                cfg,
                timestamp,
            )
            return templates.TemplateResponse(request, "_sync_empty.html", {"ui": cfg.ui_strings})
        sync_id = uuid.uuid4().hex
        sync_sessions[sync_id] = SyncSession(
            report=report, new_cards=new_cards, timestamp=timestamp
        )
        return templates.TemplateResponse(
            request,
            "_sync_diff.html",
            {
                "ui": cfg.ui_strings,
                "sync_id": sync_id,
                "report": report,
                "diff_headers": cfg.diff_headers,
                "faction_names": cfg.faction_names,
                "ability_names": cfg.ability_names,
            },
        )

    @app.post("/sync/apply/{sync_id}")
    async def sync_apply(sync_id: str) -> Response:
        session = sync_sessions.pop(sync_id, None)
        if session is None:
            raise HTTPException(status_code=404, detail="sync session not found")
        await asyncio.to_thread(
            apply_sync_changes,
            str(db_path_resolved),
            session.new_cards,
            session.report,
            cfg,
            session.timestamp,
        )
        response = Response(content="", status_code=200)
        response.headers["HX-Redirect"] = "/"
        return response

    @app.post("/sync/cancel/{sync_id}")
    def sync_cancel(sync_id: str) -> Response:
        sync_sessions.pop(sync_id, None)
        return Response(content="", status_code=200)

    @app.get("/export/modal", response_class=HTMLResponse)
    def export_modal(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "_export_modal.html", {"ui": cfg.ui_strings})

    @app.get("/export/{fmt}")
    async def export_download(fmt: str) -> FileResponse:
        if fmt not in EXPORT_MIME_TYPES:
            raise HTTPException(status_code=400, detail=f"unsupported format: {fmt}")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{fmt}")
        tmp.close()
        try:
            await asyncio.to_thread(
                export_collection,
                fmt,
                tmp.name,
                str(db_path_resolved),
                lang=cfg.code,
            )
        except SystemExit as exc:
            os.unlink(tmp.name)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        filename = f"kards_collection_{cfg.code}_{timestamp}.{fmt}"
        return FileResponse(
            tmp.name,
            media_type=EXPORT_MIME_TYPES[fmt],
            filename=filename,
            background=BackgroundTask(os.unlink, tmp.name),
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _parse_admin_form(form: Mapping[str, Any]) -> dict:
    """Parse the admin edit form into a fields dict for update_card_admin.

    Validates ranges and categorical values. Empty number inputs map to None.
    Title is required non-empty; text may be empty.

    Args:
        form: A Starlette FormData (or any mapping-like object exposing .get).
            Values may be ``str`` or ``UploadFile``; non-string values for the
            keys this parser reads are coerced via ``str()`` where needed.
    """
    fields: dict = {}

    # Categorical
    for key, allowed in (
        ("faction", FACTIONS),
        ("type", TYPES),
        ("rarity", RARITIES),
        ("set", SETS),
    ):
        value = form.get(key)
        if value is None:
            continue
        if value not in allowed:
            raise ValueError(f"invalid {key}: {value}")
        fields[key] = value

    # Integers (kredits required >=0; others may be None on empty)
    for key in ("kredits", "attack", "defense", "operationCost"):
        raw = form.get(key)
        if raw is None or raw == "":
            if key == "kredits":
                continue
            fields[key] = None
            continue
        try:
            num = int(raw)
        except ValueError as exc:
            raise ValueError(f"{key} must be an integer") from exc
        if num < 0:
            raise ValueError(f"{key} must be >= 0")
        fields[key] = num

    # Boolean reserved (checkbox is absent when unchecked)
    fields["reserved"] = 1 if form.get("reserved") in ("1", "on", "true") else 0

    # Abilities (binary checkboxes)
    for ability in KNOWN_ABILITIES:
        col = f"ability_{ability}"
        fields[col] = 1 if form.get(col) in ("1", "on", "true") else 0
    for ability in KNOWN_EXTRA_ABILITIES:
        col = f"extra_ability_{ability}"
        fields[col] = 1 if form.get(col) in ("1", "on", "true") else 0

    # Localized title/text (active locale)
    title = form.get("title_localized")
    if title is not None:
        title_str = str(title).strip()
        if not title_str:
            raise ValueError("title must not be empty")
        fields["title"] = title_str

    text = form.get("text_localized")
    if text is not None:
        # Empty text is allowed.
        fields["text"] = str(text)

    # Sanity: nothing outside the documented allow-list.
    for key in fields:
        if key not in _ADMIN_FORM_FIELDS:
            raise ValueError(f"unsupported admin field: {key}")
    return fields


def _resolve_lang(lang_code: str | None) -> LanguageConfig | None:
    """Map a CLI language code to a LanguageConfig (None ⇒ default English)."""
    if not lang_code:
        return None
    return get_language_config(lang_code)


def run(
    db_path: str | Path | None = None,
    port: int = 8765,
    open_browser: bool = True,
    host: str = "127.0.0.1",
    lang: str | None = None,
    admin: bool = False,
) -> None:
    """Start uvicorn after validating the DB exists and is non-empty."""
    # Lazy: uvicorn is only needed when the user actually starts the web server,
    # not for `kardscm --help` or any non-web subcommand.
    import uvicorn

    actual_db = Path(db_path) if db_path else Path(DEFAULT_DB_PATH)
    if not actual_db.exists():
        raise SystemExit(f"Database not found at {actual_db}. Run `kardscm sync` first.")

    with closing(get_connection(actual_db)) as conn:
        initialize_schema(conn)
        if _total_card_count(conn) == 0:
            raise SystemExit("Card database is empty. Run `kardscm sync` first to populate it.")

    if admin and host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit(
            f"Admin mode is not allowed with --host {host!r}. "
            "Bind to 127.0.0.1 (default) to use --admin."
        )

    backup_path: Path | None = None
    if admin:
        backup_path = backup_database(actual_db)
        print(f"ADMIN MODE — DB backed up to {backup_path}")

    app = create_app(
        actual_db,
        lang_config=_resolve_lang(lang),
        admin=admin,
        backup_path=backup_path,
    )
    url = f"http://{host}:{port}"
    print(f"kardscm webUI listening on {url}")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to open browser: %s", exc)
    uvicorn.run(app, host=host, port=port, log_level="info")
