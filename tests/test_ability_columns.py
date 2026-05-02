"""Failing tests for Stage 2: binary ability columns replacing attributes JSON.

These tests describe the desired end-state and fail until the implementation
is complete.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from kardscm.constants import KNOWN_ABILITIES
from kardscm.locales import LANGUAGE_EN
from kardscm.storage import get_connection, initialize_schema


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_schema_has_no_attributes_column(db_connection):
    cols = {row[1] for row in db_connection.execute("PRAGMA table_info(cards)").fetchall()}
    assert "attributes" not in cols


def test_schema_has_all_ability_columns(db_connection):
    cols = {row[1] for row in db_connection.execute("PRAGMA table_info(cards)").fetchall()}
    for ability in KNOWN_ABILITIES:
        assert f"ability_{ability}" in cols, f"missing column: ability_{ability}"


def test_ability_columns_default_to_zero(db_connection):
    db_connection.execute(
        """
        INSERT INTO cards (cardId, faction, type, rarity, "set", title, kredits)
        VALUES ('x', 'Soviet', 'infantry', 'Standard', 'Base',
                '{"en-EN":"X"}', 1)
        """
    )
    row = db_connection.execute(
        "SELECT ability_guard, ability_blitz FROM cards WHERE cardId='x'"
    ).fetchone()
    assert row[0] == 0
    assert row[1] == 0


# ---------------------------------------------------------------------------
# Migration: old schema with attributes column
# ---------------------------------------------------------------------------


def _make_old_db(db_path: Path) -> None:
    """Create a minimal DB using the pre-Stage-2 schema."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE cards (
            cardId TEXT PRIMARY KEY,
            faction TEXT NOT NULL DEFAULT '',
            type TEXT NOT NULL DEFAULT '',
            rarity TEXT NOT NULL DEFAULT '',
            "set" TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            kredits INTEGER NOT NULL DEFAULT 0,
            attributes TEXT,
            quantity INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        "INSERT INTO cards (cardId, faction, type, rarity, \"set\", title, kredits, attributes) "
        "VALUES ('abc', 'Soviet', 'infantry', 'Standard', 'Base', '{\"en-EN\":\"X\"}', 1, '[\"blitz\"]')"
    )
    conn.commit()
    conn.close()


def test_old_schema_creates_backup(tmp_path):
    db_path = tmp_path / "collection.db"
    backup_path = tmp_path / "collection.db.bak"
    _make_old_db(db_path)

    with pytest.raises(SystemExit):
        conn = get_connection(db_path)
        initialize_schema(conn, db_path)

    assert backup_path.exists(), "backup was not created"


def test_old_schema_backup_contains_original_data(tmp_path):
    db_path = tmp_path / "collection.db"
    _make_old_db(db_path)

    with pytest.raises(SystemExit):
        conn = get_connection(db_path)
        initialize_schema(conn, db_path)

    bak = sqlite3.connect(str(tmp_path / "collection.db.bak"))
    row = bak.execute("SELECT attributes FROM cards WHERE cardId='abc'").fetchone()
    bak.close()
    assert row is not None
    assert row[0] == '["blitz"]'


def test_old_schema_exit_message_mentions_backup(tmp_path):
    db_path = tmp_path / "collection.db"
    _make_old_db(db_path)

    with pytest.raises(SystemExit) as exc_info:
        conn = get_connection(db_path)
        initialize_schema(conn, db_path)

    message = str(exc_info.value)
    assert "bak" in message.lower() or "backup" in message.lower()


def test_after_migration_new_schema_is_created(tmp_path):
    """After migration raises SystemExit, a second initialize_schema call succeeds."""
    db_path = tmp_path / "collection.db"
    _make_old_db(db_path)

    with pytest.raises(SystemExit):
        conn = get_connection(db_path)
        initialize_schema(conn, db_path)
        conn.close()

    conn2 = get_connection(db_path)
    initialize_schema(conn2, db_path)
    cols = {row[1] for row in conn2.execute("PRAGMA table_info(cards)").fetchall()}
    conn2.close()
    assert "ability_guard" in cols
    assert "attributes" not in cols


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------


def test_normalizer_sets_ability_flags():
    from kardscm.scraping.normalizer import normalize_card

    node = {
        "cardId": "n1",
        "importId": "i1",
        "imageUrl": "",
        "thumbUrl": "",
        "faction": {"name": "Soviet"},
        "cardType": {"name": "infantry"},
        "rarity": {"name": "Standard"},
        "set": {"name": "Base"},
        "title": [{"value": "T", "languageId": "en-EN"}],
        "text": [],
        "kredits": 2,
        "attack": 1,
        "defense": 1,
        "attributes": ["blitz", "guard"],
        "operationCost": None,
        "reserved": False,
        "image": "",
        "canCreate": None,
        "exile": None,
    }
    result = normalize_card(node)

    assert result["ability_blitz"] == 1
    assert result["ability_guard"] == 1
    assert result["ability_alpine"] == 0
    assert result["ability_smokescreen"] == 0
    assert "attributes" not in result


def test_normalizer_unknown_ability_is_silently_ignored():
    from kardscm.scraping.normalizer import normalize_card

    node = {
        "cardId": "n2",
        "importId": "i2",
        "imageUrl": "",
        "thumbUrl": "",
        "faction": {"name": "Soviet"},
        "cardType": {"name": "infantry"},
        "rarity": {"name": "Standard"},
        "set": {"name": "Base"},
        "title": [{"value": "T", "languageId": "en-EN"}],
        "text": [],
        "kredits": 1,
        "attack": 0,
        "defense": 0,
        "attributes": ["BecomesVeteran", "unknownAbility"],
        "operationCost": None,
        "reserved": False,
        "image": "",
        "canCreate": None,
        "exile": None,
    }
    result = normalize_card(node)
    for ability in KNOWN_ABILITIES:
        assert result[f"ability_{ability}"] == 0


# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------


def _ability_card(**overrides) -> dict:
    """Minimal card dict with all ability columns."""
    base: dict = {
        "cardId": "c1",
        "importId": "i1",
        "imageUrl": "",
        "thumbUrl": "",
        "faction": "Soviet",
        "type": "infantry",
        "rarity": "Standard",
        "set": "Base",
        "title": '{"en-EN":"Alpha"}',
        "text": '{"en-EN":"Desc"}',
        "kredits": 1,
        "attack": 1,
        "defense": 1,
        "operationCost": None,
        "reserved": 0,
        "image": "",
        "can_create": None,
        "exile": None,
        "quantity": 0,
    }
    for ability in KNOWN_ABILITIES:
        base[f"ability_{ability}"] = 0
    base.update(overrides)
    return base


def test_translate_card_reads_ability_columns():
    from kardscm.export.exporters import translate_card_for_export

    card = _ability_card(ability_guard=1, ability_blitz=1)
    result = translate_card_for_export(card, LANGUAGE_EN)
    abilities_field = result["attributes"]
    assert "Guard" in abilities_field
    assert "Blitz" in abilities_field
    assert "Alpine" not in abilities_field


def test_translate_card_no_abilities_gives_empty_string():
    from kardscm.export.exporters import translate_card_for_export

    card = _ability_card()
    result = translate_card_for_export(card, LANGUAGE_EN)
    assert result["attributes"] == ""


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


def test_diff_detects_ability_change(make_card):
    from kardscm.diff import compute_diff
    from kardscm.locales import LANGUAGE_EN

    old = make_card(cardId="c1", ability_guard=0, ability_blitz=0)
    new_card = make_card(cardId="c1", ability_guard=1, ability_blitz=0)

    result = compute_diff([old], [new_card], LANGUAGE_EN)
    changed_ids = [c["cardId"] for c in result["changed"]]
    assert "c1" in changed_ids


def test_diff_same_abilities_no_change(make_card):
    from kardscm.diff import compute_diff
    from kardscm.locales import LANGUAGE_EN

    card = make_card(cardId="c1", ability_guard=1)
    result = compute_diff([card], [card], LANGUAGE_EN)
    assert result["changed"] == []
