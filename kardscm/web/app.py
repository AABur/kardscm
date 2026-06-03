"""FastAPI app for the local kardscm webUI."""

from __future__ import annotations

import logging
import webbrowser
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from kardscm.config import LanguageConfig, get_language_config
from kardscm.constants import DEFAULT_DB_PATH, RARITY_MAX_QUANTITY
from kardscm.helpers import extract_locale
from kardscm.storage.backup import backup_database
from kardscm.storage.database import (
    get_connection,
    initialize_schema,
)
from kardscm.web.admin import create_admin_router
from kardscm.web.deps import _total_card_count
from kardscm.web.routes_collection import create_collection_router
from kardscm.web.routes_export import create_export_router
from kardscm.web.routes_sync import create_sync_router

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

    app = FastAPI(title="kardscm webUI", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    sync_router, sync_sessions = create_sync_router(templates, cfg, str(db_path_resolved))
    app.include_router(sync_router)
    export_router = create_export_router(templates, cfg, str(db_path_resolved))
    app.include_router(export_router)
    collection_router, edit_snapshot = create_collection_router(
        templates, cfg, str(db_path_resolved), admin
    )
    app.include_router(collection_router)

    if admin:
        admin_router = create_admin_router(templates, cfg, str(db_path_resolved))
        app.include_router(admin_router)

    templates.env.globals["fallback_warnings"] = cfg.fallback_warnings
    templates.env.globals["admin"] = admin
    templates.env.globals["backup_path"] = str(backup_path) if backup_path else ""
    templates.env.globals["rarity_max_quantity"] = RARITY_MAX_QUANTITY
    templates.env.filters["card_title"] = lambda raw: extract_locale(
        raw, cfg.locale_key, default=str(raw or ""), en_fallback=True
    )

    return app


def _resolve_lang(lang_code: str | None) -> LanguageConfig | None:
    """Map a CLI language code to a LanguageConfig (None => default English)."""
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
