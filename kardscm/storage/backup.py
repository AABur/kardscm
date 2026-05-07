"""SQLite database backup helper used before admin sessions."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path


def backup_database(db_path: Path) -> Path:
    """Copy the database file next to itself with a timestamped suffix.

    Args:
        db_path: Path to the live SQLite file.

    Returns:
        Path of the created backup.

    Raises:
        FileNotFoundError: If db_path does not exist.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at {db_path}")
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = db_path.with_suffix(db_path.suffix + f".bak.{ts}")
    shutil.copy2(db_path, backup_path)
    return backup_path
