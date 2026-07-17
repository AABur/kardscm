"""Baseline management commands."""

from __future__ import annotations

import json
import logging
from typing import cast

from kardscm.commands.sync import OBSERVED_SNAPSHOT_KEY
from kardscm.constants import DEFAULT_DB_PATH
from kardscm.scraping.baseline import Snapshot, save_baseline
from kardscm.storage import (
    delete_metadata,
    get_connection,
    get_metadata,
    initialize_schema,
)

logger = logging.getLogger(__name__)

_BASELINE_REQUIRED_KEYS = ("card_count", "node_keys", "json_keys", "enum_values")
_REQUIRED_KEY_TYPES: dict[str, tuple[type, str]] = {
    "card_count": (int, "an int"),
    "node_keys": (list, "a list"),
    "json_keys": (dict, "a dict"),
    "enum_values": (dict, "a dict"),
}


def baseline_accept(db_path: str = DEFAULT_DB_PATH) -> None:
    """Promote the snapshot stashed by the last halted sync to baseline.

    The snapshot is the shape the user reviewed when the sync halted, so
    accepting adopts exactly that — not whatever the API serves right now.

    Args:
        db_path: SQLite database path.
    """
    with get_connection(db_path) as conn:
        initialize_schema(conn, db_path)
        raw = get_metadata(conn, OBSERVED_SNAPSHOT_KEY)

    if raw is None:
        raise SystemExit(
            "No drifted API shape is waiting to be accepted. "
            "Run `kardscm sync` first — accept only applies after a sync halts on drift."
        )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Stored snapshot is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise SystemExit(f"Stored snapshot is not an object (got {type(parsed).__name__}).")
    missing = [k for k in _BASELINE_REQUIRED_KEYS if k not in parsed]
    if missing:
        raise SystemExit(f"Stored snapshot is missing required keys: {', '.join(missing)}")
    for key, (expected, label) in _REQUIRED_KEY_TYPES.items():
        if not isinstance(parsed[key], expected):
            raise SystemExit(f"Stored snapshot: {key} must be {label}")

    save_baseline(cast(Snapshot, parsed))
    with get_connection(db_path) as conn:
        delete_metadata(conn, OBSERVED_SNAPSHOT_KEY)
    logger.info("Baseline updated from the last halted sync.")
