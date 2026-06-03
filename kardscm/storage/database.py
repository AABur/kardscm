"""SQLite storage helpers for card collections."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import sqlite3
import tomllib
from collections.abc import Iterable
from pathlib import Path

from kardscm.constants import DECK_NATION_TO_DB, KNOWN_ABILITIES, KNOWN_EXTRA_ABILITIES
from kardscm.helpers import sanitize_text
from kardscm.models import CardDict, DeckCardEntry, ParsedDeck

ADMIN_EDITABLE_SCALARS: tuple[str, ...] = (
    "faction",
    "type",
    "rarity",
    "set",
    "kredits",
    "attack",
    "defense",
    "operationCost",
    "reserved",
)

# DB columns the admin UI can write directly. Title/text are NOT in this
# set — they are stored as locale-keyed JSON and merged in a separate
# branch in update_card_admin.
ADMIN_DB_COLUMNS: frozenset[str] = (
    frozenset(ADMIN_EDITABLE_SCALARS)
    | {f"ability_{a}" for a in KNOWN_ABILITIES}
    | {f"extra_ability_{a}" for a in KNOWN_EXTRA_ABILITIES}
)

logger = logging.getLogger(__name__)

_EXTRA_ABILITIES_TOML = Path(__file__).parent.parent / "data" / "extra_abilities.toml"


def _ability_columns_sql() -> str:
    return "\n".join(f"    ability_{a} INTEGER NOT NULL DEFAULT 0," for a in KNOWN_ABILITIES)


def _extra_ability_columns_sql() -> str:
    return "\n".join(
        f"    extra_ability_{a} INTEGER NOT NULL DEFAULT 0," for a in KNOWN_EXTRA_ABILITIES
    )


SCHEMA_SQL = f"""
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
{_ability_columns_sql()}
{_extra_ability_columns_sql()}
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
    conn.create_function("sanitize_text", 1, sanitize_text, deterministic=True)
    # Unicode-aware case folding for Cyrillic/non-ASCII text search
    conn.create_function("uni_lower", 1, lambda s: s.casefold() if s else "", deterministic=True)
    return conn


def initialize_schema(conn: sqlite3.Connection, db_path: str | Path | None = None) -> None:
    """Initialize database schema, migrating old schemas when detected.

    Two legacy schemas are recognized:
    - v1: has a 'nation' column — too old; user must delete manually.
    - v2: has an 'attributes' TEXT column — Stage 2 migration. The DB is
      backed up to <db_path>.bak, all tables are dropped, the new schema is
      created, and SystemExit is raised so the user knows to re-sync.

    Args:
        conn: SQLite connection instance.
        db_path: Path to the DB file; required for backup during v2 migration.

    Raises:
        SystemExit: If an incompatible or migrated schema is detected.
    """
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cards'")
    if cursor.fetchone():
        columns = {row[1] for row in conn.execute("PRAGMA table_info(cards)").fetchall()}
        if "nation" in columns:
            raise SystemExit(
                "Old database schema detected (has 'nation' column). "
                "Delete collection.db and run 'kardscm sync' to re-create."
            )
        if "attributes" in columns:
            backup_msg = ""
            if db_path is not None:
                backup = Path(str(db_path) + ".bak")
                shutil.copy2(db_path, backup)
                backup_msg = f" Backup saved to {backup}."
            conn.executescript(
                "DROP TABLE IF EXISTS deck_cards;"
                "DROP TABLE IF EXISTS decks;"
                "DROP TABLE IF EXISTS metadata;"
                "DROP TABLE IF EXISTS cards;"
            )
            conn.executescript(SCHEMA_SQL)
            raise SystemExit(
                f"Database schema updated (Stage 2: ability columns).{backup_msg} "
                "Run 'kardscm sync' to rebuild your collection."
            )
    conn.executescript(SCHEMA_SQL)
    _ensure_extra_ability_columns(conn)
    _bootstrap_extra_abilities_if_stale(conn)


def _ensure_extra_ability_columns(conn: sqlite3.Connection) -> None:
    """Add any missing extra_ability_* columns via ALTER TABLE (idempotent).

    Allows growing ``KNOWN_EXTRA_ABILITIES`` without forcing re-sync.
    Called from ``initialize_schema``; safe to call repeatedly.
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info(cards)").fetchall()}
    for ability in KNOWN_EXTRA_ABILITIES:
        col = f"extra_ability_{ability}"
        if col not in existing:
            conn.execute(f"ALTER TABLE cards ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0")


_SEED_HASH_METADATA_KEY = "extra_abilities_seed_sha256"


def _seed_file_hash() -> str:
    """SHA-256 of the bundled seed TOML — invalidates DB state on edit."""
    return hashlib.sha256(_EXTRA_ABILITIES_TOML.read_bytes()).hexdigest()


def _bootstrap_extra_abilities_if_stale(conn: sqlite3.Connection) -> None:
    """Apply the seed when the bundled file differs from what's stored in DB.

    Detection via SHA-256 of the seed TOML stored in the metadata table.
    Applies on:
      - fresh install (no hash stored)
      - upgrade adding new abilities or correcting cardId lists
    Skips when the seed is already up-to-date — preserves any future
    per-card UI edits across restarts. Sync still calls
    ``apply_extra_abilities_seed`` explicitly to re-apply authoritatively.
    """
    if not KNOWN_EXTRA_ABILITIES:
        return
    current_hash = _seed_file_hash()
    row = conn.execute(
        "SELECT value FROM metadata WHERE key = ?", (_SEED_HASH_METADATA_KEY,)
    ).fetchone()
    stored_hash = row[0] if row else None
    if stored_hash == current_hash:
        return
    apply_extra_abilities_seed(conn)


def _load_extra_abilities_seed() -> dict[str, list[str]]:
    """Read the bundled TOML seed → {ability_key: [cardId, ...]}.

    Raises ValueError on structural mismatch — fail-fast on hand-edit typos
    that would otherwise silently corrupt flags (e.g. ``cards = "abc"``
    coerced into ``["a", "b", "c"]``).
    """
    with _EXTRA_ABILITIES_TOML.open("rb") as f:
        data = tomllib.load(f)
    abilities = data.get("abilities", {})
    if not isinstance(abilities, dict):
        raise ValueError(
            f"{_EXTRA_ABILITIES_TOML}: [abilities] must be a table, got {type(abilities).__name__}"
        )
    seed: dict[str, list[str]] = {}
    for key, section in abilities.items():
        if not isinstance(section, dict):
            raise ValueError(f"{_EXTRA_ABILITIES_TOML}: [abilities.{key}] must be a table")
        cards = section.get("cards", [])
        if not isinstance(cards, list) or not all(isinstance(c, str) for c in cards):
            raise ValueError(
                f"{_EXTRA_ABILITIES_TOML}: [abilities.{key}].cards must be an array of strings"
            )
        seed[key] = list(cards)
    return seed


def apply_extra_abilities_seed(
    conn: sqlite3.Connection, seed: dict[str, list[str]] | None = None
) -> None:
    """Apply manually-curated extra-ability flags to the cards table.

    Resets every ``extra_ability_*`` column to 0 in a single UPDATE, then
    sets 1 for cardIds listed in the seed (one UPDATE per ability with a
    populated list). Unknown ability keys and non-existent cardIds are
    silently ignored.

    Args:
        conn: SQLite connection.
        seed: Mapping ``ability_key → [cardId, ...]``. If None, loads
            from the bundled ``kardscm/data/extra_abilities.toml``.
    """
    seed_provided = seed is not None
    if seed is None:
        seed = _load_extra_abilities_seed()
    if KNOWN_EXTRA_ABILITIES:
        reset_clause = ", ".join(f"extra_ability_{a} = 0" for a in KNOWN_EXTRA_ABILITIES)
        conn.execute(f"UPDATE cards SET {reset_clause}")
    for ability in KNOWN_EXTRA_ABILITIES:
        card_ids = seed.get(ability, [])
        if not card_ids:
            continue
        placeholders = ", ".join("?" for _ in card_ids)
        conn.execute(
            f"UPDATE cards SET extra_ability_{ability} = 1 WHERE cardId IN ({placeholders})",
            tuple(card_ids),
        )
    if not seed_provided:
        # Track the bundled seed file's hash so subsequent startups can
        # detect changes and re-apply automatically.
        set_metadata(conn, _SEED_HASH_METADATA_KEY, _seed_file_hash())
    conn.commit()


from kardscm.storage.metadata import set_metadata


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
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        f"""
        SELECT
            cardId, importId, imageUrl, thumbUrl,
            faction, type, rarity, "set",
            title, text, kredits, attack, defense,
            {ability_cols},
            operationCost, reserved,
            image, can_create, exile, quantity, updated_at
        FROM cards
        ORDER BY title
        """
    )
    rows = cursor.fetchall()
    conn.row_factory = None
    return [dict(row) for row in rows]


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


def update_card_admin(
    conn: sqlite3.Connection,
    card_id: str,
    fields: dict,
    locale_key: str,
) -> None:
    """Apply admin edits to a single card. Caller must commit.

    Whitelists column names, merges localized title/text into existing JSON,
    rejects unknown fields, and emits a single parametrised UPDATE.

    Args:
        conn: SQLite connection instance.
        card_id: cardId of the row to update.
        fields: Mapping of column name to new value. Recognised keys:
            ADMIN_EDITABLE_SCALARS, ability_*, extra_ability_*, title, text.
            title/text values must be plain strings (the active locale text);
            they are merged into the existing JSON under locale_key.
        locale_key: JSON key for title/text merge (e.g. "en-EN").

    Raises:
        KeyError: If card_id does not exist.
        ValueError: If fields contains an unsupported key.
    """
    row = conn.execute("SELECT title, text FROM cards WHERE cardId = ?", (card_id,)).fetchone()
    if row is None:
        raise KeyError(f"card not found: {card_id}")

    set_clauses: list[str] = []
    params: list[object] = []

    for key, value in fields.items():
        if key in ADMIN_DB_COLUMNS:
            set_clauses.append(f'"{key}" = ?')
            params.append(value)
        elif key == "title":
            existing = json.loads(row[0]) if row[0] else {}
            existing[locale_key] = value
            set_clauses.append('"title" = ?')
            params.append(json.dumps(existing, ensure_ascii=False))
        elif key == "text":
            existing = json.loads(row[1]) if row[1] else {}
            existing[locale_key] = value
            set_clauses.append('"text" = ?')
            params.append(json.dumps(existing, ensure_ascii=False))
        else:
            raise ValueError(f"unsupported admin field: {key}")

    if not set_clauses:
        return

    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(card_id)
    sql = f"UPDATE cards SET {', '.join(set_clauses)} WHERE cardId = ?"
    conn.execute(sql, params)


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
