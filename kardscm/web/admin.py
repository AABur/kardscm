"""Admin route handlers for the kardscm webUI."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from kardscm.config import LanguageConfig
from kardscm.constants import KNOWN_ABILITIES, KNOWN_EXTRA_ABILITIES
from kardscm.storage.database import update_card_admin
from kardscm.web.constants import (
    _ADMIN_FORM_FIELDS,
    FACTIONS,
    RARITIES,
    SETS,
    TYPES,
)
from kardscm.web.deps import (
    _decoded_locale_value,
    _fetch_card,
    _open_conn,
)
from kardscm.web.translate import to_view


def create_admin_router(
    templates: Jinja2Templates,
    cfg: LanguageConfig,
    db_path: str,
) -> APIRouter:
    """Create the admin APIRouter with edit form and save routes.

    Args:
        templates: Shared Jinja2Templates instance.
        cfg: Active language configuration.
        db_path: Path to the SQLite database as a string.
    """
    db_path_resolved = Path(db_path)

    router = APIRouter()

    @router.get("/admin/cards/{card_id}/edit", response_class=HTMLResponse)
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

    @router.post("/admin/cards/{card_id}", response_class=HTMLResponse)
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

    return router


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
