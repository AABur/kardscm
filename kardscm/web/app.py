"""FastAPI app for the local kardscm webUI."""

from __future__ import annotations

import logging
import webbrowser
from contextlib import closing
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from kardscm.config import LanguageConfig, get_language_config
from kardscm.constants import (
    DEFAULT_DB_PATH,
    KNOWN_ABILITIES,
    KNOWN_EXTRA_ABILITIES,
    RARITY_MAX_QUANTITY,
)
from kardscm.helpers import extract_locale
from kardscm.storage.backup import backup_database
from kardscm.storage.database import (
    get_card_quantity_by_id,
    get_connection,
    initialize_schema,
    update_card_quantity_by_id,
)
from kardscm.web.constants import (
    EDIT_MODE_COOKIE,
    FACTIONS,
    KREDITS_RANGE,
    RARITIES,
    SETS,
    TYPES,
)
from kardscm.web.deps import (
    _fetch_card,
    _is_edit_mode,
    _open_conn,
    _total_card_count,
    card_filters_dep,
)
from kardscm.web.queries import ALLOWED_SORT_COLUMNS, CardFilters, query_cards
from kardscm.web.routes_export import create_export_router
from kardscm.web.routes_sync import create_sync_router
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

    app = FastAPI(title="kardscm webUI", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    sync_router, sync_sessions = create_sync_router(templates, cfg, str(db_path_resolved))
    app.include_router(sync_router)
    export_router = create_export_router(templates, cfg, str(db_path_resolved))
    app.include_router(export_router)
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
        from kardscm.web.admin import create_admin_router

        admin_router = create_admin_router(templates, cfg, str(db_path_resolved))
        app.include_router(admin_router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


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
