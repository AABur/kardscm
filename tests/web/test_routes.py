"""End-to-end route tests for the kardscm webUI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kardscm.config import LANGUAGE_EN, LANGUAGE_RU
from kardscm.storage.database import get_connection, initialize_schema
from kardscm.web.app import _resolve_lang, create_app


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    db_file = tmp_path / "test.db"
    conn = get_connection(db_file)
    initialize_schema(conn)
    cards = [
        (
            "sov_inf",
            "",  # importId
            "/images/card/sov_inf.avif",  # imageUrl
            "/images/card/thumb/sov_inf.avif",  # thumbUrl
            "Soviet",
            "infantry",
            "Standard",
            "Base",
            json.dumps({"en-EN": "Soviet Rifles", "ru-RU": "Советские стрелки"}),
            json.dumps({"en-EN": "Standard rifles.", "ru-RU": "Обычные стрелки."}),
            2,
            1,
            2,
            json.dumps([]),
            None,
            0,
            "",
            None,
            None,
            2,
        ),
        (
            "ger_tank",
            "",
            "",
            "",
            "Germany",
            "tank",
            "Limited",
            "WorldAtWar",
            json.dumps({"en-EN": "Panzer", "ru-RU": "Танк"}),
            json.dumps({"en-EN": "A tank.", "ru-RU": "Танк."}),
            4,
            3,
            5,
            json.dumps(["heavyArmor1"]),
            None,
            0,
            "",
            None,
            None,
            0,
        ),
        (
            "reserved_card",
            "",
            "",
            "",
            "Soviet",
            "infantry",
            "Standard",
            "Base",
            json.dumps({"en-EN": "Reserved", "ru-RU": "Резерв"}),
            json.dumps({"en-EN": "", "ru-RU": ""}),
            1,
            1,
            1,
            json.dumps([]),
            None,
            1,  # reserved
            "",
            None,
            None,
            0,
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
        cards,
    )
    conn.commit()
    conn.close()
    return db_file


@pytest.fixture
def client(db_path: Path) -> TestClient:
    app = create_app(db_path, lang_config=LANGUAGE_EN)
    return TestClient(app)


class TestHealth:
    def test_healthz(self, client: TestClient) -> None:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestIndex:
    def test_index_renders_table(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert "<table" in r.text
        assert "Soviet Rifles" in r.text
        assert "Panzer" in r.text
        # reserved excluded by default
        assert "Reserved" not in r.text

    def test_index_includes_filter_form(self, client: TestClient) -> None:
        r = client.get("/")
        assert 'id="filters"' in r.text
        assert 'name="factions"' in r.text
        assert 'name="q"' in r.text

    def test_index_counter_visible(self, client: TestClient) -> None:
        r = client.get("/")
        # 2 visible (reserved excluded) of 3 total
        assert "2 / 3" in r.text


class TestCardsPartial:
    def test_cards_partial_returns_table_only(self, client: TestClient) -> None:
        r = client.get("/cards")
        assert r.status_code == 200
        # No <html> wrapper — partial response
        assert "<!doctype html>" not in r.text.lower()
        assert "<table" in r.text

    def test_cards_partial_includes_oob_counter(self, client: TestClient) -> None:
        r = client.get("/cards")
        assert 'id="counter"' in r.text
        assert 'hx-swap-oob="true"' in r.text

    def test_filter_by_faction(self, client: TestClient) -> None:
        r = client.get("/cards", params={"factions": "Soviet"})
        assert "Soviet Rifles" in r.text
        assert "Panzer" not in r.text

    def test_filter_text_search(self, client: TestClient) -> None:
        r = client.get("/cards", params={"q": "Panzer"})
        assert "Panzer" in r.text
        assert "Soviet Rifles" not in r.text

    def test_owned_only_excludes_zero_qty(self, client: TestClient) -> None:
        r = client.get("/cards", params={"owned": "true"})
        assert "Soviet Rifles" in r.text  # qty=2
        assert "Panzer" not in r.text  # qty=0

    def test_include_reserved(self, client: TestClient) -> None:
        r = client.get("/cards", params={"reserved": "true"})
        assert "Reserved" in r.text


class TestQuantityUpdate:
    def test_update_quantity_persists(self, client: TestClient, db_path: Path) -> None:
        r = client.post("/cards/sov_inf/quantity", data={"quantity": 3})
        assert r.status_code == 200
        # Response is the updated <td>
        assert 'value="3"' in r.text
        assert 'name="quantity"' in r.text
        # Persistence
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT quantity FROM cards WHERE cardId = ?", ("sov_inf",)
            ).fetchone()
        assert row[0] == 3

    def test_update_quantity_clamps_negative_to_zero(self, client: TestClient) -> None:
        r = client.post("/cards/sov_inf/quantity", data={"quantity": -5})
        assert r.status_code == 200
        assert 'value="0"' in r.text

    def test_update_quantity_unknown_card(self, client: TestClient) -> None:
        r = client.post("/cards/no_such_card/quantity", data={"quantity": 1})
        assert r.status_code == 404


class TestCardModal:
    def test_modal_renders(self, client: TestClient) -> None:
        r = client.get("/cards/sov_inf")
        assert r.status_code == 200
        assert "Soviet Rifles" in r.text
        assert "Standard rifles." in r.text
        assert "modal-backdrop" in r.text

    def test_modal_unknown_card(self, client: TestClient) -> None:
        r = client.get("/cards/no_such_card")
        assert r.status_code == 404


class TestI18n:
    def test_index_uses_en_strings_with_en_config(self, client: TestClient) -> None:
        r = client.get("/")
        # English UI strings appear when LANGUAGE_EN is active
        assert LANGUAGE_EN.ui_strings["page_title"] in r.text
        assert LANGUAGE_EN.ui_strings["search_placeholder"] in r.text
        assert LANGUAGE_EN.ui_strings["toggle_owned"] in r.text
        assert LANGUAGE_EN.ui_strings["col_cost"] in r.text
        # Russian UI strings should not leak
        assert LANGUAGE_RU.ui_strings["page_title"] not in r.text

    def test_index_uses_ru_strings_with_ru_config(self, db_path: Path) -> None:
        ru_app = create_app(db_path, lang_config=LANGUAGE_RU)
        ru_client = TestClient(ru_app)
        r = ru_client.get("/")
        assert LANGUAGE_RU.ui_strings["page_title"] in r.text
        assert LANGUAGE_RU.ui_strings["search_placeholder"] in r.text
        assert LANGUAGE_RU.ui_strings["toggle_owned"] in r.text
        assert LANGUAGE_RU.ui_strings["col_cost"] in r.text
        # English chrome should not leak
        assert LANGUAGE_EN.ui_strings["page_title"] not in r.text

    def test_qty_cell_has_settle_delay_for_save_flash(self, client: TestClient) -> None:
        # The qty cell rendered in the table partial should include the settle
        # window so the green flash CSS has time to be visible after save.
        r = client.get("/cards")
        assert "settle:600ms" in r.text

    def test_modal_uses_translated_card_id_label(self, client: TestClient) -> None:
        r = client.get("/cards/sov_inf")
        assert LANGUAGE_EN.ui_strings["card_id_label"] in r.text


class TestResolveLang:
    def test_none_returns_none(self) -> None:
        assert _resolve_lang(None) is None
        assert _resolve_lang("") is None

    def test_known_codes_return_configs(self) -> None:
        assert _resolve_lang("en") is LANGUAGE_EN
        assert _resolve_lang("ru") is LANGUAGE_RU

    def test_known_codes_case_insensitive(self) -> None:
        assert _resolve_lang("EN") is LANGUAGE_EN
        assert _resolve_lang("Ru") is LANGUAGE_RU

    def test_unknown_code_raises_systemexit(self) -> None:
        with pytest.raises(SystemExit):
            _resolve_lang("zz")
