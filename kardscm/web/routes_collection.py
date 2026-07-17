"""Collection route handlers for the kardscm webUI."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from kardscm.config import LanguageConfig
from kardscm.constants import (
    KNOWN_ABILITIES,
    KNOWN_EXTRA_ABILITIES,
)
from kardscm.helpers import extract_locale
from kardscm.storage.database import (
    get_card_quantity_by_id,
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
from kardscm.web.translate import to_view


def create_collection_router(
    templates: Jinja2Templates,
    cfg: LanguageConfig,
    db_path: str,
    admin: bool,
) -> tuple[APIRouter, dict]:
    """Create the collection APIRouter and its associated edit snapshot.

    Args:
        templates: Shared Jinja2Templates instance.
        cfg: Active LanguageConfig.
        db_path: Resolved path to the SQLite database (as a str).
        admin: If True, edit mode is treated as always-on.

    Returns:
        A tuple of (router, edit_snapshot) where edit_snapshot is the
        mutable dict used to track pre-edit quantities.
    """
    router = APIRouter()
    edit_snapshot: dict = {}
    db_path_resolved = Path(db_path)

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

    @router.get("/", response_class=HTMLResponse)
    def index(
        request: Request,
        filters: CardFilters = Depends(card_filters_dep),
        sort: str = Query(default="faction"),
        direction: str = Query(default="asc"),
    ) -> HTMLResponse:
        return render_table(request, filters, sort, direction, "index.html")

    @router.get("/cards", response_class=HTMLResponse)
    def cards_partial(
        request: Request,
        filters: CardFilters = Depends(card_filters_dep),
        sort: str = Query(default="faction"),
        direction: str = Query(default="asc"),
    ) -> HTMLResponse:
        return render_table(request, filters, sort, direction, "_table.html")

    @router.post("/start-edit")
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

    @router.post("/request-save", response_class=HTMLResponse)
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

    @router.post("/confirm-save")
    def confirm_save(request: Request) -> Response:
        edit_snapshot.clear()
        target = request.headers.get("HX-Current-URL") or request.headers.get("referer") or "/"
        response = Response(content="", status_code=200)
        response.set_cookie(EDIT_MODE_COOKIE, "0", samesite="lax", httponly=False)
        response.headers["HX-Redirect"] = target
        return response

    @router.post("/undo-save")
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

    @router.post("/close-save-modal", response_class=HTMLResponse)
    def close_save_modal() -> HTMLResponse:
        return HTMLResponse("")

    @router.post("/cards/{card_id}/quantity", response_class=HTMLResponse)
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

    @router.get("/cards/{card_id}", response_class=HTMLResponse)
    def card_modal(request: Request, card_id: str) -> HTMLResponse:
        with closing(_open_conn(db_path_resolved)) as conn:
            row = _fetch_card(conn, card_id)
        if row is None:
            raise HTTPException(status_code=404, detail="card not found")
        card = to_view(row, cfg)
        return templates.TemplateResponse(
            request, "_modal.html", {"card": card, "ui": cfg.ui_strings}
        )

    @router.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return router, edit_snapshot
