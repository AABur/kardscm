"""SQLite storage helpers for card collections."""

from __future__ import annotations

import hashlib
import logging
import shutil
import sqlite3
import tomllib
from pathlib import Path

from kardscm.constants import KNOWN_ABILITIES, KNOWN_EXTRA_ABILITIES
from kardscm.helpers import sanitize_text
from kardscm.storage.admin import (  # noqa: F401
    ADMIN_DB_COLUMNS,
    ADMIN_EDITABLE_SCALARS,
    update_card_admin,
)
from kardscm.storage.cards import (  # noqa: F401
    delete_cards,
    fetch_cards,
    find_card_id,
    find_card_id_by_exile,
    get_card_quantity_by_id,
    update_card_quantity_by_id,
    update_quantity,
    upsert_cards,
)
from kardscm.storage.decks import (  # noqa: F401
    delete_all_decks,
    delete_deck,
    fetch_all_decks,
    fetch_deck_cards,
    find_deck_by_name,
    insert_deck,
    insert_deck_cards,
)
from kardscm.storage.metadata import set_metadata  # noqa: F401

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




