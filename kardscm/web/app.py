"""FastAPI app for the local kardscm webUI."""

from __future__ import annotations

import logging
import sqlite3
import webbrowser
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from kardscm.config import LanguageConfig, get_language_config
from kardscm.constants import DEFAULT_DB_PATH
from kardscm.locales import LANGUAGES
from kardscm.storage.database import (
    get_card_quantity_by_id,
    get_connection,
    initialize_schema,
    update_card_quantity_by_id,
)
from kardscm.web.queries import ALLOWED_SORT_COLUMNS, CardFilters, query_cards
from kardscm.web.translate import to_view

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

FACTIONS = ["Soviet", "USA", "Britain", "Germany", "Japan", "France", "Italy", "Poland", "Finland"]
TYPES = ["infantry", "tank", "artillery", "fighter", "bomber", "order", "countermeasure"]
RARITIES = ["Standard", "Limited", "Special", "Elite"]
SETS = [
    "Base",
    "Allegiance",
    "TheatersOfWar",
    "Breakthrough",
    "WorldAtWar",
    "CovertOps",
    "BloodAndIron",
    "Legions",
    "NavalWarfare",
    "Homefront",
    "WinterWar",
    "BrothersInArms",
    "Special",
    "OnlySpawnable",
]
KREDITS_RANGE = list(range(0, 11))

CARD_COLUMNS = (
    'cardId, importId, imageUrl, thumbUrl, faction, type, rarity, "set", '
    "title, text, kredits, attack, defense, attributes, operationCost, "
    "reserved, image, can_create, exile, quantity, updated_at"
)


def _read_filters(
    factions: list[str],
    types: list[str],
    rarities: list[str],
    sets: list[str],
    kredits: list[int],
    q: str,
    spawnable: bool,
    reserved: bool,
    owned: bool,
) -> CardFilters:
    return CardFilters(
        factions=factions,
        types=types,
        rarities=rarities,
        sets=sets,
        kredits=kredits,
        text_query=q.strip(),
        include_spawnable=spawnable,
        include_reserved=reserved,
        owned_only=owned,
    )


def _total_card_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM cards").fetchone()
    return int(row[0]) if row else 0


def _open_conn(db_path: str | Path) -> sqlite3.Connection:
    conn = get_connection(db_path)
    initialize_schema(conn)
    return conn


def _fetch_card(conn: sqlite3.Connection, card_id: str) -> dict | None:
    prev = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            f"SELECT {CARD_COLUMNS} FROM cards WHERE cardId = ?", (card_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.row_factory = prev


def create_app(db_path: str | Path, lang_config: LanguageConfig | None = None) -> FastAPI:
    """Build a FastAPI app bound to the given DB path and language config."""
    cfg = lang_config or get_language_config()
    db_path_resolved = Path(db_path)

    app = FastAPI(title="kardscm webUI", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals["fallback_warnings"] = cfg.fallback_warnings

    def render_table(
        request: Request,
        filters: CardFilters,
        sort: str,
        direction: str,
        template: str,
    ) -> HTMLResponse:
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
                },
                "headers": cfg.export_headers,
                "ui": cfg.ui_strings,
                "lang": cfg.code,
            },
        )

    @app.get("/", response_class=HTMLResponse)
    def index(
        request: Request,
        factions: list[str] = Query(default=[]),
        types: list[str] = Query(default=[]),
        rarities: list[str] = Query(default=[]),
        sets: list[str] = Query(default=[]),
        kredits: list[int] = Query(default=[]),
        q: str = Query(default=""),
        spawnable: bool = Query(default=False),
        reserved: bool = Query(default=False),
        owned: bool = Query(default=False),
        sort: str = Query(default="faction"),
        direction: str = Query(default="asc"),
    ) -> HTMLResponse:
        filters = _read_filters(
            factions, types, rarities, sets, kredits, q, spawnable, reserved, owned
        )
        return render_table(request, filters, sort, direction, "index.html")

    @app.get("/cards", response_class=HTMLResponse)
    def cards_partial(
        request: Request,
        factions: list[str] = Query(default=[]),
        types: list[str] = Query(default=[]),
        rarities: list[str] = Query(default=[]),
        sets: list[str] = Query(default=[]),
        kredits: list[int] = Query(default=[]),
        q: str = Query(default=""),
        spawnable: bool = Query(default=False),
        reserved: bool = Query(default=False),
        owned: bool = Query(default=False),
        sort: str = Query(default="faction"),
        direction: str = Query(default="asc"),
    ) -> HTMLResponse:
        filters = _read_filters(
            factions, types, rarities, sets, kredits, q, spawnable, reserved, owned
        )
        return render_table(request, filters, sort, direction, "_table.html")

    @app.post("/cards/{card_id}/quantity", response_class=HTMLResponse)
    def update_quantity(
        request: Request,
        card_id: str,
        quantity: int = Form(...),
    ) -> HTMLResponse:
        if quantity < 0:
            quantity = 0
        with closing(_open_conn(db_path_resolved)) as conn:
            exists = conn.execute("SELECT 1 FROM cards WHERE cardId = ?", (card_id,)).fetchone()
            if exists is None:
                raise HTTPException(status_code=404, detail="card not found")
            update_card_quantity_by_id(conn, card_id, quantity)
            conn.commit()
            persisted = get_card_quantity_by_id(conn, card_id)
        return templates.TemplateResponse(
            request,
            "_qty_cell.html",
            {"card": {"cardId": card_id, "quantity": persisted}},
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

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _resolve_lang(lang_code: str | None) -> LanguageConfig | None:
    """Map a CLI language code to a LanguageConfig, or None to fall back."""
    if not lang_code:
        return None
    code = lang_code.strip().lower()
    if code not in LANGUAGES:
        supported = ", ".join(sorted(LANGUAGES))
        raise SystemExit(f"Unsupported language '{lang_code}'. Supported: {supported}")
    return LANGUAGES[code]


def run(
    db_path: str | Path | None = None,
    port: int = 8765,
    open_browser: bool = True,
    host: str = "127.0.0.1",
    lang: str | None = None,
) -> None:
    """Start uvicorn after validating the DB exists and is non-empty."""
    import uvicorn

    actual_db = Path(db_path) if db_path else Path(DEFAULT_DB_PATH)
    if not actual_db.exists():
        raise SystemExit(f"Database not found at {actual_db}. Run `kardscm sync` first.")

    with closing(get_connection(actual_db)) as conn:
        initialize_schema(conn)
        if _total_card_count(conn) == 0:
            raise SystemExit("Card database is empty. Run `kardscm sync` first to populate it.")

    app = create_app(actual_db, lang_config=_resolve_lang(lang))
    url = f"http://{host}:{port}"
    print(f"kardscm webUI listening on {url}")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to open browser: %s", exc)
    uvicorn.run(app, host=host, port=port, log_level="info")
