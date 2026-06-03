"""Deck CRUD helpers for SQLite storage."""

from __future__ import annotations

import sqlite3

from kardscm.constants import DECK_NATION_TO_DB, KNOWN_ABILITIES
from kardscm.models import DeckCardEntry, ParsedDeck
from kardscm.storage.cards import find_card_id, find_card_id_by_exile


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
    locale_key: str,
    use_exile_fallback: bool = False,
) -> None:
    """Insert deck cards, linking each to its card_id.

    Args:
        conn: SQLite connection instance.
        deck_id: ID of the deck.
        cards: List of DeckCardEntry dicts.
        locale_key: Locale key for title lookup.
        use_exile_fallback: If True, try exile lookup when faction lookup fails.

    Raises:
        ValueError: If a card is not found in the collection.
    """
    for card in cards:
        faction = DECK_NATION_TO_DB.get(card["nation"], card["nation"])
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
    ability_cols = ", ".join(f"c.ability_{a}" for a in KNOWN_ABILITIES)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        f"""
        SELECT
            c.faction, c.title, c.type, c.rarity,
            {ability_cols},
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
