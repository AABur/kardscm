"""Baseline management commands."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from kardscm.scraping import baseline

logger = logging.getLogger(__name__)

_BASELINE_REQUIRED_KEYS = ("card_count", "node_keys", "json_keys", "enum_values")


def baseline_accept() -> None:
    """Promote the most recent ``sync-schema-observed-*.json`` to baseline.

    Looks for files matching the pattern in cwd, picks the lexicographically
    latest (timestamps are ISO-like and sort correctly), validates its
    structural shape (must be a dict with all required snapshot keys of
    the correct types), and copies it to the committed baseline location.
    """
    candidates = sorted(Path.cwd().glob("sync-schema-observed-*.json"))
    if not candidates:
        raise SystemExit(
            "No sync-schema-observed-*.json files found in current directory. "
            "Run `kardscm sync` first."
        )
    latest = candidates[-1]
    try:
        parsed = json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"Cannot parse {latest}: {exc}") from exc

    if not isinstance(parsed, dict):
        raise SystemExit(f"{latest} is not a snapshot object (got {type(parsed).__name__}).")
    missing = [k for k in _BASELINE_REQUIRED_KEYS if k not in parsed]
    if missing:
        raise SystemExit(f"{latest} is missing required keys: {', '.join(missing)}")
    if not isinstance(parsed["card_count"], int):
        raise SystemExit(f"{latest}: card_count must be an int")
    if not isinstance(parsed["node_keys"], list):
        raise SystemExit(f"{latest}: node_keys must be a list")
    if not isinstance(parsed["json_keys"], dict):
        raise SystemExit(f"{latest}: json_keys must be a dict")
    if not isinstance(parsed["enum_values"], dict):
        raise SystemExit(f"{latest}: enum_values must be a dict")

    shutil.copy2(latest, baseline.BASELINE_PATH)
    logger.info("Baseline updated from %s.", latest.name)
