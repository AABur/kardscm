"""Metadata key-value storage helpers."""

from __future__ import annotations

import sqlite3


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


def get_metadata(conn: sqlite3.Connection, key: str) -> str | None:
    """Read a metadata key value.

    Args:
        conn: SQLite connection instance.
        key: Metadata key.

    Returns:
        The stored value, or None if the key is not set.
    """
    row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def delete_metadata(conn: sqlite3.Connection, key: str) -> None:
    """Remove a metadata key.

    Args:
        conn: SQLite connection instance.
        key: Metadata key.
    """
    conn.execute("DELETE FROM metadata WHERE key = ?", (key,))
    conn.commit()
