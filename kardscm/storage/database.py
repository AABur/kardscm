"""SQLite storage helpers for card collections."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from kardscm.helpers import parse_int, to_text
from kardscm.models import DeckCardEntry, ParsedDeck

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

CREATE TABLE IF NOT EXISTS decks (
    deck_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    major_power TEXT NOT NULL,
    ally TEXT,
    hq TEXT,
    deck_code TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deck_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    cost INTEGER NOT NULL,
    FOREIGN KEY (deck_id) REFERENCES decks(deck_id) ON DELETE CASCADE,
    FOREIGN KEY (card_id) REFERENCES cards(card_id),
    UNIQUE(deck_id, card_id)
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
            abilities = excluded.abilities,
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


def find_card_id_by_nation_name(conn: sqlite3.Connection, nation: str, name: str) -> str | None:
    """Find card_id by nation and name.

    Args:
        conn: SQLite connection instance.
        nation: Card nation (e.g. 'Soviet').
        name: Card name.

    Returns:
        card_id string or None if not found.
    """
    row = conn.execute(
        "SELECT card_id FROM cards WHERE nation = ? AND name = ?",
        (nation, name),
    ).fetchone()
    return row[0] if row else None


def insert_deck(conn: sqlite3.Connection, deck: ParsedDeck) -> int:
    """Insert deck metadata into the database.

    Args:
        conn: SQLite connection instance.
        deck: Parsed deck data.

    Returns:
        The new deck_id.
    """
    cursor = conn.execute(
        "INSERT INTO decks (name, major_power, ally, hq, deck_code) VALUES (?, ?, ?, ?, ?)",
        (deck["name"], deck["major_power"], deck["ally"], deck["hq"], deck["deck_code"]),
    )
    return cursor.lastrowid  # type: ignore[return-value]


def insert_deck_cards(
    conn: sqlite3.Connection,
    deck_id: int,
    cards: list[DeckCardEntry],
    nation_map: dict[str, str],
) -> None:
    """Insert deck cards, linking each to its card_id.

    Args:
        conn: SQLite connection instance.
        deck_id: ID of the deck.
        cards: List of DeckCardEntry dicts.
        nation_map: Mapping from deck nation key to DB nation name.

    Raises:
        ValueError: If a card is not found in the collection.
    """
    for card in cards:
        db_nation = nation_map.get(card["nation"], card["nation"])
        card_id = find_card_id_by_nation_name(conn, db_nation, card["name"])
        if card_id is None:
            msg = f"Card not found: {db_nation} / {card['name']}"
            raise ValueError(msg)
        conn.execute(
            "INSERT INTO deck_cards (deck_id, card_id, quantity, cost) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(deck_id, card_id) DO UPDATE SET "
            "quantity = excluded.quantity, cost = excluded.cost",
            (deck_id, card_id, card["quantity"], card["cost"]),
        )


def fetch_all_decks(conn: sqlite3.Connection) -> list[dict]:
    """Fetch all decks from the database.

    Args:
        conn: SQLite connection instance.

    Returns:
        List of deck metadata dicts.
    """
    cursor = conn.execute(
        "SELECT deck_id, name, major_power, ally, hq, deck_code, imported_at "
        "FROM decks ORDER BY deck_id"
    )
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def find_deck_by_name(conn: sqlite3.Connection, name: str) -> dict | None:
    """Find a deck by name.

    Args:
        conn: SQLite connection instance.
        name: Deck name to search for.

    Returns:
        Deck metadata dict or None if not found.
    """
    cursor = conn.execute(
        "SELECT deck_id, name, major_power, ally, hq, deck_code, imported_at "
        "FROM decks WHERE name = ?",
        (name,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def fetch_deck_cards(conn: sqlite3.Connection, deck_id: int) -> list[dict]:
    """Fetch deck cards with full card info from the collection.

    Args:
        conn: SQLite connection instance.
        deck_id: ID of the deck.

    Returns:
        List of card dicts with deck_quantity and deck_cost added.
    """
    cursor = conn.execute(
        """
        SELECT
            c.nation, c.name, c.type, c.rarity, c.abilities,
            c.set_name, c.credits, c.attack, c.defense, c.description,
            dc.quantity AS deck_quantity, dc.cost AS deck_cost
        FROM deck_cards dc
        JOIN cards c ON dc.card_id = c.card_id
        WHERE dc.deck_id = ?
        ORDER BY c.nation, dc.cost, c.name
        """,
        (deck_id,),
    )
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
