"""Tests for extra-abilities storage layer (Stage Этап 2)."""

from __future__ import annotations

import sqlite3

import pytest

from kardscm.constants import KNOWN_ABILITIES, KNOWN_EXTRA_ABILITIES
from kardscm.storage.database import (
    _ensure_extra_ability_columns,
    apply_extra_abilities_seed,
    initialize_schema,
)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _insert_minimal_card(conn: sqlite3.Connection, card_id: str, *, quantity: int = 0) -> None:
    ability_cols = ", ".join(f"ability_{a}" for a in KNOWN_ABILITIES)
    ability_zeros = ", ".join("0" for _ in KNOWN_ABILITIES)
    conn.execute(
        f"""
        INSERT INTO cards (
            cardId, faction, type, rarity, "set", title, kredits, quantity,
            {ability_cols}
        ) VALUES (?, 'Soviet', 'infantry', 'Standard', 'Base', '{{}}', 0, ?,
            {ability_zeros})
        """,
        (card_id, quantity),
    )


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    initialize_schema(c)
    yield c
    c.close()


class TestEnsureExtraAbilityColumns:
    def test_fresh_schema_has_all_extra_ability_columns(self, conn):
        cols = _table_columns(conn, "cards")
        for ability in KNOWN_EXTRA_ABILITIES:
            assert f"extra_ability_{ability}" in cols

    def test_idempotent_on_second_call(self, conn):
        # initialize_schema already ran in fixture; calling ensure again is fine
        _ensure_extra_ability_columns(conn)
        _ensure_extra_ability_columns(conn)
        cols = _table_columns(conn, "cards")
        for ability in KNOWN_EXTRA_ABILITIES:
            assert f"extra_ability_{ability}" in cols

    def test_adds_missing_columns_to_legacy_schema(self):
        # Simulate a DB that has cards table but no extra_ability_* columns —
        # this is the realistic upgrade path for existing users.
        c = sqlite3.connect(":memory:")
        ability_cols_sql = ",\n".join(
            f"    ability_{a} INTEGER NOT NULL DEFAULT 0" for a in KNOWN_ABILITIES
        )
        c.executescript(
            f"""
            CREATE TABLE cards (
                cardId TEXT PRIMARY KEY,
                faction TEXT NOT NULL,
                type TEXT NOT NULL,
                rarity TEXT NOT NULL,
                "set" TEXT NOT NULL,
                title TEXT NOT NULL,
                kredits INTEGER NOT NULL DEFAULT 0,
                quantity INTEGER DEFAULT 0,
            {ability_cols_sql}
            );
            """
        )
        c.execute(
            'INSERT INTO cards (cardId, faction, type, rarity, "set", title, kredits, quantity) '
            "VALUES ('test_card', 'Soviet', 'infantry', 'Standard', 'Base', '{}', 1, 5)"
        )

        before_cols = _table_columns(c, "cards")
        for ability in KNOWN_EXTRA_ABILITIES:
            assert f"extra_ability_{ability}" not in before_cols

        _ensure_extra_ability_columns(c)

        after_cols = _table_columns(c, "cards")
        for ability in KNOWN_EXTRA_ABILITIES:
            assert f"extra_ability_{ability}" in after_cols

        # Existing data preserved
        row = c.execute(
            "SELECT cardId, quantity FROM cards WHERE cardId = ?", ("test_card",)
        ).fetchone()
        assert row == ("test_card", 5)
        c.close()


class TestApplyExtraAbilitiesSeed:
    def test_sets_flags_for_listed_cards(self, conn):
        _insert_minimal_card(conn, "card_a")
        _insert_minimal_card(conn, "card_b")
        _insert_minimal_card(conn, "card_c")

        apply_extra_abilities_seed(conn, seed={"pincer": ["card_a", "card_b"]})

        rows = conn.execute(
            "SELECT cardId, extra_ability_pincer FROM cards ORDER BY cardId"
        ).fetchall()
        assert rows == [("card_a", 1), ("card_b", 1), ("card_c", 0)]

    def test_resets_flag_when_card_removed_from_seed(self, conn):
        _insert_minimal_card(conn, "card_a")
        # First pass — card_a marked
        apply_extra_abilities_seed(conn, seed={"pincer": ["card_a"]})
        assert conn.execute(
            "SELECT extra_ability_pincer FROM cards WHERE cardId = ?", ("card_a",)
        ).fetchone() == (1,)
        # Second pass — empty seed → flag must reset
        apply_extra_abilities_seed(conn, seed={"pincer": []})
        assert conn.execute(
            "SELECT extra_ability_pincer FROM cards WHERE cardId = ?", ("card_a",)
        ).fetchone() == (0,)

    def test_ignores_unknown_ability_in_seed(self, conn):
        _insert_minimal_card(conn, "card_a")
        # Bogus ability key not in KNOWN_EXTRA_ABILITIES — must not raise
        apply_extra_abilities_seed(conn, seed={"bogus_ability_x": ["card_a"]})
        # No new column was added; pincer flag still 0
        row = conn.execute(
            "SELECT extra_ability_pincer FROM cards WHERE cardId = ?", ("card_a",)
        ).fetchone()
        assert row == (0,)

    def test_ignores_unknown_card_id_in_seed(self, conn):
        _insert_minimal_card(conn, "card_a")
        # Seed lists a cardId that doesn't exist — must not raise
        apply_extra_abilities_seed(conn, seed={"pincer": ["card_a", "no_such_card"]})
        row = conn.execute(
            "SELECT extra_ability_pincer FROM cards WHERE cardId = ?", ("card_a",)
        ).fetchone()
        assert row == (1,)

    def test_default_seed_loads_from_toml_file(self, conn):
        # Without seed= arg, should load from kardscm/data/extra_abilities.toml.
        # We just check it runs without error and one of the real cardIds gets
        # the right flag (uses fixture's empty cards table → no rows updated,
        # but no error either).
        apply_extra_abilities_seed(conn)
        # No cards in fixture — so just verify the columns exist (sanity)
        cols = _table_columns(conn, "cards")
        for ability in KNOWN_EXTRA_ABILITIES:
            assert f"extra_ability_{ability}" in cols


class TestSeedLoaderValidation:
    """_load_extra_abilities_seed must fail fast on malformed TOML."""

    def test_rejects_string_in_cards_field(self, tmp_path, monkeypatch):
        # cards = "abc" would silently coerce to ['a','b','c'] without validation
        bad = tmp_path / "extra_abilities.toml"
        bad.write_text('[abilities.pincer]\ncards = "abc"\n')
        from kardscm.storage import seed_extra_abilities as seed_mod

        monkeypatch.setattr(seed_mod, "_EXTRA_ABILITIES_TOML", bad)
        with pytest.raises(ValueError, match="cards must be an array of strings"):
            seed_mod._load_extra_abilities_seed()

    def test_rejects_non_string_element_in_cards(self, tmp_path, monkeypatch):
        bad = tmp_path / "extra_abilities.toml"
        bad.write_text("[abilities.pincer]\ncards = [123]\n")
        from kardscm.storage import seed_extra_abilities as seed_mod

        monkeypatch.setattr(seed_mod, "_EXTRA_ABILITIES_TOML", bad)
        with pytest.raises(ValueError, match="cards must be an array of strings"):
            seed_mod._load_extra_abilities_seed()
