"""Tests for kardscm.web.queries — filter/sort SQL builder."""

from __future__ import annotations

import json
import sqlite3

import pytest

from kardscm.constants import KNOWN_ABILITIES
from kardscm.storage.database import get_connection, initialize_schema
from kardscm.web.queries import ALLOWED_SORT_COLUMNS, CardFilters, query_cards

_ABILITY_COLS = [f"ability_{a}" for a in KNOWN_ABILITIES]


def _make_card(
    *,
    card_id: str,
    faction: str = "Soviet",
    card_type: str = "infantry",
    rarity: str = "Standard",
    card_set: str = "Base",
    title_en: str = "Card",
    title_ru: str = "Карта",
    text_en: str = "",
    text_ru: str = "",
    kredits: int = 1,
    attack: int | None = 1,
    defense: int | None = 1,
    operation_cost: int | None = None,
    reserved: int = 0,
    can_create: str | None = None,
    quantity: int = 0,
    abilities: frozenset[str] = frozenset(),
    exile: str | None = None,
) -> tuple:
    title = json.dumps({"en-EN": title_en, "ru-RU": title_ru})
    text = json.dumps({"en-EN": text_en, "ru-RU": text_ru})
    return (
        card_id,
        "",  # importId
        "",  # imageUrl
        "",  # thumbUrl
        faction,
        card_type,
        rarity,
        card_set,
        title,
        text,
        kredits,
        attack,
        defense,
        *(1 if a in abilities else 0 for a in KNOWN_ABILITIES),
        operation_cost,
        reserved,
        "",  # image
        can_create,
        exile,
        quantity,
    )


@pytest.fixture
def conn() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    initialize_schema(conn)
    rows = [
        _make_card(
            card_id="sov_inf_1",
            faction="Soviet",
            card_type="infantry",
            rarity="Standard",
            card_set="Base",
            title_en="Soviet Rifles",
            title_ru="Советские стрелки",
            text_en="standard rifles",
            text_ru="обычные стрелки",
            kredits=2,
            quantity=2,
            abilities=frozenset({"blitz"}),
        ),
        _make_card(
            card_id="sov_tank_1",
            faction="Soviet",
            card_type="tank",
            rarity="Limited",
            card_set="WorldAtWar",
            title_en="T-34",
            title_ru="Т-34",
            kredits=4,
            attack=3,
            defense=4,
            quantity=0,
            abilities=frozenset({"guard"}),
        ),
        _make_card(
            card_id="ger_inf_1",
            faction="Germany",
            card_type="infantry",
            rarity="Standard",
            card_set="Base",
            title_en="Wehrmacht",
            title_ru="Вермахт",
            kredits=2,
            quantity=3,
        ),
        _make_card(
            card_id="usa_order",
            faction="USA",
            card_type="order",
            rarity="Standard",
            card_set="Base",
            title_en="Air Strike",
            title_ru="Авиаудар",
            kredits=3,
            attack=None,
            defense=None,
            operation_cost=2,
            quantity=1,
            abilities=frozenset({"blitz"}),
        ),
        _make_card(
            card_id="reserved_card",
            faction="Soviet",
            card_type="infantry",
            title_en="Reserved Card",
            title_ru="Резервная карта",
            reserved=1,
            quantity=0,
        ),
        _make_card(
            card_id="spawnable_card",
            faction="Soviet",
            card_type="tank",
            card_set="OnlySpawnable",
            title_en="Spawned Card",
            title_ru="Спаунованная карта",
            quantity=0,
        ),
        _make_card(
            card_id="pol_exile_tank",
            faction="Poland",
            card_type="tank",
            rarity="Standard",
            card_set="Legions",
            title_en="T-34 76 PL",
            title_ru="Т-34 76 PL",
            kredits=4,
            attack=4,
            defense=4,
            quantity=0,
            exile="Soviet",
        ),
    ]
    ability_cols = ", ".join(_ABILITY_COLS)
    ability_placeholders = ", ".join("?" for _ in KNOWN_ABILITIES)
    conn.executemany(
        f"""
        INSERT INTO cards (
            cardId, importId, imageUrl, thumbUrl,
            faction, type, rarity, "set",
            title, text, kredits, attack, defense,
            {ability_cols},
            operationCost, reserved,
            image, can_create, exile, quantity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {ability_placeholders}, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    yield conn
    conn.close()


def _ids(rows: list[dict]) -> list[str]:
    return [r["cardId"] for r in rows]


class TestDefaults:
    def test_no_filters_excludes_reserved_and_spawnable(self, conn):
        result = query_cards(conn, CardFilters())
        assert "reserved_card" not in _ids(result)
        assert "spawnable_card" not in _ids(result)
        # An exile card is a normal card under its own faction: shown by default.
        assert "pol_exile_tank" in _ids(result)
        assert len(result) == 5

    def test_default_sort_is_faction_then_title(self, conn):
        result = query_cards(conn, CardFilters(), locale_key="en-EN")
        ids = _ids(result)
        # Germany < Poland < Soviet < USA; within a faction alphabetical by title
        assert ids == ["ger_inf_1", "pol_exile_tank", "sov_inf_1", "sov_tank_1", "usa_order"]


class TestFilters:
    def test_filter_by_faction(self, conn):
        result = query_cards(conn, CardFilters(factions=["Soviet"], include_exiles=False))
        assert _ids(result) == ["sov_inf_1", "sov_tank_1"]

    def test_filter_by_multiple_factions(self, conn):
        result = query_cards(conn, CardFilters(factions=["Germany", "USA"]))
        assert set(_ids(result)) == {"ger_inf_1", "usa_order"}

    def test_filter_by_type(self, conn):
        result = query_cards(conn, CardFilters(types=["infantry"]))
        assert set(_ids(result)) == {"sov_inf_1", "ger_inf_1"}

    def test_filter_by_rarity(self, conn):
        result = query_cards(conn, CardFilters(rarities=["Limited"]))
        assert _ids(result) == ["sov_tank_1"]

    def test_filter_by_set(self, conn):
        result = query_cards(conn, CardFilters(sets=["WorldAtWar"]))
        assert _ids(result) == ["sov_tank_1"]

    def test_filter_by_kredits(self, conn):
        result = query_cards(conn, CardFilters(kredits=[2]))
        assert set(_ids(result)) == {"sov_inf_1", "ger_inf_1"}

    def test_filter_by_kredits_multiple(self, conn):
        result = query_cards(conn, CardFilters(kredits=[3, 4]))
        assert set(_ids(result)) == {"sov_tank_1", "usa_order", "pol_exile_tank"}

    def test_text_search_matches_title_en(self, conn):
        result = query_cards(conn, CardFilters(text_query="rifles"), locale_key="en-EN")
        assert _ids(result) == ["sov_inf_1"]

    def test_text_search_matches_title_ru(self, conn):
        result = query_cards(conn, CardFilters(text_query="стрелки"), locale_key="ru-RU")
        assert _ids(result) == ["sov_inf_1"]

    def test_text_search_case_insensitive(self, conn):
        result = query_cards(conn, CardFilters(text_query="RIFLES"), locale_key="en-EN")
        assert _ids(result) == ["sov_inf_1"]

    def test_text_search_matches_text_en(self, conn):
        # "standard" appears in text_en of sov_inf_1 but not in its title or any other card
        result = query_cards(conn, CardFilters(text_query="standard"), locale_key="en-EN")
        assert _ids(result) == ["sov_inf_1"]

    def test_text_search_matches_text_ru(self, conn):
        # "обычные" appears in text_ru of sov_inf_1 — exact-case (SQLite LOWER is ASCII-only)
        result = query_cards(conn, CardFilters(text_query="обычные"), locale_key="ru-RU")
        assert _ids(result) == ["sov_inf_1"]

    def test_text_search_no_double_count(self, conn):
        # sov_inf_1 matches both title ("Soviet Rifles") and text ("standard rifles")
        # via the word "rifles" — must appear exactly once
        result = query_cards(conn, CardFilters(text_query="rifles"), locale_key="en-EN")
        assert _ids(result).count("sov_inf_1") == 1

    def test_text_search_cyrillic_case_insensitive(self, conn):
        # "Т-34" title in ru-RU; lowercase query "т-34" must match (SQLite LOWER is ASCII-only)
        result = query_cards(conn, CardFilters(text_query="т-34"), locale_key="ru-RU")
        assert "sov_tank_1" in _ids(result)

    def test_text_search_en_title_fallback_in_ru_locale(self, conn):
        # sov_tank_1 title_en="T-34" — searching "T-34" with ru-RU locale must still find it
        result = query_cards(conn, CardFilters(text_query="T-34"), locale_key="ru-RU")
        assert "sov_tank_1" in _ids(result)

    def test_owned_only(self, conn):
        result = query_cards(conn, CardFilters(owned_only=True))
        # quantities: sov_inf_1=2, sov_tank_1=0, ger_inf_1=3, usa_order=1
        assert set(_ids(result)) == {"sov_inf_1", "ger_inf_1", "usa_order"}

    def test_include_reserved_adds_reserved(self, conn):
        result = query_cards(conn, CardFilters(include_reserved=True))
        assert "reserved_card" in _ids(result)

    def test_include_spawnable_adds_spawnable(self, conn):
        result = query_cards(conn, CardFilters(include_spawnable=True))
        assert "spawnable_card" in _ids(result)

    def test_card_with_can_create_not_filtered_as_spawnable(self, conn):
        # sov_tank_1 has can_create=None in fixture; insert a card with can_create
        # set but set != OnlySpawnable — it must still appear without include_spawnable
        conn.execute(
            "UPDATE cards SET can_create = ? WHERE cardId = ?",
            ('["spawnable_card"]', "sov_tank_1"),
        )
        conn.commit()
        result = query_cards(conn, CardFilters())
        assert "sov_tank_1" in _ids(result)

    def test_filters_combined_with_and(self, conn):
        result = query_cards(
            conn,
            CardFilters(factions=["Soviet"], types=["tank"], include_exiles=False),
        )
        assert _ids(result) == ["sov_tank_1"]


class TestExileFilter:
    def test_include_exiles_defaults_to_true(self):
        assert CardFilters().include_exiles is True

    def test_faction_filter_includes_exiles_by_default(self, conn):
        # Filtering by Soviet surfaces the Polish exile tank (exile=Soviet),
        # the way the game client shows forces-in-exile in a nation's view.
        result = query_cards(conn, CardFilters(factions=["Soviet"]))
        assert "pol_exile_tank" in _ids(result)
        assert {"sov_inf_1", "sov_tank_1"} <= set(_ids(result))

    def test_exiles_off_excludes_them_from_faction_filter(self, conn):
        result = query_cards(conn, CardFilters(factions=["Soviet"], include_exiles=False))
        assert "pol_exile_tank" not in _ids(result)

    def test_exile_card_keeps_its_own_faction(self, conn):
        result = query_cards(conn, CardFilters(factions=["Soviet"]))
        row = next(r for r in result if r["cardId"] == "pol_exile_tank")
        assert row["faction"] == "Poland"

    def test_exiles_flag_is_inert_without_a_faction_filter(self, conn):
        # With no nation selected every card is already shown, so the toggle
        # changes nothing either way.
        on = _ids(query_cards(conn, CardFilters(include_exiles=True)))
        off = _ids(query_cards(conn, CardFilters(include_exiles=False)))
        assert on == off
        assert "pol_exile_tank" in on

    def test_exile_only_matches_the_selected_faction(self, conn):
        # The Polish tank's exile is Soviet, so a Germany filter must not pull it.
        result = query_cards(conn, CardFilters(factions=["Germany"]))
        assert "pol_exile_tank" not in _ids(result)


class TestAbilityFilter:
    def test_no_ability_filter_returns_all(self, conn):
        result = query_cards(conn, CardFilters())
        assert len(result) == 5

    def test_filter_by_single_ability(self, conn):
        result = query_cards(conn, CardFilters(abilities=["guard"]))
        assert _ids(result) == ["sov_tank_1"]

    def test_filter_by_multiple_abilities_uses_or(self, conn):
        result = query_cards(conn, CardFilters(abilities=["blitz", "guard"]))
        # blitz: sov_inf_1, usa_order; guard: sov_tank_1
        assert set(_ids(result)) == {"sov_inf_1", "sov_tank_1", "usa_order"}

    def test_filter_unknown_ability_silently_ignored(self, conn):
        # Unknown name not in KNOWN_ABILITIES → treated as if not provided
        result = query_cards(conn, CardFilters(abilities=["bogus_ability_x"]))
        assert len(result) == 5

    def test_unknown_mixed_with_known_keeps_known(self, conn):
        result = query_cards(conn, CardFilters(abilities=["guard", "bogus"]))
        assert _ids(result) == ["sov_tank_1"]

    def test_ability_combines_with_faction_via_and(self, conn):
        # Soviet ∩ blitz → only sov_inf_1 (usa_order has blitz but not Soviet)
        result = query_cards(
            conn,
            CardFilters(factions=["Soviet"], abilities=["blitz"]),
        )
        assert _ids(result) == ["sov_inf_1"]


class TestExtraAbilityFilter:
    @pytest.fixture
    def conn_with_extras(self, conn):
        # Mark sov_inf_1 with pincer; sov_tank_1 with resistance; usa_order with pincer
        conn.execute("UPDATE cards SET extra_ability_pincer = 1 WHERE cardId = ?", ("sov_inf_1",))
        conn.execute(
            "UPDATE cards SET extra_ability_resistance = 1 WHERE cardId = ?", ("sov_tank_1",)
        )
        conn.execute("UPDATE cards SET extra_ability_pincer = 1 WHERE cardId = ?", ("usa_order",))
        conn.commit()
        return conn

    def test_no_extra_ability_filter_returns_all(self, conn_with_extras):
        result = query_cards(conn_with_extras, CardFilters())
        assert len(result) == 5

    def test_filter_by_single_extra_ability(self, conn_with_extras):
        result = query_cards(conn_with_extras, CardFilters(extra_abilities=["resistance"]))
        assert _ids(result) == ["sov_tank_1"]

    def test_filter_by_multiple_extra_abilities_uses_or(self, conn_with_extras):
        result = query_cards(
            conn_with_extras, CardFilters(extra_abilities=["pincer", "resistance"])
        )
        # pincer: sov_inf_1, usa_order; resistance: sov_tank_1
        assert set(_ids(result)) == {"sov_inf_1", "sov_tank_1", "usa_order"}

    def test_filter_unknown_extra_ability_silently_ignored(self, conn_with_extras):
        result = query_cards(conn_with_extras, CardFilters(extra_abilities=["bogus_extra_x"]))
        assert len(result) == 5

    def test_extra_ability_combines_with_faction_via_and(self, conn_with_extras):
        # Soviet ∩ pincer → only sov_inf_1 (usa_order has pincer but not Soviet)
        result = query_cards(
            conn_with_extras,
            CardFilters(factions=["Soviet"], extra_abilities=["pincer"]),
        )
        assert _ids(result) == ["sov_inf_1"]

    def test_extra_ability_independent_from_ability(self, conn_with_extras):
        # ability=blitz (sov_inf_1, usa_order) AND extra=resistance (sov_tank_1):
        # intersection empty (no card has both)
        result = query_cards(
            conn_with_extras,
            CardFilters(abilities=["blitz"], extra_abilities=["resistance"]),
        )
        assert _ids(result) == []


class TestSort:
    def test_sort_by_kredits_asc(self, conn):
        result = query_cards(conn, CardFilters(), sort_col="kredits", sort_dir="asc")
        assert [r["kredits"] for r in result] == [2, 2, 3, 4, 4]

    def test_sort_by_kredits_desc(self, conn):
        result = query_cards(conn, CardFilters(), sort_col="kredits", sort_dir="desc")
        assert [r["kredits"] for r in result] == [4, 4, 3, 2, 2]

    def test_sort_by_title_uses_locale(self, conn):
        result = query_cards(
            conn, CardFilters(), sort_col="title", sort_dir="asc", locale_key="en-EN"
        )
        ids = _ids(result)
        # Air Strike < Soviet Rifles < T-34 < T-34 76 PL < Wehrmacht
        assert ids == ["usa_order", "sov_inf_1", "sov_tank_1", "pol_exile_tank", "ger_inf_1"]

    def test_invalid_sort_column_falls_back_to_default(self, conn):
        result = query_cards(conn, CardFilters(), sort_col="bogus", sort_dir="asc")
        # default sort = faction -> title
        assert _ids(result) == [
            "ger_inf_1",
            "pol_exile_tank",
            "sov_inf_1",
            "sov_tank_1",
            "usa_order",
        ]

    def test_invalid_sort_dir_falls_back_to_asc(self, conn):
        result_default = query_cards(conn, CardFilters(), sort_col="kredits", sort_dir="asc")
        result_bogus = query_cards(conn, CardFilters(), sort_col="kredits", sort_dir="bogus")
        assert _ids(result_default) == _ids(result_bogus)


class TestAllowedSortColumns:
    def test_allowed_columns_include_all_table_headers(self):
        # Every column we expose in the UI should be sortable
        expected = {
            "faction",
            "title",
            "type",
            "rarity",
            "set",
            "quantity",
            "kredits",
            "operationCost",
            "attack",
            "defense",
        }
        assert expected.issubset(ALLOWED_SORT_COLUMNS)
