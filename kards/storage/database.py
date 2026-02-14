"""SQLite storage helpers for card collections."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from kards.helpers import parse_int, to_text

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cards (
    card_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    nation TEXT,
    type TEXT,
    rarity TEXT,
    abilities TEXT,
    set_name TEXT,
    quantity INTEGER,
    credits INTEGER,
    attack INTEGER,
    defense INTEGER,
    description TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys enabled.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        SQLite connection instance.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Initialize database schema if missing.

    Args:
        conn: SQLite connection instance.
    """
    conn.executescript(SCHEMA_SQL)


def set_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set a metadata key value.

    Args:
        conn: SQLite connection instance.
        key: Metadata key.
        value: Metadata value.
    """
    conn.execute(
        "INSERT INTO metadata (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def upsert_cards(conn: sqlite3.Connection, cards: Iterable[dict[str, str]]) -> None:
    """Insert or update cards in the database.

    Args:
        conn: SQLite connection instance.
        cards: Iterable of card dictionaries.
    """
    rows: list[tuple] = []
    for card in cards:
        card_id = card.get("CardId")
        name = card.get("Name")
        if not card_id or not name:
            continue
        rows.append(
            (
                card_id,
                name,
                card.get("Nation"),
                card.get("Type"),
                card.get("Rarity"),
                card.get("Abilities") or None,
                card.get("Set"),
                parse_int(card.get("Quantity")),
                parse_int(card.get("Credits")),
                parse_int(card.get("Attack")),
                parse_int(card.get("Defense")),
                card.get("Description"),
            )
        )

    if not rows:
        return

    conn.executemany(
        """
        INSERT INTO cards (
            card_id,
            name,
            nation,
            type,
            rarity,
            abilities,
            set_name,
            quantity,
            credits,
            attack,
            defense,
            description,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(card_id) DO UPDATE SET
            name = excluded.name,
            nation = excluded.nation,
            type = excluded.type,
            rarity = excluded.rarity,
            set_name = excluded.set_name,
            credits = excluded.credits,
            attack = excluded.attack,
            defense = excluded.defense,
            description = excluded.description,
            updated_at = CURRENT_TIMESTAMP
        """,
        rows,
    )
    conn.commit()


def fetch_cards(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Fetch all cards from the database.

    Args:
        conn: SQLite connection instance.

    Returns:
        List of card dictionaries ready for export.
    """
    cursor = conn.execute(
        """
        SELECT
            card_id,
            name,
            nation,
            type,
            rarity,
            abilities,
            set_name,
            quantity,
            credits,
            attack,
            defense,
            description
        FROM cards
        ORDER BY name
        """
    )
    rows = cursor.fetchall()
    return [_row_to_card(row) for row in rows]


def update_quantity_by_nation_name(
    conn: sqlite3.Connection,
    updates: Iterable[tuple[str, str, int | None]],
) -> tuple[int, list[str]]:
    """Update card quantities by nation and name.

    Args:
        conn: SQLite connection instance.
        updates: Iterable of (nation, name, quantity) tuples.

    Returns:
        Tuple of (updated_count, not_found_list).
    """
    updated = 0
    not_found = []

    for nation, name, qty in updates:
        if not nation or not name:
            continue
        if qty is None:
            continue

        cursor = conn.execute(
            "UPDATE cards SET quantity = ? WHERE nation = ? AND name = ?",
            (qty, nation, name),
        )

        if cursor.rowcount > 0:
            updated += 1
        else:
            not_found.append(f"{nation} / {name}")

    conn.commit()
    return updated, not_found


_CARD_FIELDS = (
    "CardId",
    "Name",
    "Nation",
    "Type",
    "Rarity",
    "Abilities",
    "Set",
    "Quantity",
    "Credits",
    "Attack",
    "Defense",
    "Description",
)


def _row_to_card(row: tuple) -> dict[str, str]:
    return {field: to_text(val) for field, val in zip(_CARD_FIELDS, row)}
