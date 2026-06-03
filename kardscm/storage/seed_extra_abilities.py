"""Seed loader and bootstrap logic for extra-ability flags."""

from __future__ import annotations

import hashlib
import sqlite3
import tomllib
from pathlib import Path

from kardscm.constants import KNOWN_EXTRA_ABILITIES
from kardscm.storage.metadata import set_metadata

_EXTRA_ABILITIES_TOML = Path(__file__).parent.parent / "data" / "extra_abilities.toml"

_SEED_HASH_METADATA_KEY = "extra_abilities_seed_sha256"


def _seed_file_hash() -> str:
    """SHA-256 of the bundled seed TOML — invalidates DB state on edit."""
    return hashlib.sha256(_EXTRA_ABILITIES_TOML.read_bytes()).hexdigest()


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
