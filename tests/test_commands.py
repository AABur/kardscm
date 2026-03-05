"""Tests for kardscm.commands business logic."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kardscm.commands import (
    _read_xlsx_quantities,
    _select_deck,
    add_deck,
    export_collection,
    export_deck,
    import_deck,
    sync_collection,
    update_collection,
    validate_file,
)


def _make_card(**overrides) -> dict:
    card = {
        "cardId": "c1",
        "importId": "imp-1",
        "imageUrl": "",
        "thumbUrl": "",
        "faction": "USA",
        "type": "infantry",
        "rarity": "Standard",
        "set": "Base",
        "title": json.dumps({"en-EN": "Alpha", "ru-RU": "Альфа"}),
        "text": json.dumps({"en-EN": "Test", "ru-RU": "Тест"}),
        "kredits": 1,
        "attack": 1,
        "defense": 1,
        "attributes": "[]",
        "operationCost": None,
        "reserved": 0,
        "image": "",
        "can_create": None,
        "exile": None,
    }
    card.update(overrides)
    return card


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
    def _setup_db_with_cards(self, tmp_path):
        from kardscm.storage import get_connection, initialize_schema, upsert_cards

        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [_make_card()])
        return db_path

    @patch("kardscm.commands.get_language_config")
    def test_no_cards_raises(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        db_path = str(tmp_path / "empty.db")
        with pytest.raises(SystemExit, match="No cards"):
            export_collection("csv", str(tmp_path / "out.csv"), db_path=db_path)

    @patch("kardscm.commands.get_language_config")
    def test_xlsx(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        db_path = self._setup_db_with_cards(tmp_path)
        out = tmp_path / "out.xlsx"
        export_collection("xlsx", str(out), db_path=db_path)
        assert out.exists()

    @patch("kardscm.commands.get_language_config")
    def test_csv(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        db_path = self._setup_db_with_cards(tmp_path)
        out = tmp_path / "out.csv"
        export_collection("csv", str(out), db_path=db_path)
        assert out.exists()

    @patch("kardscm.commands.get_language_config")
    def test_json(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        db_path = self._setup_db_with_cards(tmp_path)
        out = tmp_path / "out.json"
        export_collection("json", str(out), db_path=db_path)
        assert out.exists()

    @patch("kardscm.commands.get_language_config")
    def test_unsupported_format(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        db_path = self._setup_db_with_cards(tmp_path)
        with pytest.raises(ValueError, match="Unsupported format"):
            export_collection("pdf", str(tmp_path / "out.pdf"), db_path=db_path)


class TestUpdateCollection:
    @patch("kardscm.commands.get_language_config")
    def test_file_not_found(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        db_path = str(tmp_path / "test.db")
        missing = str(tmp_path / "missing.xlsx")
        with pytest.raises(SystemExit, match="Failed to read file"):
            update_collection(missing, db_path=db_path)

    @patch("kardscm.commands.get_language_config")
    def test_success(self, mock_config, tmp_path):
        from openpyxl import Workbook

        from kardscm.config import LANGUAGE_EN
        from kardscm.storage import get_connection, initialize_schema, upsert_cards

        mock_config.return_value = LANGUAGE_EN

        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(conn, [_make_card()])

        xlsx_path = tmp_path / "update.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(LANGUAGE_EN.export_headers)
        ws.append(["USA", "Alpha", "Infantry", "Standard", "", "Base", 3, "1", "1", "1", ""])
        wb.save(str(xlsx_path))

        update_collection(str(xlsx_path), db_path=db_path)

        from kardscm.storage import fetch_cards

        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert cards[0]["quantity"] == 3


class TestImportDeck:
    @patch("kardscm.commands.get_language_config")
    def test_file_not_found(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        with pytest.raises(SystemExit, match="Failed to parse deck"):
            import_deck(str(tmp_path / "missing.txt"), db_path=str(tmp_path / "t.db"))

    @patch("kardscm.commands.get_language_config")
    def test_duplicate_deck(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN
        from kardscm.storage import get_connection, initialize_schema, insert_deck

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
        from kardscm.config import LANGUAGE_EN
        from kardscm.storage import get_connection, initialize_schema

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
    def test_success(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN
        from kardscm.storage import (
            fetch_all_decks,
            get_connection,
            initialize_schema,
            upsert_cards,
        )

        mock_config.return_value = LANGUAGE_EN

        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(
                conn,
                [
                    _make_card(
                        title=json.dumps({"en-EN": "Alpha"}),
                    )
                ],
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
    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands.scrape_cards")
    def test_success(self, mock_scrape, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        mock_scrape.return_value = [_make_card()]

        db_path = str(tmp_path / "sync.db")
        sync_collection(db_path=db_path)

        from kardscm.storage import fetch_cards, get_connection

        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert len(cards) == 1
        title = json.loads(cards[0]["title"])
        assert title["en-EN"] == "Alpha"

    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands.scrape_cards")
    def test_empty_scrape(self, mock_scrape, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        mock_scrape.return_value = []

        db_path = str(tmp_path / "empty.db")
        sync_collection(db_path=db_path)

        from kardscm.storage import fetch_cards, get_connection

        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert cards == []


class TestExportDeck:
    def _setup_db_with_deck(self, tmp_path):
        from kardscm.storage import (
            get_connection,
            initialize_schema,
            insert_deck,
            insert_deck_cards,
            upsert_cards,
        )

        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            upsert_cards(
                conn,
                [
                    _make_card(
                        title=json.dumps({"en-EN": "Alpha"}),
                    )
                ],
            )
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
                {"usa": "USA"},
                "en-EN",
            )
            conn.commit()
        return db_path

    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands._select_deck")
    def test_export_json(self, mock_select, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        db_path = self._setup_db_with_deck(tmp_path)
        mock_select.return_value = {
            "deck_id": 1,
            "name": "Test Deck",
            "major_power": "usa",
            "ally": None,
            "hq": None,
        }

        out = tmp_path / "deck.json"
        export_deck("json", str(out), db_path=db_path)
        assert out.exists()

    @patch("kardscm.commands.get_language_config")
    @patch("kardscm.commands._select_deck")
    def test_no_cards_raises(self, mock_select, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN
        from kardscm.storage import get_connection, initialize_schema, insert_deck

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
        from kardscm.storage import insert_deck

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
        from kardscm.storage import insert_deck

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
        from kardscm.storage import insert_deck

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
    @patch("kardscm.commands.get_language_config")
    def test_file_not_found(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        with pytest.raises(FileNotFoundError):
            _read_xlsx_quantities(str(tmp_path / "missing.xlsx"))

    @patch("kardscm.commands.get_language_config")
    def test_missing_columns(self, mock_config, tmp_path):
        from openpyxl import Workbook

        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN

        xlsx = tmp_path / "bad.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(["Wrong", "Headers"])
        wb.save(str(xlsx))

        with pytest.raises(ValueError, match="Missing required columns"):
            _read_xlsx_quantities(str(xlsx))


class TestAddDeck:
    def _make_exile_card(self, **overrides) -> dict:
        card = {
            "cardId": "card-poland-exile",
            "importId": "imp-exile",
            "imageUrl": "",
            "thumbUrl": "",
            "faction": "Poland",
            "type": "plane",
            "rarity": "Standard",
            "set": "Base",
            "title": json.dumps({"en-EN": "IL-2M PL", "ru-RU": "Ил-2М PL"}),
            "text": json.dumps({"en-EN": "Exile card"}),
            "kredits": 3,
            "attack": 2,
            "defense": 2,
            "attributes": "[]",
            "operationCost": None,
            "reserved": 0,
            "image": "",
            "can_create": None,
            "exile": "Soviet",
        }
        card.update(overrides)
        return card

    def _setup_db(self, tmp_path, cards=None):
        from kardscm.storage import get_connection, initialize_schema, upsert_cards

        db_path = str(tmp_path / "test.db")
        with get_connection(db_path) as conn:
            initialize_schema(conn)
            if cards:
                upsert_cards(conn, cards)
        return db_path

    @patch("kardscm.commands.get_language_config")
    def test_file_not_found(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        with pytest.raises(SystemExit, match="Failed to parse deck"):
            add_deck(str(tmp_path / "missing.txt"), db_path=str(tmp_path / "t.db"))

    @patch("kardscm.commands.get_language_config")
    def test_card_not_found_no_exile(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        db_path = self._setup_db(tmp_path)

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "New Deck\nMajor power: soviet\n\nsoviet:\n1x (1K) MISSING\n",
            encoding="utf-8",
        )

        with pytest.raises(SystemExit, match="Cards not found"):
            add_deck(str(deck_file), db_path=db_path)

    @patch("kardscm.commands.get_language_config")
    def test_exile_fallback_success(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN
        from kardscm.storage import fetch_all_decks, get_connection

        mock_config.return_value = LANGUAGE_EN
        # Exile card: faction=Poland, exile=Soviet; no quantity mismatch (both 0)
        db_path = self._setup_db(tmp_path, cards=[self._make_exile_card()])

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "Soviet Deck\nMajor power: soviet\n\nsoviet:\n0x (3K) IL-2M PL\n",
            encoding="utf-8",
        )

        add_deck(str(deck_file), db_path=db_path)

        with get_connection(db_path) as conn:
            decks = fetch_all_decks(conn)
        assert len(decks) == 1
        assert decks[0]["name"] == "Soviet Deck"

    @patch("kardscm.commands.get_language_config")
    def test_quantity_mismatch_no_update(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN

        mock_config.return_value = LANGUAGE_EN
        # Card in collection with quantity=1, deck wants 2
        db_path = self._setup_db(
            tmp_path,
            cards=[_make_card(title=json.dumps({"en-EN": "Alpha"}))],
        )
        # Set quantity=1 in DB
        from kardscm.storage import get_connection

        with get_connection(db_path) as conn:
            conn.execute("UPDATE cards SET quantity = 1 WHERE cardId = 'c1'")
            conn.commit()

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "Alpha Deck\nMajor power: usa\n\nusa:\n2x (1K) Alpha\n",
            encoding="utf-8",
        )

        with pytest.raises(SystemExit, match="quantity mismatch"):
            add_deck(str(deck_file), db_path=db_path)

    @patch("kardscm.commands.get_language_config")
    def test_quantity_mismatch_with_update(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN
        from kardscm.storage import fetch_cards, get_connection

        mock_config.return_value = LANGUAGE_EN
        db_path = self._setup_db(
            tmp_path,
            cards=[_make_card(title=json.dumps({"en-EN": "Alpha"}))],
        )
        # Set quantity=1 in DB, deck wants 2
        with get_connection(db_path) as conn:
            conn.execute("UPDATE cards SET quantity = 1 WHERE cardId = 'c1'")
            conn.commit()

        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(
            "Alpha Deck\nMajor power: usa\n\nusa:\n2x (1K) Alpha\n",
            encoding="utf-8",
        )

        add_deck(str(deck_file), update=True, db_path=db_path)

        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert cards[0]["quantity"] == 2

    @patch("kardscm.commands.get_language_config")
    def test_success_no_mismatch(self, mock_config, tmp_path):
        from kardscm.config import LANGUAGE_EN
        from kardscm.storage import fetch_all_decks, get_connection

        mock_config.return_value = LANGUAGE_EN
        db_path = self._setup_db(
            tmp_path,
            cards=[_make_card(title=json.dumps({"en-EN": "Alpha"}))],
        )

        deck_file = tmp_path / "deck.txt"
        # quantity=0 matches default DB quantity=0
        deck_file.write_text(
            "My Deck\nMajor power: usa\n\nusa:\n0x (1K) Alpha\n",
            encoding="utf-8",
        )

        add_deck(str(deck_file), db_path=db_path)

        with get_connection(db_path) as conn:
            decks = fetch_all_decks(conn)
        assert len(decks) == 1
        assert decks[0]["name"] == "My Deck"
