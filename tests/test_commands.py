"""Tests for kardscm.commands business logic."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from openpyxl import Workbook

from kardscm.commands import (
    _read_xlsx_quantities,
    _select_deck,
    add_deck,
    apply_sync_changes,
    export_collection,
    export_deck,
    fetch_and_compute_diff,
    import_deck,
    remove_deck,
    sync_collection,
    update_collection,
    validate_file,
)
from kardscm.locales import LANGUAGE_EN
from kardscm.storage import (
    fetch_all_decks,
    fetch_cards,
    get_connection,
    initialize_schema,
    insert_deck,
    insert_deck_cards,
    upsert_cards,
)


class TestValidateFile:
    def test_correct_ext(self):
        result = validate_file("cards.xlsx", ".xlsx")
        assert isinstance(result, Path)
        assert result.suffix == ".xlsx"

    def test_wrong_ext(self):
        with pytest.raises(SystemExit, match="Expected .xlsx"):
            validate_file("cards.csv", ".xlsx")

    def test_no_extension(self):
        with pytest.raises(SystemExit, match="no extension"):
            validate_file("cards", ".xlsx")

    def test_must_exist_missing(self, tmp_path):
        missing = tmp_path / "missing.xlsx"
        with pytest.raises(SystemExit, match="File not found"):
            validate_file(str(missing), ".xlsx", must_exist=True)

    def test_must_exist_present(self, tmp_path):
        existing = tmp_path / "cards.xlsx"
        existing.write_bytes(b"")
        result = validate_file(str(existing), ".xlsx", must_exist=True)
        assert result.exists()

    def test_must_exist_false_missing(self, tmp_path):
        missing = tmp_path / "output.xlsx"
        result = validate_file(str(missing), ".xlsx", must_exist=False)
        assert result.suffix == ".xlsx"


class TestExportCollection:
    @pytest.fixture()
    def db_path(self, tmp_path, make_card):
        path = str(tmp_path / "test.db")
        with get_connection(path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [make_card()])
        return path

    @patch("kardscm.commands.get_language_config")
    def test_no_cards_raises(self, mock_config, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        db_path = str(tmp_path / "empty.db")
        with pytest.raises(SystemExit, match="No cards"):
            export_collection("csv", str(tmp_path / "out.csv"), db_path=db_path)

    @patch("kardscm.commands.get_language_config")
    def test_xlsx(self, mock_config, db_path, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        out = tmp_path / "out.xlsx"
        export_collection("xlsx", str(out), db_path=db_path)
        assert out.exists()

    @patch("kardscm.commands.get_language_config")
    def test_csv(self, mock_config, db_path, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        out = tmp_path / "out.csv"
        export_collection("csv", str(out), db_path=db_path)
        assert out.exists()

    @patch("kardscm.commands.get_language_config")
    def test_json(self, mock_config, db_path, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        out = tmp_path / "out.json"
        export_collection("json", str(out), db_path=db_path)
        assert out.exists()

    @patch("kardscm.commands.get_language_config")
    def test_unsupported_format(self, mock_config, db_path, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        with pytest.raises(ValueError, match="Unsupported format"):
            export_collection("pdf", str(tmp_path / "out.pdf"), db_path=db_path)


class TestUpdateCollection:
    @patch("kardscm.commands.get_language_config")
    def test_file_not_found(self, mock_config, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        db_path = str(tmp_path / "test.db")
        missing = str(tmp_path / "missing.xlsx")
        with pytest.raises(SystemExit, match="Failed to read file"):
            update_collection(missing, db_path=db_path)

    @patch("kardscm.commands.get_language_config")
    def test_success(self, mock_config, tmp_path, make_card):
        mock_config.return_value = LANGUAGE_EN

        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [make_card()])

        xlsx_path = tmp_path / "update.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(LANGUAGE_EN.export_headers)
        ws.append(["USA", "Alpha", "Infantry", "Standard", "", "Base", 3, "1", "1", "1", ""])
        wb.save(str(xlsx_path))

        update_collection(str(xlsx_path), db_path=db_path)

        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert cards[0]["quantity"] == 3


class TestImportDeck:
    @patch("kardscm.commands.get_language_config")
    def test_file_not_found(self, mock_config, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        with pytest.raises(SystemExit, match="Failed to parse deck"):
            import_deck(str(tmp_path / "missing.txt"), db_path=str(tmp_path / "t.db"))

    @patch("kardscm.commands.get_language_config")
    def test_duplicate_deck(self, mock_config, tmp_path):
        mock_config.return_value = LANGUAGE_EN

        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            insert_deck(
                conn,
                {
                    "name": "My Deck",
                    "major_power": "soviet",
                    "ally": None,
                    "hq": None,
                    "deck_code": None,
                    "cards": [],
                },
            )
            conn.commit()

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "My Deck\nMajor power: soviet\n\nsoviet:\n1x (1K) Card\n",
            encoding="utf-8",
        )

        with pytest.raises(SystemExit, match="already exists"):
            import_deck(str(deck_file), db_path=db_path)

    @patch("kardscm.commands.get_language_config")
    def test_card_not_found(self, mock_config, tmp_path):
        mock_config.return_value = LANGUAGE_EN

        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "New Deck\nMajor power: soviet\n\nsoviet:\n1x (1K) MISSING\n",
            encoding="utf-8",
        )

        with pytest.raises(SystemExit, match="Cards not found"):
            import_deck(str(deck_file), db_path=db_path)

    @patch("kardscm.commands.get_language_config")
    def test_success(self, mock_config, tmp_path, make_card):
        mock_config.return_value = LANGUAGE_EN

        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(
                conn,
                [make_card(title=json.dumps({"en-EN": "Alpha"}))],
            )

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "My Deck\nMajor power: usa\n\nusa:\n2x (1K) Alpha\n",
            encoding="utf-8",
        )

        import_deck(str(deck_file), db_path=db_path)

        with get_connection(db_path) as conn:
            decks = fetch_all_decks(conn)
        assert len(decks) == 1
        assert decks[0]["name"] == "My Deck"


class TestSyncCollection:
    @staticmethod
    def _list_diff_files(directory: Path) -> list[Path]:
        return sorted(directory.glob("sync-diff-*.md"))

    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands.scrape_cards")
    def test_first_sync_writes_all_new_cards_and_report(
        self, mock_scrape, mock_config, tmp_path, make_card, monkeypatch
    ):
        """Empty DB + non-empty scrape: every card lands in 'new', interactive
        approval (auto via --yes) writes everything and emits a report."""
        mock_config.return_value = LANGUAGE_EN
        mock_scrape.return_value = [make_card()]
        monkeypatch.chdir(tmp_path)

        db_path = str(tmp_path / "sync.db")
        sync_collection(db_path=db_path, yes=True)

        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert len(cards) == 1
        assert json.loads(cards[0]["title"])["en-EN"] == "Alpha"
        assert len(self._list_diff_files(tmp_path)) == 1

    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands.scrape_cards")
    def test_empty_diff_no_prompts_no_report(
        self, mock_scrape, mock_config, tmp_path, make_card, monkeypatch
    ):
        """If old equals new, sync skips prompts/report and updates last_sync."""
        mock_config.return_value = LANGUAGE_EN
        card = make_card()
        mock_scrape.return_value = [card]
        monkeypatch.chdir(tmp_path)

        db_path = str(tmp_path / "sync.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [card])

        sync_collection(db_path=db_path)

        assert self._list_diff_files(tmp_path) == []
        with get_connection(db_path) as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key='last_sync'").fetchone()
        assert row is not None

    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands.scrape_cards")
    def test_diff_only_writes_report_no_db_changes(
        self, mock_scrape, mock_config, tmp_path, make_card, monkeypatch
    ):
        mock_config.return_value = LANGUAGE_EN
        old = make_card(kredits=2)
        new = make_card(kredits=5)
        mock_scrape.return_value = [new]
        monkeypatch.chdir(tmp_path)

        db_path = str(tmp_path / "sync.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [old])

        sync_collection(db_path=db_path, diff_only=True)

        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert cards[0]["kredits"] == 2  # unchanged
        diff_files = self._list_diff_files(tmp_path)
        assert len(diff_files) == 1
        assert "kredits: `2` → `5`" in diff_files[0].read_text(encoding="utf-8")

    @patch("kardscm.commands.typer.confirm", return_value=False)
    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands.scrape_cards")
    def test_user_rejects_aborts_without_db_changes(
        self,
        mock_scrape,
        mock_config,
        _confirm,
        tmp_path,
        make_card,
        monkeypatch,
    ):
        mock_config.return_value = LANGUAGE_EN
        old = make_card(kredits=2)
        new = make_card(kredits=5)
        mock_scrape.return_value = [new]
        monkeypatch.chdir(tmp_path)

        db_path = str(tmp_path / "sync.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [old])

        sync_collection(db_path=db_path)

        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
            last_sync = conn.execute("SELECT value FROM metadata WHERE key='last_sync'").fetchone()
        assert cards[0]["kredits"] == 2  # rejected — DB untouched
        assert last_sync is None  # rejection does not bump last_sync
        assert len(self._list_diff_files(tmp_path)) == 1  # report still written

    @patch("kardscm.commands.delete_cards")
    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands.scrape_cards")
    def test_yes_flag_applies_writes_and_deletes(
        self,
        mock_scrape,
        mock_config,
        mock_delete,
        tmp_path,
        make_card,
        monkeypatch,
    ):
        """--yes: removed-card category triggers delete_cards on approval."""
        mock_config.return_value = LANGUAGE_EN
        existing = make_card(cardId="A")
        going_away = make_card(cardId="B", title=json.dumps({"en-EN": "Bravo"}))
        mock_scrape.return_value = [existing]
        monkeypatch.chdir(tmp_path)

        db_path = str(tmp_path / "sync.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [existing, going_away])

        sync_collection(db_path=db_path, yes=True)

        mock_delete.assert_called_once()
        deleted_ids = list(mock_delete.call_args[0][1])
        assert deleted_ids == ["B"]

    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands.scrape_cards")
    def test_diff_report_custom_path(
        self, mock_scrape, mock_config, tmp_path, make_card, monkeypatch
    ):
        mock_config.return_value = LANGUAGE_EN
        mock_scrape.return_value = [make_card(kredits=9)]
        monkeypatch.chdir(tmp_path)

        db_path = str(tmp_path / "sync.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [make_card(kredits=2)])

        custom = tmp_path / "subdir" / "out.md"
        custom.parent.mkdir()
        sync_collection(db_path=db_path, diff_only=True, diff_report_path=custom)

        assert custom.exists()
        assert "kredits" in custom.read_text(encoding="utf-8")


class TestFetchAndComputeDiff:
    @patch("kardscm.commands.scrape_cards")
    def test_returns_report_and_new_cards(
        self, mock_scrape, tmp_path, make_card
    ):
        """Helper returns (report, new_cards, timestamp) without writing DB."""
        old = make_card(kredits=2)
        new = make_card(kredits=5)
        mock_scrape.return_value = [new]

        db_path = str(tmp_path / "fc.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [old])

        report, new_cards, timestamp = fetch_and_compute_diff(db_path, LANGUAGE_EN)

        assert new_cards == [new]
        assert report["new"] == []
        assert len(report["changed"]) == 1
        assert report["changed"][0]["card"]["cardId"] == "card-1"
        assert isinstance(timestamp, str) and len(timestamp) > 0

        # DB must be untouched.
        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert cards[0]["kredits"] == 2

    @patch("kardscm.commands.scrape_cards")
    def test_empty_db_routes_all_cards_to_new(
        self, mock_scrape, tmp_path, make_card
    ):
        new = make_card()
        mock_scrape.return_value = [new]

        db_path = str(tmp_path / "fc_empty.db")
        report, new_cards, _ = fetch_and_compute_diff(db_path, LANGUAGE_EN)

        assert new_cards == [new]
        assert len(report["new"]) == 1
        assert report["changed"] == []


class TestApplySyncChanges:
    @patch("kardscm.commands.scrape_cards")
    def test_writes_db_and_report(self, mock_scrape, tmp_path, make_card):
        old = make_card(kredits=2)
        new = make_card(kredits=5)
        mock_scrape.return_value = [new]

        db_path = str(tmp_path / "ap.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [old])

        report, new_cards, timestamp = fetch_and_compute_diff(db_path, LANGUAGE_EN)
        report_path = tmp_path / "out.md"

        result = apply_sync_changes(
            db_path,
            new_cards,
            report,
            LANGUAGE_EN,
            timestamp,
            diff_report_path=report_path,
        )

        assert result == report_path
        assert report_path.exists()
        assert "kredits" in report_path.read_text(encoding="utf-8")
        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
            row = conn.execute("SELECT value FROM metadata WHERE key='last_sync'").fetchone()
        assert cards[0]["kredits"] == 5
        assert row is not None

    @patch("kardscm.commands.scrape_cards")
    def test_empty_report_only_updates_metadata(
        self, mock_scrape, tmp_path, make_card
    ):
        card = make_card()
        mock_scrape.return_value = [card]

        db_path = str(tmp_path / "ap_empty.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [card])

        report, new_cards, timestamp = fetch_and_compute_diff(db_path, LANGUAGE_EN)
        report_path = tmp_path / "should_not_exist.md"

        result = apply_sync_changes(
            db_path,
            new_cards,
            report,
            LANGUAGE_EN,
            timestamp,
            diff_report_path=report_path,
        )

        assert result is None
        assert not report_path.exists()
        with get_connection(db_path) as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key='last_sync'").fetchone()
        assert row is not None

    @patch("kardscm.commands.delete_cards")
    @patch("kardscm.commands.scrape_cards")
    def test_removed_cards_trigger_delete(
        self, mock_scrape, mock_delete, tmp_path, make_card
    ):
        existing = make_card(cardId="A")
        going_away = make_card(cardId="B", title=json.dumps({"en-EN": "Bravo"}))
        mock_scrape.return_value = [existing]

        db_path = str(tmp_path / "ap_rm.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [existing, going_away])

        report, new_cards, timestamp = fetch_and_compute_diff(db_path, LANGUAGE_EN)

        apply_sync_changes(
            db_path,
            new_cards,
            report,
            LANGUAGE_EN,
            timestamp,
            diff_report_path=tmp_path / "r.md",
        )

        mock_delete.assert_called_once()
        deleted_ids = list(mock_delete.call_args[0][1])
        assert deleted_ids == ["B"]


class TestExportDeck:
    @pytest.fixture()
    def deck_db_path(self, tmp_path, make_card):
        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [make_card(title=json.dumps({"en-EN": "Alpha"}))])
            deck_id = insert_deck(
                conn,
                {
                    "name": "Test Deck",
                    "major_power": "usa",
                    "ally": None,
                    "hq": None,
                    "deck_code": None,
                    "cards": [],
                },
            )
            insert_deck_cards(
                conn,
                deck_id,
                [{"nation": "usa", "name": "Alpha", "quantity": 2, "cost": 1}],
                "en-EN",
            )
            conn.commit()
        return db_path

    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands._select_deck")
    def test_export_json(self, mock_select, mock_config, deck_db_path, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        mock_select.return_value = {
            "deck_id": 1,
            "name": "Test Deck",
            "major_power": "usa",
            "ally": None,
            "hq": None,
        }

        out = tmp_path / "deck.json"
        export_deck("json", str(out), db_path=deck_db_path)
        assert out.exists()

    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands._select_deck")
    def test_no_cards_raises(self, mock_select, mock_config, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            insert_deck(
                conn,
                {
                    "name": "Empty",
                    "major_power": "usa",
                    "ally": None,
                    "hq": None,
                    "deck_code": None,
                    "cards": [],
                },
            )
            conn.commit()

        mock_select.return_value = {"deck_id": 1, "name": "Empty"}
        with pytest.raises(SystemExit, match="no cards"):
            export_deck("json", str(tmp_path / "out.json"), db_path=db_path)


class TestSelectDeck:
    def test_no_decks(self, db_connection):
        with pytest.raises(SystemExit, match="No decks"):
            _select_deck(db_connection)

    def test_valid_choice(self, db_connection):
        insert_deck(
            db_connection,
            {
                "name": "Deck A",
                "major_power": "usa",
                "ally": None,
                "hq": None,
                "deck_code": None,
                "cards": [],
            },
        )
        db_connection.commit()

        with patch("builtins.input", return_value="1"):
            result = _select_deck(db_connection)
        assert result["name"] == "Deck A"

    def test_invalid_input(self, db_connection):
        insert_deck(
            db_connection,
            {
                "name": "Deck A",
                "major_power": "usa",
                "ally": None,
                "hq": None,
                "deck_code": None,
                "cards": [],
            },
        )
        db_connection.commit()

        with patch("builtins.input", return_value="abc"):
            with pytest.raises(SystemExit, match="Invalid input"):
                _select_deck(db_connection)

    def test_out_of_range(self, db_connection):
        insert_deck(
            db_connection,
            {
                "name": "Deck A",
                "major_power": "usa",
                "ally": None,
                "hq": None,
                "deck_code": None,
                "cards": [],
            },
        )
        db_connection.commit()

        with patch("builtins.input", return_value="5"):
            with pytest.raises(SystemExit, match="Invalid choice"):
                _select_deck(db_connection)


class TestReadXlsxQuantities:
    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _read_xlsx_quantities(str(tmp_path / "missing.xlsx"), LANGUAGE_EN)

    def test_missing_columns(self, tmp_path):
        xlsx = tmp_path / "bad.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(["Wrong", "Headers"])
        wb.save(str(xlsx))

        with pytest.raises(ValueError, match="Missing required columns"):
            _read_xlsx_quantities(str(xlsx), LANGUAGE_EN)


class TestAddDeck:
    @pytest.fixture()
    def exile_card_data(self, make_card):
        return make_card(
            cardId="card-poland-exile",
            importId="imp-exile",
            faction="Poland",
            type="plane",
            title=json.dumps({"en-EN": "IL-2M PL", "ru-RU": "Ил-2М PL"}),
            text=json.dumps({"en-EN": "Exile card"}),
            kredits=3,
            attack=2,
            defense=2,
            exile="Soviet",
        )

    @pytest.fixture()
    def empty_db(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
        return db_path

    @pytest.fixture()
    def db_with_card(self, tmp_path, make_card):
        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [make_card(title=json.dumps({"en-EN": "Alpha"}))])
        return db_path

    @pytest.fixture()
    def db_with_exile(self, tmp_path, exile_card_data):
        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [exile_card_data])
        return db_path

    @patch("kardscm.commands.get_language_config")
    def test_file_not_found(self, mock_config, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        with pytest.raises(RuntimeError, match="Failed to parse deck"):
            add_deck(str(tmp_path / "missing.txt"), db_path=str(tmp_path / "t.db"))

    @patch("kardscm.commands.get_language_config")
    def test_card_not_found_no_exile(self, mock_config, empty_db, tmp_path):
        mock_config.return_value = LANGUAGE_EN

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "New Deck\nMajor power: soviet\n\nsoviet:\n1x (1K) MISSING\n",
            encoding="utf-8",
        )

        with pytest.raises(RuntimeError, match="Cards not found"):
            add_deck(str(deck_file), db_path=empty_db)

    @patch("kardscm.commands.get_language_config")
    def test_exile_fallback_success(self, mock_config, db_with_exile, tmp_path):
        mock_config.return_value = LANGUAGE_EN

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "Soviet Deck\nMajor power: soviet\n\nsoviet:\n0x (3K) IL-2M PL\n",
            encoding="utf-8",
        )

        add_deck(str(deck_file), db_path=db_with_exile)

        with get_connection(db_with_exile) as conn:
            decks = fetch_all_decks(conn)
        assert len(decks) == 1
        assert decks[0]["name"] == "Soviet Deck"

    @patch("kardscm.commands.get_language_config")
    def test_quantity_mismatch_no_update(self, mock_config, db_with_card, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        with get_connection(db_with_card) as conn:
            conn.execute("UPDATE cards SET quantity = 1 WHERE cardId = 'card-1'")
            conn.commit()

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "Alpha Deck\nMajor power: usa\n\nusa:\n2x (1K) Alpha\n",
            encoding="utf-8",
        )

        with pytest.raises(RuntimeError, match="quantity mismatch"):
            add_deck(str(deck_file), db_path=db_with_card)

    @patch("kardscm.commands.get_language_config")
    def test_quantity_mismatch_with_update(self, mock_config, db_with_card, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        with get_connection(db_with_card) as conn:
            conn.execute("UPDATE cards SET quantity = 1 WHERE cardId = 'card-1'")
            conn.commit()

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "Alpha Deck\nMajor power: usa\n\nusa:\n2x (1K) Alpha\n",
            encoding="utf-8",
        )

        add_deck(str(deck_file), update=True, db_path=db_with_card)

        with get_connection(db_with_card) as conn:
            cards = fetch_cards(conn)
        assert cards[0]["quantity"] == 2

    @patch("kardscm.commands.get_language_config")
    def test_success_no_mismatch(self, mock_config, db_with_card, tmp_path):
        mock_config.return_value = LANGUAGE_EN

        deck_file = tmp_path / "deck.txt"
        # quantity=0 matches default DB quantity=0
        deck_file.write_text(
            "My Deck\nMajor power: usa\n\nusa:\n0x (1K) Alpha\n",
            encoding="utf-8",
        )

        add_deck(str(deck_file), db_path=db_with_card)

        with get_connection(db_with_card) as conn:
            decks = fetch_all_decks(conn)
        assert len(decks) == 1
        assert decks[0]["name"] == "My Deck"

    @patch("kardscm.commands.get_language_config")
    def test_duplicate_same_code_no_replace_error(self, mock_config, db_with_card, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "My Deck\nMajor power: usa\n\nusa:\n0x (1K) Alpha\n",
            encoding="utf-8",
        )
        add_deck(str(deck_file), db_path=db_with_card)
        with pytest.raises(RuntimeError, match="already exists"):
            add_deck(str(deck_file), db_path=db_with_card)

    @patch("kardscm.commands.get_language_config")
    def test_duplicate_different_code_no_replace_hint(self, mock_config, db_with_card, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "My Deck\nMajor power: usa\n%%AAA\n\nusa:\n0x (1K) Alpha\n",
            encoding="utf-8",
        )
        add_deck(str(deck_file), db_path=db_with_card)

        deck_file2 = tmp_path / "deck2.txt"
        deck_file2.write_text(
            "My Deck\nMajor power: usa\n%%BBB\n\nusa:\n0x (1K) Alpha\n",
            encoding="utf-8",
        )
        with pytest.raises(RuntimeError, match="Use --replace"):
            add_deck(str(deck_file2), db_path=db_with_card)

    @patch("kardscm.commands.get_language_config")
    def test_replace_deletes_old_deck(self, mock_config, db_with_card, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "My Deck\nMajor power: usa\n%%AAA\n\nusa:\n0x (1K) Alpha\n",
            encoding="utf-8",
        )
        add_deck(str(deck_file), db_path=db_with_card)

        deck_file2 = tmp_path / "deck2.txt"
        deck_file2.write_text(
            "My Deck\nMajor power: usa\n%%BBB\n\nusa:\n0x (1K) Alpha\n",
            encoding="utf-8",
        )
        add_deck(str(deck_file2), replace=True, db_path=db_with_card)

        with get_connection(db_with_card) as conn:
            decks = fetch_all_decks(conn)
        assert len(decks) == 1
        assert decks[0]["deck_code"] == "%%BBB"

    @patch("kardscm.commands.get_language_config")
    def test_replace_no_existing_normal_add(self, mock_config, db_with_card, tmp_path):
        mock_config.return_value = LANGUAGE_EN
        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "New Deck\nMajor power: usa\n\nusa:\n0x (1K) Alpha\n",
            encoding="utf-8",
        )
        add_deck(str(deck_file), replace=True, db_path=db_with_card)

        with get_connection(db_with_card) as conn:
            decks = fetch_all_decks(conn)
        assert len(decks) == 1
        assert decks[0]["name"] == "New Deck"


class TestRemoveDeck:
    @pytest.fixture()
    def two_deck_db(self, tmp_path):
        """DB with two decks, no cards required."""
        db_path = str(tmp_path / "decks.db")
        deck_base = {
            "major_power": "usa",
            "ally": None,
            "hq": None,
            "deck_code": None,
            "cards": [],
        }
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            insert_deck(conn, {**deck_base, "name": "Deck A"})
            insert_deck(conn, {**deck_base, "name": "Deck B"})
            conn.commit()
        return db_path

    def test_no_decks_raises(self, tmp_path):
        db_path = str(tmp_path / "empty.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            conn.commit()
        with pytest.raises(SystemExit, match="No decks"):
            remove_deck(db_path=db_path)

    def test_delete_all_confirmed(self, two_deck_db):
        with patch("builtins.input", side_effect=["0", "y"]):
            remove_deck(db_path=two_deck_db)
        with get_connection(two_deck_db) as conn:
            assert fetch_all_decks(conn) == []

    def test_delete_all_aborted(self, two_deck_db):
        with patch("builtins.input", side_effect=["0", "n"]):
            with pytest.raises(SystemExit, match="Aborted"):
                remove_deck(db_path=two_deck_db)
        with get_connection(two_deck_db) as conn:
            assert len(fetch_all_decks(conn)) == 2

    def test_delete_one_still_works(self, two_deck_db):
        with patch("builtins.input", side_effect=["1", "y"]):
            remove_deck(db_path=two_deck_db)
        with get_connection(two_deck_db) as conn:
            remaining = fetch_all_decks(conn)
        assert len(remaining) == 1
        assert remaining[0]["name"] == "Deck B"

    def test_invalid_choice_negative(self, two_deck_db):
        with patch("builtins.input", return_value="-1"):
            with pytest.raises(SystemExit, match="Invalid choice"):
                remove_deck(db_path=two_deck_db)


# ---------------------------------------------------------------------------
# Locale warning tests
# ---------------------------------------------------------------------------


def test_emit_locale_warnings_silent_when_no_warnings(capsys) -> None:
    from kardscm.commands import _emit_locale_warnings

    _emit_locale_warnings(LANGUAGE_EN)
    assert capsys.readouterr().err == ""


def test_emit_locale_warnings_emits_to_stderr(capsys) -> None:
    from dataclasses import replace

    from kardscm.commands import _emit_locale_warnings

    cfg = replace(
        LANGUAGE_EN,
        fallback_warnings=["abilities.mobilize", "ui_strings.modal_close"],
    )
    _emit_locale_warnings(cfg)
    captured = capsys.readouterr()
    assert "Locale 'en': 2 key(s)" in captured.err
    assert "abilities.mobilize" in captured.err
    assert captured.out == ""


def test_emit_locale_warnings_truncates_after_five(capsys) -> None:
    from dataclasses import replace

    from kardscm.commands import _emit_locale_warnings

    keys = [f"section.key{i}" for i in range(8)]
    cfg = replace(LANGUAGE_EN, fallback_warnings=keys)
    _emit_locale_warnings(cfg)
    captured = capsys.readouterr()
    assert "8 key(s)" in captured.err
    assert "… and 3 more" in captured.err
