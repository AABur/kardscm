"""End-to-end route tests for the kardscm webUI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kardscm.constants import KNOWN_ABILITIES
from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU
from kardscm.storage.database import get_connection, initialize_schema
from kardscm.web.app import _resolve_lang, create_app

_ZERO_ABILITIES = tuple(0 for _ in KNOWN_ABILITIES)
_ABILITY_COLS = ", ".join(f"ability_{a}" for a in KNOWN_ABILITIES)
_ABILITY_PLACEHOLDERS = ", ".join("?" for _ in KNOWN_ABILITIES)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    db_file = tmp_path / "test.db"
    conn = get_connection(db_file)
    initialize_schema(conn)
    _ha1 = tuple(1 if a == "heavyArmor1" else 0 for a in KNOWN_ABILITIES)
    _blitz = tuple(1 if a == "blitz" else 0 for a in KNOWN_ABILITIES)
    cards = [
        (
            "sov_inf",
            "",
            "/images/card/sov_inf.avif",
            "/images/card/thumb/sov_inf.avif",
            "Soviet",
            "infantry",
            "Standard",
            "Base",
            json.dumps({"en-EN": "Soviet Rifles", "ru-RU": "Советские стрелки"}),
            json.dumps({"en-EN": "Standard rifles.", "ru-RU": "Обычные стрелки."}),
            2,
            1,
            2,
            *_blitz,
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
            *_ha1,
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
            *_ZERO_ABILITIES,
            None,
            1,
            "",
            None,
            None,
            0,
        ),
    ]
    conn.executemany(
        f"""
        INSERT INTO cards (
            cardId, importId, imageUrl, thumbUrl,
            faction, type, rarity, "set",
            title, text, kredits, attack, defense,
            {_ABILITY_COLS},
            operationCost, reserved,
            image, can_create, exile, quantity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {_ABILITY_PLACEHOLDERS}, ?, ?, ?, ?, ?, ?)
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
        assert 'name="abilities"' in r.text
        assert 'name="extra_abilities"' in r.text
        assert 'name="q"' in r.text

    def test_index_renders_extra_ability_chip_labels(self, client: TestClient) -> None:
        r = client.get("/")
        # English labels from LANGUAGE_EN.extra_ability_names
        assert "Pincer" in r.text
        assert "Resistance" in r.text

    def test_index_renders_ability_chip_labels(self, client: TestClient) -> None:
        r = client.get("/")
        # English labels from LANGUAGE_EN.ability_names
        assert "Blitz" in r.text
        assert "Guard" in r.text

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

    def test_filter_text_search_by_description(self, client: TestClient) -> None:
        # "Standard rifles." is in text_en of sov_inf, not in its title
        r = client.get("/cards", params={"q": "Standard rifles."})
        assert "Soviet Rifles" in r.text
        assert "Panzer" not in r.text

    def test_owned_only_excludes_zero_qty(self, client: TestClient) -> None:
        r = client.get("/cards", params={"owned": "true"})
        assert "Soviet Rifles" in r.text  # qty=2
        assert "Panzer" not in r.text  # qty=0

    def test_include_reserved(self, client: TestClient) -> None:
        r = client.get("/cards", params={"reserved": "true"})
        assert "Reserved" in r.text

    def test_filter_by_single_ability(self, client: TestClient) -> None:
        r = client.get("/cards", params={"abilities": "blitz"})
        # sov_inf has blitz; ger_tank has heavyArmor1 only
        assert "Soviet Rifles" in r.text
        assert "Panzer" not in r.text

    def test_filter_by_multiple_abilities_or(self, client: TestClient) -> None:
        r = client.get("/cards", params=[("abilities", "blitz"), ("abilities", "heavyArmor1")])
        assert "Soviet Rifles" in r.text
        assert "Panzer" in r.text

    def test_filter_by_unknown_ability_ignored(self, client: TestClient) -> None:
        r = client.get("/cards", params={"abilities": "bogus"})
        # Unknown ability → no filter → both visible
        assert "Soviet Rifles" in r.text
        assert "Panzer" in r.text

    def test_filter_by_extra_ability(self, client: TestClient, db_path: Path) -> None:
        # Mark sov_inf with pincer extra ability
        with get_connection(db_path) as conn:
            conn.execute("UPDATE cards SET extra_ability_pincer = 1 WHERE cardId = ?", ("sov_inf",))
            conn.commit()
        r = client.get("/cards", params={"extra_abilities": "pincer"})
        assert "Soviet Rifles" in r.text
        assert "Panzer" not in r.text

    def test_filter_by_multiple_extra_abilities_or(self, client: TestClient, db_path: Path) -> None:
        with get_connection(db_path) as conn:
            conn.execute("UPDATE cards SET extra_ability_pincer = 1 WHERE cardId = ?", ("sov_inf",))
            conn.execute(
                "UPDATE cards SET extra_ability_resistance = 1 WHERE cardId = ?", ("ger_tank",)
            )
            conn.commit()
        r = client.get(
            "/cards",
            params=[("extra_abilities", "pincer"), ("extra_abilities", "resistance")],
        )
        assert "Soviet Rifles" in r.text
        assert "Panzer" in r.text


class TestQuantityUpdate:
    def test_update_quantity_persists(self, client: TestClient, db_path: Path) -> None:
        # Quantity edits must work regardless of edit_mode cookie — the toggle
        # is a UI affordance, not a server-side gate (localhost only).
        r = client.post(
            "/cards/sov_inf/quantity",
            data={"quantity": 3},
            cookies={"kardscm_edit": "1"},
        )
        assert r.status_code == 200
        assert 'value="3"' in r.text
        assert 'name="quantity"' in r.text
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT quantity FROM cards WHERE cardId = ?", ("sov_inf",)
            ).fetchone()
        assert row[0] == 3

    def test_update_quantity_clamps_negative_to_zero(self, client: TestClient) -> None:
        r = client.post(
            "/cards/sov_inf/quantity",
            data={"quantity": -5},
            cookies={"kardscm_edit": "1"},
        )
        assert r.status_code == 200
        assert 'value="0"' in r.text

    def test_update_quantity_unknown_card(self, client: TestClient) -> None:
        r = client.post("/cards/no_such_card/quantity", data={"quantity": 1})
        assert r.status_code == 404

    def test_update_quantity_clamps_above_rarity_max(
        self, client: TestClient, db_path: Path
    ) -> None:
        # sov_inf is Standard (max 4) — posting 99 should clamp to 4.
        r = client.post(
            "/cards/sov_inf/quantity",
            data={"quantity": 99},
            cookies={"kardscm_edit": "1"},
        )
        assert r.status_code == 200
        assert 'value="4"' in r.text
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT quantity FROM cards WHERE cardId = ?", ("sov_inf",)
            ).fetchone()
        assert row[0] == 4

    def test_update_quantity_clamps_limited_to_three(
        self, client: TestClient, db_path: Path
    ) -> None:
        # ger_tank is Limited (max 3) — posting 99 should clamp to 3.
        r = client.post(
            "/cards/ger_tank/quantity",
            data={"quantity": 99},
            cookies={"kardscm_edit": "1"},
        )
        assert r.status_code == 200
        assert 'value="3"' in r.text
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT quantity FROM cards WHERE cardId = ?", ("ger_tank",)
            ).fetchone()
        assert row[0] == 3

    def test_qty_cell_max_attr_reflects_rarity(self, client: TestClient) -> None:
        # Standard card — input max should be 4.
        r = client.get("/", cookies={"kardscm_edit": "1"})
        assert 'max="4"' in r.text

    def test_qty_cell_is_readonly_without_cookie(self, client: TestClient) -> None:
        # Default page: edit_mode is off, qty cells render as plain numbers.
        r = client.get("/")
        assert 'name="quantity"' not in r.text

    def test_qty_cell_is_editable_with_cookie(self, client: TestClient) -> None:
        r = client.get("/", cookies={"kardscm_edit": "1"})
        assert 'name="quantity"' in r.text
        assert "settle:600ms" in r.text


class TestEditToggle:
    def test_start_edit_sets_cookie(self, client: TestClient) -> None:
        r = client.post("/start-edit", headers={"HX-Current-URL": "/"})
        assert r.status_code == 200
        assert "kardscm_edit=1" in r.headers.get("set-cookie", "")

    def test_start_edit_hx_redirects_to_current_url(self, client: TestClient) -> None:
        r = client.post(
            "/start-edit",
            headers={"HX-Current-URL": "/?factions=Soviet"},
        )
        assert r.headers.get("HX-Redirect") == "/?factions=Soviet"

    def test_request_save_redirects_when_no_changes(self, client: TestClient) -> None:
        # Enter edit mode (takes snapshot), then immediately request save → no diff.
        client.post("/start-edit", headers={"HX-Current-URL": "/"})
        r = client.post(
            "/request-save",
            headers={"HX-Current-URL": "/"},
            cookies={"kardscm_edit": "1"},
        )
        assert r.status_code == 200
        assert "kardscm_edit=0" in r.headers.get("set-cookie", "")
        assert r.headers.get("HX-Redirect") == "/"

    def test_request_save_returns_modal_when_changes_exist(
        self, client: TestClient, db_path: Path
    ) -> None:
        # Start edit (snapshot: sov_inf qty=2), change it, then request-save.
        client.post("/start-edit", headers={"HX-Current-URL": "/"})
        client.post("/cards/sov_inf/quantity", data={"quantity": 4})
        r = client.post(
            "/request-save",
            headers={"HX-Current-URL": "/"},
            cookies={"kardscm_edit": "1"},
        )
        assert r.status_code == 200
        assert "modal-backdrop" in r.text
        assert "Soviet Rifles" in r.text
        # Before/after columns present
        assert "2" in r.text  # qty_before
        assert "4" in r.text  # qty_after

    def test_confirm_save_clears_cookie(self, client: TestClient) -> None:
        r = client.post("/confirm-save")
        assert r.status_code == 200
        assert "kardscm_edit=0" in r.headers.get("set-cookie", "")
        assert r.headers.get("HX-Redirect") == "/"

    def test_undo_save_restores_quantities(self, client: TestClient, db_path: Path) -> None:
        # Snapshot at qty=2, change to 4, then undo → back to 2.
        client.post("/start-edit", headers={"HX-Current-URL": "/"})
        client.post("/cards/sov_inf/quantity", data={"quantity": 4})
        r = client.post("/undo-save")
        assert r.status_code == 200
        assert "kardscm_edit=0" in r.headers.get("set-cookie", "")
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT quantity FROM cards WHERE cardId = ?", ("sov_inf",)
            ).fetchone()
        assert row[0] == 2

    def test_close_save_modal_returns_empty(self, client: TestClient) -> None:
        r = client.post("/close-save-modal")
        assert r.status_code == 200
        assert r.text == ""


class TestEditToggleButtonRender:
    def test_toggle_button_visible_in_user_mode(self, client: TestClient) -> None:
        r = client.get("/")
        assert "/start-edit" in r.text
        assert "edit-toggle" in r.text

    def test_save_button_visible_in_edit_mode(self, client: TestClient) -> None:
        r = client.get("/", cookies={"kardscm_edit": "1"})
        assert "/request-save" in r.text
        assert "edit-toggle on" in r.text

    def test_toggle_button_hidden_in_admin_mode(self, db_path: Path) -> None:
        from kardscm.web.app import create_app

        admin_app = create_app(
            db_path,
            lang_config=LANGUAGE_EN,
            admin=True,
            backup_path=db_path.with_suffix(".db.bak.test"),
        )
        admin_client = TestClient(admin_app)
        r = admin_client.get("/")
        assert "/start-edit" not in r.text
        assert "/request-save" not in r.text


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

    def test_unknown_code_falls_back_to_english(self) -> None:
        # Unknown codes log a warning and fall back to English (no SystemExit).
        assert _resolve_lang("zz") is LANGUAGE_EN

    def test_compound_code_matches_case_sensitively(self) -> None:
        # 'RU' (uppercase) is not a registry key — falls back to English.
        assert _resolve_lang("RU") is LANGUAGE_EN


class TestLocaleWarningStrip:
    def test_strip_visible_when_warnings_present(self, db_path: Path) -> None:
        from dataclasses import replace

        cfg = replace(LANGUAGE_EN, fallback_warnings=["abilities.mobilize"])
        app = create_app(db_path, lang_config=cfg)
        client = TestClient(app)
        r = client.get("/")
        assert r.status_code == 200
        assert 'class="locale-warning-strip"' in r.text
        assert "abilities.mobilize" in r.text

    def test_strip_absent_when_no_warnings(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert "locale-warning-strip" not in r.text
