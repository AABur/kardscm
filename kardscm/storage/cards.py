"""Card CRUD helpers for SQLite storage."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from kardscm.constants import KNOWN_ABILITIES, KNOWN_EXTRA_ABILITIES
from kardscm.models import CardDict


def upsert_cards(conn: sqlite3.Connection, cards: Iterable[CardDict]) -> None:
    """Insert or update cards in the database.

    Preserves the user-managed 'quantity' field on conflict.

    Args:
        conn: SQLite connection instance.
        cards: Iterable of CardDict objects.
    """
    _ability_cols = [f"ability_{a}" for a in KNOWN_ABILITIES]
    ability_update_sql = "\n".join(
        f"            ability_{a} = excluded.ability_{a}," for a in KNOWN_ABILITIES
    )
    insert_cols = ", ".join(_ability_cols)
    insert_placeholders = ", ".join("?" for _ in KNOWN_ABILITIES)

    rows: list[tuple] = []
    for card in cards:
        card_id = card.get("cardId")
        if not card_id:
            continue
        ability_values = tuple(card.get(f"ability_{a}", 0) for a in KNOWN_ABILITIES)
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
                *ability_values,
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
        f"""
        INSERT INTO cards (
            cardId, importId, imageUrl, thumbUrl,
            faction, type, rarity, "set",
            title, text, kredits, attack, defense,
            {insert_cols},
            operationCost, reserved,
            image, can_create, exile, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            {insert_placeholders},
            ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
        )
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
            {ability_update_sql}
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
    ability_cols = ", ".join(f"ability_{a}" for a in KNOWN_ABILITIES)
    extra_ability_cols = ", ".join(f"extra_ability_{a}" for a in KNOWN_EXTRA_ABILITIES)
    cursor = conn.execute(
        f"""
        SELECT
            cardId, importId, imageUrl, thumbUrl,
            faction, type, rarity, "set",
            title, text, kredits, attack, defense,
            {ability_cols},
            {extra_ability_cols},
            operationCost, reserved,
            image, can_create, exile, quantity, updated_at
        FROM cards
        ORDER BY title
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def delete_cards(conn: sqlite3.Connection, card_ids: Iterable[str]) -> int:
    """Delete cards from the database by cardId. Used after explicit user
    approval of the "removed" diff category.

    Args:
        conn: SQLite connection instance.
        card_ids: Iterable of cardId strings to remove.

    Returns:
        Number of rows actually deleted.
    """
    ids = [cid for cid in card_ids if cid]
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    cursor = conn.execute(f"DELETE FROM cards WHERE cardId IN ({placeholders})", ids)
    conn.commit()
    return cursor.rowcount


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
            "UPDATE cards SET quantity = ? "
            "WHERE faction = ? "
            "AND sanitize_text(json_extract(title, ?)) = sanitize_text(?)",
            (qty, faction, f'$."{locale_key}"', title),
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
        "SELECT cardId FROM cards "
        "WHERE faction = ? "
        "AND sanitize_text(json_extract(title, ?)) = sanitize_text(?)",
        (faction, f'$."{locale_key}"', title),
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
        "SELECT cardId FROM cards "
        "WHERE exile = ? "
        "AND sanitize_text(json_extract(title, ?)) = sanitize_text(?)",
        (exile_faction, f'$."{locale_key}"', title),
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
