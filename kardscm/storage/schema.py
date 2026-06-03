"""SQLite schema definition, connection bootstrap, and schema initializer."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from kardscm.constants import KNOWN_ABILITIES, KNOWN_EXTRA_ABILITIES
from kardscm.helpers import sanitize_text
from kardscm.storage.seed_extra_abilities import _bootstrap_extra_abilities_if_stale


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
