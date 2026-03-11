"""SQLite storage helpers for card collections."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from kardscm.models import CardDict, DeckCardEntry, DeckStats, MatchupStats, ParsedDeck

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cards (
    cardId TEXT PRIMARY KEY,
    importId TEXT,
    imageUrl TEXT,
    thumbUrl TEXT,
    faction TEXT NOT NULL,
    type TEXT NOT NULL,
    rarity TEXT NOT NULL,
    "set" TEXT NOT NULL,
    title TEXT NOT NULL,
    text TEXT,
    kredits INTEGER NOT NULL DEFAULT 0,
    attack INTEGER,
    defense INTEGER,
    attributes TEXT,
    operationCost INTEGER,
    reserved INTEGER NOT NULL DEFAULT 0,
    image TEXT,
    can_create TEXT,
    exile TEXT,
    quantity INTEGER DEFAULT 0,
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
    FOREIGN KEY (card_id) REFERENCES cards(cardId),
    UNIQUE(deck_id, card_id)
);

CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    result TEXT NOT NULL CHECK(result IN ('win', 'loss')),
    opponent_major TEXT NOT NULL,
    opponent_ally TEXT NOT NULL,
    FOREIGN KEY (deck_id) REFERENCES decks(deck_id) ON DELETE CASCADE
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

    Detects old schema (with 'nation' column) and raises an error
    instructing the user to delete the DB and re-sync.

    Args:
        conn: SQLite connection instance.

    Raises:
        SystemExit: If old schema is detected.
    """
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cards'")
    if cursor.fetchone():
        columns = {row[1] for row in conn.execute("PRAGMA table_info(cards)").fetchall()}
        if "nation" in columns:
            raise SystemExit(
                "Old database schema detected (has 'nation' column). "
                "Delete collection.db and run 'kardscm sync' to re-create."
            )
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


def upsert_cards(conn: sqlite3.Connection, cards: Iterable[CardDict]) -> None:
    """Insert or update cards in the database.

    Preserves the user-managed 'quantity' field on conflict.

    Args:
        conn: SQLite connection instance.
        cards: Iterable of CardDict objects.
    """
    rows: list[tuple] = []
    for card in cards:
        card_id = card.get("cardId")
        if not card_id:
            continue
        rows.append(
            (
                card_id,
                card.get("importId", ""),
                card.get("imageUrl", ""),
                card.get("thumbUrl", ""),
                card.get("faction", ""),
                card.get("type", ""),
                card.get("rarity", ""),
                card.get("set", ""),
                card.get("title", ""),
                card.get("text", ""),
                card.get("kredits", 0),
                card.get("attack"),
                card.get("defense"),
                card.get("attributes"),
                card.get("operationCost"),
                card.get("reserved", 0),
                card.get("image", ""),
                card.get("can_create"),
                card.get("exile"),
            )
        )

    if not rows:
        return

    conn.executemany(
        """
        INSERT INTO cards (
            cardId, importId, imageUrl, thumbUrl,
            faction, type, rarity, "set",
            title, text, kredits, attack, defense,
            attributes, operationCost, reserved,
            image, can_create, exile, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(cardId) DO UPDATE SET
            importId = excluded.importId,
            imageUrl = excluded.imageUrl,
            thumbUrl = excluded.thumbUrl,
            faction = excluded.faction,
            type = excluded.type,
            rarity = excluded.rarity,
            "set" = excluded."set",
            title = excluded.title,
            text = excluded.text,
            kredits = excluded.kredits,
            attack = excluded.attack,
            defense = excluded.defense,
            attributes = excluded.attributes,
            operationCost = excluded.operationCost,
            reserved = excluded.reserved,
            image = excluded.image,
            can_create = excluded.can_create,
            exile = excluded.exile,
            updated_at = CURRENT_TIMESTAMP
        """,
        rows,
    )
    conn.commit()


def fetch_cards(conn: sqlite3.Connection) -> list[dict]:
    """Fetch all cards from the database as dicts.

    Args:
        conn: SQLite connection instance.

    Returns:
        List of card dictionaries.
    """
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """
        SELECT
            cardId, importId, imageUrl, thumbUrl,
            faction, type, rarity, "set",
            title, text, kredits, attack, defense,
            attributes, operationCost, reserved,
            image, can_create, exile, quantity, updated_at
        FROM cards
        ORDER BY title
        """
    )
    rows = cursor.fetchall()
    conn.row_factory = None
    return [dict(row) for row in rows]


def update_quantity(
    conn: sqlite3.Connection,
    updates: Iterable[tuple[str, str, int | None]],
    locale_key: str,
) -> tuple[int, list[str]]:
    """Update card quantities by faction and localized title.

    Args:
        conn: SQLite connection instance.
        updates: Iterable of (faction_display, localized_title, quantity) tuples.
        locale_key: Locale key for JSON title extraction (e.g. "en-EN").

    Returns:
        Tuple of (updated_count, not_found_list).
    """
    updated = 0
    not_found = []

    for faction, title, qty in updates:
        if not faction or not title:
            continue
        if qty is None:
            continue

        cursor = conn.execute(
            "UPDATE cards SET quantity = ? WHERE faction = ? AND TRIM(json_extract(title, ?)) = ?",
            (qty, faction, f'$."{locale_key}"', title.strip()),
        )

        if cursor.rowcount > 0:
            updated += 1
        else:
            not_found.append(f"{faction} / {title}")

    conn.commit()
    return updated, not_found


def find_card_id(
    conn: sqlite3.Connection,
    faction: str,
    title: str,
    locale_key: str,
) -> str | None:
    """Find cardId by faction and localized title.

    Args:
        conn: SQLite connection instance.
        faction: Card faction (API name, e.g. 'Soviet').
        title: Localized card title.
        locale_key: Locale key for JSON title extraction.

    Returns:
        cardId string or None if not found.
    """
    row = conn.execute(
        "SELECT cardId FROM cards WHERE faction = ? AND TRIM(json_extract(title, ?)) = ?",
        (faction, f'$."{locale_key}"', title.strip()),
    ).fetchone()
    return row[0] if row else None


def find_card_id_by_exile(
    conn: sqlite3.Connection,
    exile_faction: str,
    title: str,
    locale_key: str,
) -> str | None:
    """Find cardId where exile == faction (cross-faction card fallback).

    Args:
        conn: SQLite connection instance.
        exile_faction: Faction that can use the card via exile (e.g. 'Soviet').
        title: Localized card title.
        locale_key: Locale key for JSON title extraction.

    Returns:
        cardId string or None if not found.
    """
    row = conn.execute(
        "SELECT cardId FROM cards WHERE exile = ? AND TRIM(json_extract(title, ?)) = ?",
        (exile_faction, f'$."{locale_key}"', title.strip()),
    ).fetchone()
    return row[0] if row else None


def get_card_quantity_by_id(conn: sqlite3.Connection, card_id: str) -> int:
    """Return current quantity for a card (0 if not found).

    Args:
        conn: SQLite connection instance.
        card_id: cardId to look up.

    Returns:
        Quantity value, or 0 if card not found.
    """
    row = conn.execute("SELECT quantity FROM cards WHERE cardId = ?", (card_id,)).fetchone()
    return row[0] if row else 0


def update_card_quantity_by_id(conn: sqlite3.Connection, card_id: str, quantity: int) -> None:
    """Update quantity for a card by its ID.

    Args:
        conn: SQLite connection instance.
        card_id: cardId to update.
        quantity: New quantity value.
    """
    conn.execute("UPDATE cards SET quantity = ? WHERE cardId = ?", (quantity, card_id))


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
    faction_map: dict[str, str],
    locale_key: str,
    use_exile_fallback: bool = False,
) -> None:
    """Insert deck cards, linking each to its card_id.

    Args:
        conn: SQLite connection instance.
        deck_id: ID of the deck.
        cards: List of DeckCardEntry dicts.
        faction_map: Mapping from deck nation key to API faction name.
        locale_key: Locale key for title lookup.
        use_exile_fallback: If True, try exile lookup when faction lookup fails.

    Raises:
        ValueError: If a card is not found in the collection.
    """
    for card in cards:
        faction = faction_map.get(card["nation"], card["nation"])
        card_id = find_card_id(conn, faction, card["name"], locale_key)
        if card_id is None and use_exile_fallback:
            card_id = find_card_id_by_exile(conn, faction, card["name"], locale_key)
        if card_id is None:
            msg = f"Card not found: {faction} / {card['name']}"
            raise ValueError(msg)
        conn.execute(
            "INSERT INTO deck_cards (deck_id, card_id, quantity, cost) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(deck_id, card_id) DO UPDATE SET "
            "quantity = excluded.quantity, cost = excluded.cost",
            (deck_id, card_id, card["quantity"], card["cost"]),
        )


def delete_deck(conn: sqlite3.Connection, deck_id: int) -> None:
    """Delete a deck and its cards from the database.

    Relies on ON DELETE CASCADE to remove deck_cards rows automatically.
    Does not affect the cards table.

    Args:
        conn: SQLite connection instance.
        deck_id: ID of the deck to delete.
    """
    conn.execute("DELETE FROM decks WHERE deck_id = ?", (deck_id,))


def delete_all_decks(conn: sqlite3.Connection) -> int:
    """Delete all decks and their cards from the database.

    Relies on ON DELETE CASCADE to remove deck_cards rows automatically.
    Does not affect the cards table.

    Args:
        conn: SQLite connection instance.

    Returns:
        Number of decks deleted.
    """
    cursor = conn.execute("DELETE FROM decks")
    return cursor.rowcount


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
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """
        SELECT
            c.faction, c.title, c.type, c.rarity, c.attributes,
            c."set", c.kredits, c.attack, c.defense, c.text,
            dc.quantity AS deck_quantity, dc.cost AS deck_cost
        FROM deck_cards dc
        JOIN cards c ON dc.card_id = c.cardId
        WHERE dc.deck_id = ?
        ORDER BY c.faction, dc.cost, c.title
        """,
        (deck_id,),
    )
    rows = cursor.fetchall()
    conn.row_factory = None
    return [dict(row) for row in rows]


def insert_match(
    conn: sqlite3.Connection,
    deck_id: int,
    result: str,
    opponent_major: str,
    opponent_ally: str,
) -> int:
    """Insert a match record into the database.

    Args:
        conn: SQLite connection instance.
        deck_id: ID of the deck used.
        result: Match result ('win' or 'loss').
        opponent_major: Opponent's major power faction.
        opponent_ally: Opponent's ally faction.

    Returns:
        The new match_id.
    """
    cursor = conn.execute(
        "INSERT INTO matches (deck_id, result, opponent_major, opponent_ally) "
        "VALUES (?, ?, ?, ?)",
        (deck_id, result, opponent_major, opponent_ally),
    )
    return cursor.lastrowid  # type: ignore[return-value]


def fetch_matches_by_deck(conn: sqlite3.Connection, deck_id: int) -> list[dict]:
    """Fetch all match records for a deck.

    Args:
        conn: SQLite connection instance.
        deck_id: ID of the deck.

    Returns:
        List of match record dicts.
    """
    cursor = conn.execute(
        "SELECT match_id, deck_id, result, opponent_major, opponent_ally "
        "FROM matches WHERE deck_id = ? ORDER BY match_id",
        (deck_id,),
    )
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def compute_deck_stats(conn: sqlite3.Connection, deck_id: int) -> DeckStats | None:
    """Compute aggregated match statistics for a deck.

    Args:
        conn: SQLite connection instance.
        deck_id: ID of the deck.

    Returns:
        DeckStats dict or None if no matches exist.
    """
    matches = fetch_matches_by_deck(conn, deck_id)
    if not matches:
        return None

    wins = sum(1 for m in matches if m["result"] == "win")
    losses = len(matches) - wins
    total = len(matches)

    matchups: dict[tuple[str, str], MatchupStats] = {}
    for m in matches:
        key = (m["opponent_major"], m["opponent_ally"])
        if key not in matchups:
            matchups[key] = MatchupStats(wins=0, losses=0)
        if m["result"] == "win":
            matchups[key]["wins"] += 1
        else:
            matchups[key]["losses"] += 1

    return DeckStats(
        total=total,
        wins=wins,
        losses=losses,
        winrate=round(wins / total * 100, 1) if total > 0 else 0.0,
        matchups=matchups,
    )
