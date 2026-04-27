"""Tests for kardscm.web.queries — filter/sort SQL builder."""

from __future__ import annotations

import json
import sqlite3

import pytest

from kardscm.storage.database import initialize_schema
from kardscm.web.queries import ALLOWED_SORT_COLUMNS, CardFilters, query_cards


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
    attributes: list[str] | None = None,
    operation_cost: int | None = None,
    reserved: int = 0,
    can_create: str | None = None,
    quantity: int = 0,
) -> tuple:
    title = json.dumps({"en-EN": title_en, "ru-RU": title_ru})
    text = json.dumps({"en-EN": text_en, "ru-RU": text_ru})
    attrs = json.dumps(attributes or [])
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
        attrs,
        operation_cost,
        reserved,
        "",  # image
        can_create,
        None,  # exile
        quantity,
    )


@pytest.fixture
def conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
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
            title_en="Spawned Card",
            title_ru="Спаунованная карта",
            can_create='["sov_tank_1"]',
            quantity=0,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO cards (
            cardId, importId, imageUrl, thumbUrl,
            faction, type, rarity, "set",
            title, text, kredits, attack, defense,
            attributes, operationCost, reserved,
            image, can_create, exile, quantity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        assert len(result) == 4

    def test_default_sort_is_faction_then_title(self, conn):
        result = query_cards(conn, CardFilters(), locale_key="en-EN")
        ids = _ids(result)
        # Germany < Soviet < USA; within Soviet alphabetical by title
        assert ids == ["ger_inf_1", "sov_inf_1", "sov_tank_1", "usa_order"]


class TestFilters:
    def test_filter_by_faction(self, conn):
        result = query_cards(conn, CardFilters(factions=["Soviet"]))
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
        assert set(_ids(result)) == {"sov_tank_1", "usa_order"}

    def test_text_search_matches_title_en(self, conn):
        result = query_cards(conn, CardFilters(text_query="rifles"), locale_key="en-EN")
        assert _ids(result) == ["sov_inf_1"]

    def test_text_search_matches_title_ru(self, conn):
        result = query_cards(conn, CardFilters(text_query="стрелки"), locale_key="ru-RU")
        assert _ids(result) == ["sov_inf_1"]

    def test_text_search_case_insensitive(self, conn):
        result = query_cards(conn, CardFilters(text_query="RIFLES"), locale_key="en-EN")
        assert _ids(result) == ["sov_inf_1"]

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

    def test_filters_combined_with_and(self, conn):
        result = query_cards(
            conn,
            CardFilters(factions=["Soviet"], types=["tank"]),
        )
        assert _ids(result) == ["sov_tank_1"]


class TestSort:
    def test_sort_by_kredits_asc(self, conn):
        result = query_cards(conn, CardFilters(), sort_col="kredits", sort_dir="asc")
        assert [r["kredits"] for r in result] == [2, 2, 3, 4]

    def test_sort_by_kredits_desc(self, conn):
        result = query_cards(conn, CardFilters(), sort_col="kredits", sort_dir="desc")
        assert [r["kredits"] for r in result] == [4, 3, 2, 2]

    def test_sort_by_title_uses_locale(self, conn):
        result = query_cards(
            conn, CardFilters(), sort_col="title", sort_dir="asc", locale_key="en-EN"
        )
        ids = _ids(result)
        # Air Strike < Soviet Rifles < T-34 < Wehrmacht
        assert ids == ["usa_order", "sov_inf_1", "sov_tank_1", "ger_inf_1"]

    def test_invalid_sort_column_falls_back_to_default(self, conn):
        result = query_cards(conn, CardFilters(), sort_col="bogus", sort_dir="asc")
        # default sort = faction -> title
        assert _ids(result) == ["ger_inf_1", "sov_inf_1", "sov_tank_1", "usa_order"]

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
