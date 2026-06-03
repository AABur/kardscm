"""Export routes for the kardscm webUI."""

from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

from kardscm.commands import export_collection
from kardscm.config import LanguageConfig
from kardscm.web.constants import EXPORT_MIME_TYPES


def create_export_router(
    templates: Jinja2Templates,
    cfg: LanguageConfig,
    db_path: str,
) -> APIRouter:
    """Build an APIRouter with export route handlers bound to templates, cfg, and db_path.

    Args:
        templates: Jinja2Templates instance shared with the main app.
        cfg: Active language configuration.
        db_path: Resolved path to the SQLite collection database.
    """
    router = APIRouter()

    @router.get("/export/modal", response_class=HTMLResponse)
    def export_modal(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "_export_modal.html", {"ui": cfg.ui_strings})

    @router.get("/export/{fmt}")
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
                db_path,
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

    return router
