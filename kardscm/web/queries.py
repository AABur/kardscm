"""SQL query builder for the webUI card table.

Builds parametrized SQL with AND-combined filters and a whitelisted sort
column. The query targets the existing `cards` table; no schema changes.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from kardscm.constants import KNOWN_ABILITIES

ALLOWED_SORT_COLUMNS: frozenset[str] = frozenset(
    {
        "faction",
        "title",
        "type",
        "rarity",
        "set",
        "quantity",
        "kredits",
        "operationCost",
        "attack",
        "defense",
    }
)

_ABILITY_COLS = ", ".join(f"ability_{a}" for a in KNOWN_ABILITIES)
SELECT_COLUMNS = (
    'cardId, importId, imageUrl, thumbUrl, faction, type, rarity, "set", '
    f"title, text, kredits, attack, defense, {_ABILITY_COLS}, operationCost, "
    "reserved, image, can_create, exile, quantity, updated_at"
)


@dataclass(frozen=True)
class CardFilters:
    """Filter state for the webUI card table."""

    factions: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)
    rarities: list[str] = field(default_factory=list)
    sets: list[str] = field(default_factory=list)
    kredits: list[int] = field(default_factory=list)
    abilities: list[str] = field(default_factory=list)
    text_query: str = ""
    include_spawnable: bool = False
    include_reserved: bool = False
    owned_only: bool = False


def _title_expr(locale_key: str) -> str:
    """SQL expression that extracts the localized title from the title JSON."""
    return f"json_extract(title, '$.\"{locale_key}\"')"


def _build_where(filters: CardFilters, locale_key: str) -> tuple[list[str], list[object]]:
    where: list[str] = []
    params: list[object] = []

    if not filters.include_reserved:
        where.append("reserved = 0")
    if not filters.include_spawnable:
        where.append("(can_create IS NULL OR can_create = '[]')")

    if filters.factions:
        placeholders = ",".join("?" for _ in filters.factions)
        where.append(f"faction IN ({placeholders})")
        params.extend(filters.factions)

    if filters.types:
        placeholders = ",".join("?" for _ in filters.types)
        where.append(f"type IN ({placeholders})")
        params.extend(filters.types)

    if filters.rarities:
        placeholders = ",".join("?" for _ in filters.rarities)
        where.append(f"rarity IN ({placeholders})")
        params.extend(filters.rarities)

    if filters.sets:
        placeholders = ",".join("?" for _ in filters.sets)
        where.append(f'"set" IN ({placeholders})')
        params.extend(filters.sets)

    if filters.kredits:
        placeholders = ",".join("?" for _ in filters.kredits)
        where.append(f"kredits IN ({placeholders})")
        params.extend(filters.kredits)

    if filters.abilities:
        # Whitelist against KNOWN_ABILITIES — column names cannot be
        # parameterized so unsafe input must be rejected before string
        # interpolation. OR semantics: card matches if ANY selected
        # ability is set.
        valid = [a for a in filters.abilities if a in KNOWN_ABILITIES]
        if valid:
            clauses = " OR ".join(f"ability_{a} = 1" for a in valid)
            where.append(f"({clauses})")

    if filters.text_query:
        text_expr = f"json_extract(text, '$.\"{locale_key}\"')"
        where.append(
            f"(LOWER({_title_expr(locale_key)}) LIKE LOWER(?) OR LOWER({text_expr}) LIKE LOWER(?))"
        )
        params.extend([f"%{filters.text_query}%", f"%{filters.text_query}%"])

    if filters.owned_only:
        where.append("quantity > 0")

    return where, params


def _build_order_by(sort_col: str, sort_dir: str, locale_key: str) -> str:
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    if sort_col not in ALLOWED_SORT_COLUMNS:
        # default: faction, then title
        return f"faction ASC, {_title_expr(locale_key)} COLLATE NOCASE ASC"

    if sort_col == "title":
        return f"{_title_expr(locale_key)} COLLATE NOCASE {direction}"

    quoted = f'"{sort_col}"' if sort_col == "set" else sort_col
    return f"{quoted} {direction}"


def build_query(
    filters: CardFilters,
    sort_col: str = "faction",
    sort_dir: str = "asc",
    locale_key: str = "en-EN",
) -> tuple[str, tuple[object, ...]]:
    """Build a parametrized SELECT for the card table."""
    where, params = _build_where(filters, locale_key)
    order_by = _build_order_by(sort_col, sort_dir, locale_key)

    where_clause = f" WHERE {' AND '.join(where)}" if where else ""
    sql = f"SELECT {SELECT_COLUMNS} FROM cards{where_clause} ORDER BY {order_by}"
    return sql, tuple(params)


def query_cards(
    conn: sqlite3.Connection,
    filters: CardFilters,
    sort_col: str = "faction",
    sort_dir: str = "asc",
    locale_key: str = "en-EN",
) -> list[dict]:
    """Run a filtered/sorted SELECT and return rows as plain dicts."""
    sql, params = build_query(filters, sort_col, sort_dir, locale_key)
    prev_factory = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.row_factory = prev_factory
