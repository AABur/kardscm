"""Tests for admin-mode storage helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kardscm.storage import (
    backup_database,
    get_connection,
    initialize_schema,
    update_card_admin,
)


def _seed_card(conn) -> None:
    conn.execute(
        """
        INSERT INTO cards (
            cardId, faction, type, rarity, "set",
            title, text, kredits, attack, defense, reserved
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "card-1",
            "Soviet",
            "infantry",
            "Standard",
            "Base",
            json.dumps({"en-EN": "Soldier", "ru-RU": "Солдат"}, ensure_ascii=False),
            json.dumps({"en-EN": "Bang.", "ru-RU": "Бах."}, ensure_ascii=False),
            1,
            2,
            3,
            0,
        ),
    )
    conn.commit()


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "admin.db"
    conn = get_connection(path)
    initialize_schema(conn)
    _seed_card(conn)
    conn.close()
    return path


class TestBackupDatabase:
    def test_creates_sibling_file_with_timestamped_suffix(self, db_path: Path) -> None:
        backup = backup_database(db_path)
        assert backup.exists()
        assert backup.parent == db_path.parent
        assert backup.name.startswith(db_path.name + ".bak.")

    def test_backup_is_real_copy(self, db_path: Path) -> None:
        backup = backup_database(db_path)
        with get_connection(backup) as conn:
            row = conn.execute("SELECT cardId FROM cards").fetchone()
        assert row[0] == "card-1"

    def test_missing_db_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            backup_database(tmp_path / "missing.db")

    def test_rapid_backups_produce_unique_names(self, db_path: Path) -> None:
        b1 = backup_database(db_path)
        b2 = backup_database(db_path)
        assert b1 != b2


class TestUpdateCardAdmin:
    def test_updates_scalar_columns(self, db_path: Path) -> None:
        with get_connection(db_path) as conn:
            update_card_admin(
                conn,
                "card-1",
                {"attack": 9, "defense": 4, "kredits": 7},
                locale_key="en-EN",
            )
            conn.commit()
            row = conn.execute(
                "SELECT attack, defense, kredits FROM cards WHERE cardId = ?",
                ("card-1",),
            ).fetchone()
        assert row == (9, 4, 7)

    def test_merges_only_active_locale_in_title(self, db_path: Path) -> None:
        with get_connection(db_path) as conn:
            update_card_admin(
                conn,
                "card-1",
                {"title": "Воин"},
                locale_key="ru-RU",
            )
            conn.commit()
            (raw_title,) = conn.execute(
                "SELECT title FROM cards WHERE cardId = ?", ("card-1",)
            ).fetchone()
        decoded = json.loads(raw_title)
        assert decoded["ru-RU"] == "Воин"
        assert decoded["en-EN"] == "Soldier"

    def test_merges_only_active_locale_in_text(self, db_path: Path) -> None:
        with get_connection(db_path) as conn:
            update_card_admin(
                conn,
                "card-1",
                {"text": "Stomp."},
                locale_key="en-EN",
            )
            conn.commit()
            (raw_text,) = conn.execute(
                "SELECT text FROM cards WHERE cardId = ?", ("card-1",)
            ).fetchone()
        decoded = json.loads(raw_text)
        assert decoded["en-EN"] == "Stomp."
        assert decoded["ru-RU"] == "Бах."

    def test_empty_text_allowed(self, db_path: Path) -> None:
        with get_connection(db_path) as conn:
            update_card_admin(
                conn,
                "card-1",
                {"text": ""},
                locale_key="en-EN",
            )
            conn.commit()
            (raw_text,) = conn.execute(
                "SELECT text FROM cards WHERE cardId = ?", ("card-1",)
            ).fetchone()
        decoded = json.loads(raw_text)
        assert decoded["en-EN"] == ""

    def test_updates_ability_column(self, db_path: Path) -> None:
        with get_connection(db_path) as conn:
            update_card_admin(
                conn,
                "card-1",
                {"ability_blitz": 1},
                locale_key="en-EN",
            )
            conn.commit()
            (val,) = conn.execute(
                "SELECT ability_blitz FROM cards WHERE cardId = ?", ("card-1",)
            ).fetchone()
        assert val == 1

    def test_updates_extra_ability_column(self, db_path: Path) -> None:
        with get_connection(db_path) as conn:
            update_card_admin(
                conn,
                "card-1",
                {"extra_ability_pincer": 1},
                locale_key="en-EN",
            )
            conn.commit()
            (val,) = conn.execute(
                "SELECT extra_ability_pincer FROM cards WHERE cardId = ?", ("card-1",)
            ).fetchone()
        assert val == 1

    def test_unknown_field_raises(self, db_path: Path) -> None:
        with get_connection(db_path) as conn, pytest.raises(ValueError):
            update_card_admin(
                conn,
                "card-1",
                {"image": "evil.png"},
                locale_key="en-EN",
            )

    def test_can_create_field_rejected(self, db_path: Path) -> None:
        with get_connection(db_path) as conn, pytest.raises(ValueError):
            update_card_admin(
                conn,
                "card-1",
                {"can_create": "junk"},
                locale_key="en-EN",
            )

    def test_unknown_card_raises_keyerror(self, db_path: Path) -> None:
        with get_connection(db_path) as conn, pytest.raises(KeyError):
            update_card_admin(
                conn,
                "no-such-card",
                {"attack": 1},
                locale_key="en-EN",
            )

    def test_empty_fields_is_noop(self, db_path: Path) -> None:
        with get_connection(db_path) as conn:
            update_card_admin(conn, "card-1", {}, locale_key="en-EN")
            conn.commit()
            (val,) = conn.execute(
                "SELECT attack FROM cards WHERE cardId = ?", ("card-1",)
            ).fetchone()
        assert val == 2  # original

    def test_does_not_commit_on_its_own(self, db_path: Path) -> None:
        # The route layer wraps the connection in contextlib.closing (close-only,
        # no implicit commit). Verify the helper does not commit.
        from contextlib import closing

        with closing(get_connection(db_path)) as conn:
            update_card_admin(conn, "card-1", {"attack": 99}, locale_key="en-EN")
            # no commit
        with get_connection(db_path) as conn:
            (val,) = conn.execute(
                "SELECT attack FROM cards WHERE cardId = ?", ("card-1",)
            ).fetchone()
        assert val == 2  # original — change rolled back
