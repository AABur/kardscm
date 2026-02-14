"""SQLite storage helpers for card collections."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

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
                _parse_int(card.get("Quantity")),
                _parse_int(card.get("Credits")),
                _parse_int(card.get("Attack")),
                _parse_int(card.get("Defense")),
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


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


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


def _row_to_card(row: tuple) -> dict[str, str]:
    return {
        "CardId": _to_text(row[0]),
        "Name": _to_text(row[1]),
        "Nation": _to_text(row[2]),
        "Type": _to_text(row[3]),
        "Rarity": _to_text(row[4]),
        "Abilities": _to_text(row[5]),
        "Set": _to_text(row[6]),
        "Quantity": _to_text(row[7]),
        "Credits": _to_text(row[8]),
        "Attack": _to_text(row[9]),
        "Defense": _to_text(row[10]),
        "Description": _to_text(row[11]),
    }


def _to_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)
