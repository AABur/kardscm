"""Sync route handlers for the kardscm webUI."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from kardscm.commands import apply_sync_changes, fetch_and_compute_diff
from kardscm.config import LanguageConfig
from kardscm.diff import is_empty
from kardscm.scraping import ApiContractDriftError
from kardscm.web.deps import SyncSession


def create_sync_router(
    templates: Jinja2Templates,
    cfg: LanguageConfig,
    db_path: str,
) -> tuple[APIRouter, dict[str, SyncSession]]:
    """Create the sync APIRouter and its associated session store.

    Args:
        templates: Shared Jinja2Templates instance.
        cfg: Active LanguageConfig.
        db_path: Resolved path to the SQLite database (as a str).

    Returns:
        A tuple of (router, sync_sessions) where sync_sessions is the shared
        dict used by all four sync route handlers.
    """
    router = APIRouter()
    sync_sessions: dict[str, SyncSession] = {}

    @router.get("/sync/modal", response_class=HTMLResponse)
    def sync_confirm_modal(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "_sync_confirm.html", {"ui": cfg.ui_strings})

    @router.post("/sync/start", response_class=HTMLResponse)
    async def sync_start(request: Request) -> HTMLResponse:
        try:
            report, new_cards, timestamp = await asyncio.to_thread(
                fetch_and_compute_diff, db_path, cfg
            )
        except ApiContractDriftError as exc:
            return templates.TemplateResponse(
                request,
                "_sync_drift.html",
                {
                    "ui": cfg.ui_strings,
                    "drift": exc.report,
                    "drift_count": exc.report.count(),
                },
            )
        if is_empty(report):
            await asyncio.to_thread(
                apply_sync_changes,
                db_path,
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

    @router.post("/sync/apply/{sync_id}")
    async def sync_apply(sync_id: str) -> Response:
        session = sync_sessions.pop(sync_id, None)
        if session is None:
            raise HTTPException(status_code=404, detail="sync session not found")
        await asyncio.to_thread(
            apply_sync_changes,
            db_path,
            session.new_cards,
            session.report,
            cfg,
            session.timestamp,
        )
        response = Response(content="", status_code=200)
        response.headers["HX-Redirect"] = "/"
        return response

    @router.post("/sync/cancel/{sync_id}")
    def sync_cancel(sync_id: str) -> Response:
        sync_sessions.pop(sync_id, None)
        return Response(content="", status_code=200)

    return router, sync_sessions
