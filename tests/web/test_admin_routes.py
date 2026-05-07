"""Admin-mode route tests for the kardscm webUI.

Covers:
- Admin endpoints exist only when admin=True (404 otherwise — isolation).
- GET edit form populates active-locale title/text decoded from JSON.
- POST save updates DB, returns refreshed row, and clears the modal via OOB.
- update_card_admin invalid input → 400.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kardscm.constants import KNOWN_ABILITIES
from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU
from kardscm.storage.database import get_connection, initialize_schema
from kardscm.web.app import create_app

_ZERO_ABILITIES = tuple(0 for _ in KNOWN_ABILITIES)
_ABILITY_COLS = ", ".join(f"ability_{a}" for a in KNOWN_ABILITIES)
_ABILITY_PLACEHOLDERS = ", ".join("?" for _ in KNOWN_ABILITIES)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    db_file = tmp_path / "admin.db"
    conn = get_connection(db_file)
    initialize_schema(conn)
    cards = [
        (
            "sov_inf",
            "",
            "",
            "",
            "Soviet",
            "infantry",
            "Standard",
            "Base",
            json.dumps(
                {"en-EN": "Soviet Rifles", "ru-RU": "Советские стрелки"},
                ensure_ascii=False,
            ),
            json.dumps(
                {"en-EN": "Bang.", "ru-RU": "Бах."},
                ensure_ascii=False,
            ),
            2,
            1,
            2,
            *_ZERO_ABILITIES,
            None,
            0,
            "",
            None,
            None,
            1,
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


def _admin_client(db_path: Path, lang_config=LANGUAGE_EN) -> TestClient:
    app = create_app(
        db_path,
        lang_config=lang_config,
        admin=True,
        backup_path=db_path.with_suffix(".db.bak.test"),
    )
    return TestClient(app)


def _user_client(db_path: Path) -> TestClient:
    app = create_app(db_path, lang_config=LANGUAGE_EN, admin=False)
    return TestClient(app)


class TestAdminIsolation:
    """Without --admin the admin endpoints must not be registered at all."""

    def test_admin_edit_form_is_404_in_user_mode(self, db_path: Path) -> None:
        r = _user_client(db_path).get("/admin/cards/sov_inf/edit")
        assert r.status_code == 404

    def test_admin_save_is_404_in_user_mode(self, db_path: Path) -> None:
        r = _user_client(db_path).post(
            "/admin/cards/sov_inf",
            data={"faction": "Soviet"},
        )
        assert r.status_code == 404


class TestAdminBanner:
    def test_banner_visible_in_admin_mode(self, db_path: Path) -> None:
        r = _admin_client(db_path).get("/")
        assert "admin-banner" in r.text
        assert "ADMIN MODE" in r.text

    def test_banner_includes_backup_path(self, db_path: Path) -> None:
        r = _admin_client(db_path).get("/")
        assert ".db.bak.test" in r.text

    def test_banner_absent_in_user_mode(self, db_path: Path) -> None:
        r = _user_client(db_path).get("/")
        assert "admin-banner" not in r.text


class TestAdminEditMode:
    def test_admin_forces_edit_mode(self, db_path: Path) -> None:
        # Admin mode renders quantity inputs without any cookie.
        r = _admin_client(db_path).get("/")
        assert 'name="quantity"' in r.text

    def test_admin_row_links_to_admin_edit(self, db_path: Path) -> None:
        r = _admin_client(db_path).get("/")
        assert "/admin/cards/sov_inf/edit" in r.text

    def test_user_row_links_to_readonly_modal(self, db_path: Path) -> None:
        r = _user_client(db_path).get("/")
        assert "/admin/cards/sov_inf/edit" not in r.text
        assert 'hx-get="/cards/sov_inf"' in r.text


class TestAdminEditForm:
    def test_form_populates_active_locale_title(self, db_path: Path) -> None:
        r = _admin_client(db_path).get("/admin/cards/sov_inf/edit")
        assert r.status_code == 200
        # English title is decoded into the input value, not raw JSON.
        assert "Soviet Rifles" in r.text
        assert '"en-EN"' not in r.text

    def test_form_populates_ru_locale_when_lang_ru(self, db_path: Path) -> None:
        r = _admin_client(db_path, lang_config=LANGUAGE_RU).get("/admin/cards/sov_inf/edit")
        assert r.status_code == 200
        assert "Советские стрелки" in r.text

    def test_form_lists_all_factions(self, db_path: Path) -> None:
        r = _admin_client(db_path).get("/admin/cards/sov_inf/edit")
        for faction in ("Soviet", "USA", "Germany", "Japan"):
            assert f'value="{faction}"' in r.text

    def test_form_lists_all_abilities(self, db_path: Path) -> None:
        r = _admin_client(db_path).get("/admin/cards/sov_inf/edit")
        for ability in ("ability_blitz", "ability_guard", "ability_heavyArmor1"):
            assert f'name="{ability}"' in r.text

    def test_form_404_for_unknown_card(self, db_path: Path) -> None:
        r = _admin_client(db_path).get("/admin/cards/no_such/edit")
        assert r.status_code == 404


class TestAdminSave:
    def _full_form(self, **overrides) -> dict:
        base = {
            "title_localized": "Soviet Rifles",
            "text_localized": "Bang.",
            "faction": "Soviet",
            "type": "infantry",
            "rarity": "Standard",
            "set": "Base",
            "kredits": "2",
            "attack": "1",
            "defense": "2",
            "operationCost": "",
        }
        base.update(overrides)
        return base

    def test_updates_numeric_field(self, db_path: Path) -> None:
        r = _admin_client(db_path).post(
            "/admin/cards/sov_inf",
            data=self._full_form(attack="9"),
        )
        assert r.status_code == 200
        with get_connection(db_path) as conn:
            (val,) = conn.execute(
                "SELECT attack FROM cards WHERE cardId = ?", ("sov_inf",)
            ).fetchone()
        assert val == 9

    def test_updates_ability_checkbox(self, db_path: Path) -> None:
        r = _admin_client(db_path).post(
            "/admin/cards/sov_inf",
            data=self._full_form(ability_blitz="1"),
        )
        assert r.status_code == 200
        with get_connection(db_path) as conn:
            (val,) = conn.execute(
                "SELECT ability_blitz FROM cards WHERE cardId = ?", ("sov_inf",)
            ).fetchone()
        assert val == 1

    def test_unchecked_ability_clears_column(self, db_path: Path) -> None:
        # Pre-set the ability, then post a form that omits it (== unchecked).
        with get_connection(db_path) as conn:
            conn.execute("UPDATE cards SET ability_blitz = 1 WHERE cardId = ?", ("sov_inf",))
            conn.commit()
        _admin_client(db_path).post("/admin/cards/sov_inf", data=self._full_form())
        with get_connection(db_path) as conn:
            (val,) = conn.execute(
                "SELECT ability_blitz FROM cards WHERE cardId = ?", ("sov_inf",)
            ).fetchone()
        assert val == 0

    def test_updates_only_active_locale_title(self, db_path: Path) -> None:
        # Submit RU title; EN must not change.
        r = _admin_client(db_path, lang_config=LANGUAGE_RU).post(
            "/admin/cards/sov_inf",
            data=self._full_form(title_localized="Советские бойцы"),
        )
        assert r.status_code == 200
        with get_connection(db_path) as conn:
            (raw,) = conn.execute(
                "SELECT title FROM cards WHERE cardId = ?", ("sov_inf",)
            ).fetchone()
        decoded = json.loads(raw)
        assert decoded["ru-RU"] == "Советские бойцы"
        assert decoded["en-EN"] == "Soviet Rifles"

    def test_empty_text_allowed(self, db_path: Path) -> None:
        r = _admin_client(db_path).post(
            "/admin/cards/sov_inf",
            data=self._full_form(text_localized=""),
        )
        assert r.status_code == 200
        with get_connection(db_path) as conn:
            (raw,) = conn.execute(
                "SELECT text FROM cards WHERE cardId = ?", ("sov_inf",)
            ).fetchone()
        decoded = json.loads(raw)
        assert decoded["en-EN"] == ""

    def test_empty_title_rejected(self, db_path: Path) -> None:
        r = _admin_client(db_path).post(
            "/admin/cards/sov_inf",
            data=self._full_form(title_localized=""),
        )
        assert r.status_code == 400

    def test_invalid_faction_rejected(self, db_path: Path) -> None:
        r = _admin_client(db_path).post(
            "/admin/cards/sov_inf",
            data=self._full_form(faction="Atlantis"),
        )
        assert r.status_code == 400

    def test_negative_attack_rejected(self, db_path: Path) -> None:
        r = _admin_client(db_path).post(
            "/admin/cards/sov_inf",
            data=self._full_form(attack="-1"),
        )
        assert r.status_code == 400

    def test_save_returns_refreshed_row_with_oob_modal_clear(self, db_path: Path) -> None:
        r = _admin_client(db_path).post(
            "/admin/cards/sov_inf",
            data=self._full_form(attack="7"),
        )
        assert r.status_code == 200
        # Row outerHTML for the swap target.
        assert 'id="card-row-sov_inf"' in r.text
        # OOB swap that clears #modal.
        assert 'id="modal"' in r.text and 'hx-swap-oob="innerHTML"' in r.text

    def test_save_unknown_card_404(self, db_path: Path) -> None:
        r = _admin_client(db_path).post(
            "/admin/cards/no_such",
            data=self._full_form(),
        )
        assert r.status_code == 404
