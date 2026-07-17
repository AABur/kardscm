"""Shared FastAPI dependencies and helpers for the kardscm web UI."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from fastapi import Query, Request

from kardscm.helpers import extract_locale
from kardscm.models import CardDict, DiffReport
from kardscm.storage.database import get_connection, initialize_schema
from kardscm.web.constants import EDIT_MODE_COOKIE
from kardscm.web.queries import SELECT_COLUMNS, CardFilters


@dataclass
class SyncSession:
    """In-memory state passed from /sync/start to /sync/apply.

    Holds the diff preview and the cards needed to apply the change so
    the second phase can reuse the already-fetched data without hitting
    the API a second time.
    """

    report: DiffReport
    new_cards: list[CardDict]
    timestamp: str


def card_filters_dep(
    factions: list[str] = Query(default=[]),
    types: list[str] = Query(default=[]),
    rarities: list[str] = Query(default=[]),
    sets: list[str] = Query(default=[]),
    kredits: list[int] = Query(default=[]),
    abilities: list[str] = Query(default=[]),
    extra_abilities: list[str] = Query(default=[]),
    q: str = Query(default=""),
    spawnable: bool = Query(default=False),
    reserved: bool = Query(default=False),
    exiles: list[str] = Query(default=[]),
    owned: bool = Query(default=False),
) -> CardFilters:
    """FastAPI dependency that builds CardFilters from query string params.

    `exiles` arrives as a list because the exile toggle defaults to ON: the
    template pairs a hidden ``exiles=false`` with the checkbox's ``exiles=true``
    so an unchecked box still submits a value. Absent entirely (a bare page
    load with no form) means "use the default", which is ON.
    """
    return CardFilters(
        factions=factions,
        types=types,
        rarities=rarities,
        sets=sets,
        kredits=kredits,
        abilities=abilities,
        extra_abilities=extra_abilities,
        text_query=q.strip(),
        include_spawnable=spawnable,
        include_reserved=reserved,
        include_exiles=("true" in exiles) if exiles else True,
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
            f"SELECT {SELECT_COLUMNS} FROM cards WHERE cardId = ?", (card_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.row_factory = prev


def _is_edit_mode(request: Request, *, admin: bool) -> bool:
    if admin:
        return True
    return bool(request.cookies.get(EDIT_MODE_COOKIE) == "1")


def _decoded_locale_value(raw: object, locale_key: str) -> str:
    return extract_locale(raw, locale_key)
