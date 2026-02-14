"""Tests for export functions."""

import csv
import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

from kards_final_scraper import (
    TranslationLoader,
    export_to_csv,
    export_to_json,
    export_to_xlsx,
)


@pytest.fixture
def sample_cards() -> list[dict[str, str]]:
    """Fixture providing sample cards for testing."""
    return [
        {
            "Nation": "USA",
            "Name": "Test Card 1",
            "Type": "Infantry",
            "Rarity": "Standard",
            "Abilities": "",
            "Set": "Base",
            "Quantity": "",
            "Credits": "2",
            "Attack": "3",
            "Defense": "2",
            "Description": "Test description 1",
        },
        {
            "Nation": "Germany",
            "Name": "Test Card 2",
            "Type": "Armor",
            "Rarity": "Limited",
            "Abilities": "",
            "Set": "Base",
            "Quantity": "",
            "Credits": "4",
            "Attack": "5",
            "Defense": "4",
            "Description": "Test description 2",
        },
    ]


def test_export_to_xlsx_creates_file(sample_cards: list[dict[str, str]], tmp_path: Path) -> None:
    """Test that XLSX export creates output file."""
    output_file = tmp_path / "test.xlsx"
    export_to_xlsx(sample_cards, str(output_file), "en")

    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_export_to_xlsx_contains_data(sample_cards: list[dict[str, str]], tmp_path: Path) -> None:
    """Test that XLSX file contains correct data."""
    output_file = tmp_path / "test.xlsx"
    export_to_xlsx(sample_cards, str(output_file), "en")

    wb = load_workbook(str(output_file))
    ws = wb.active

    # Check header row (new order: Nation, Name, ...)
    assert ws.cell(1, 1).value == "Nation"
    assert ws.cell(1, 2).value == "Name"

    # Check data rows
    assert ws.max_row == len(sample_cards) + 1  # +1 for header


def test_export_to_xlsx_sorting(sample_cards: list[dict[str, str]], tmp_path: Path) -> None:
    """Test that XLSX export sorts cards by name."""
    output_file = tmp_path / "test.xlsx"
    export_to_xlsx(sample_cards, str(output_file), "en")

    wb = load_workbook(str(output_file))
    ws = wb.active

    # Cards should be sorted alphabetically (Name is in column 2)
    card1_name = ws.cell(2, 2).value  # First data row, column 2 (Name)
    card2_name = ws.cell(3, 2).value  # Second data row, column 2 (Name)

    assert card1_name <= card2_name


def test_export_to_csv_creates_file(sample_cards: list[dict[str, str]], tmp_path: Path) -> None:
    """Test that CSV export creates output file."""
    output_file = tmp_path / "test.csv"
    export_to_csv(sample_cards, str(output_file))

    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_export_to_csv_contains_data(sample_cards: list[dict[str, str]], tmp_path: Path) -> None:
    """Test that CSV file contains correct data."""
    output_file = tmp_path / "test.csv"
    export_to_csv(sample_cards, str(output_file))

    with open(output_file, encoding="utf-8-sig") as csvfile:
        reader = csv.reader(csvfile)
        rows = list(reader)

    # Check header row (new order: Nation, Name, ...)
    assert len(rows) == len(sample_cards) + 1  # +1 for header
    assert rows[0][0] == "Nation"
    assert rows[0][1] == "Name"


def test_export_to_csv_encoding(sample_cards: list[dict[str, str]], tmp_path: Path) -> None:
    """Test that CSV uses UTF-8 with BOM for Windows compatibility."""
    output_file = tmp_path / "test.csv"
    export_to_csv(sample_cards, str(output_file))

    with open(output_file, "rb") as f:
        content = f.read()
        # UTF-8 BOM is EF BB BF
        assert content[:3] == b'\xef\xbb\xbf'


def test_export_to_json_creates_file(sample_cards: list[dict[str, str]], tmp_path: Path) -> None:
    """Test that JSON export creates output file."""
    output_file = tmp_path / "test.json"
    export_to_json(sample_cards, str(output_file), "en")

    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_export_to_json_contains_metadata(
    sample_cards: list[dict[str, str]], tmp_path: Path
) -> None:
    """Test that JSON file contains metadata."""
    output_file = tmp_path / "test.json"
    language = "ja"
    export_to_json(sample_cards, str(output_file), language)

    with open(output_file, encoding="utf-8") as jsonfile:
        data = json.load(jsonfile)

    assert "metadata" in data
    assert data["metadata"]["language"] == language
    assert data["metadata"]["total_cards"] == len(sample_cards)


def test_export_to_json_contains_cards(
    sample_cards: list[dict[str, str]], tmp_path: Path
) -> None:
    """Test that JSON file contains cards."""
    output_file = tmp_path / "test.json"
    export_to_json(sample_cards, str(output_file), "en")

    with open(output_file, encoding="utf-8") as jsonfile:
        data = json.load(jsonfile)

    assert "cards" in data
    assert len(data["cards"]) == len(sample_cards)


def test_export_to_json_sorting(sample_cards: list[dict[str, str]], tmp_path: Path) -> None:
    """Test that JSON export sorts cards by name."""
    output_file = tmp_path / "test.json"
    export_to_json(sample_cards, str(output_file), "en")

    with open(output_file, encoding="utf-8") as jsonfile:
        data = json.load(jsonfile)

    cards = data["cards"]
    card_names = [card["Name"] for card in cards]
    assert card_names == sorted(card_names)


def test_export_empty_cards_list(tmp_path: Path) -> None:
    """Test exporting empty card list."""
    empty_cards: list[dict[str, str]] = []
    output_file = tmp_path / "empty.xlsx"

    export_to_xlsx(empty_cards, str(output_file), "en")
    assert output_file.exists()

    wb = load_workbook(str(output_file))
    ws = wb.active
    assert ws.max_row == 1  # Only header row


def test_export_handles_missing_fields(tmp_path: Path) -> None:
    """Test export handles cards with missing fields."""
    partial_cards = [
        {
            "Name": "Partial Card",
            "Nation": "USA",
            # Missing other fields
        }
    ]

    output_file = tmp_path / "partial.xlsx"
    export_to_xlsx(partial_cards, str(output_file), "en")

    wb = load_workbook(str(output_file))
    ws = wb.active
    assert ws.max_row == 2  # Header + 1 card


def test_field_order_correct(sample_cards: list[dict[str, str]], tmp_path: Path) -> None:
    """Test that fields are in correct order."""
    output_file = tmp_path / "test.xlsx"
    export_to_xlsx(sample_cards, str(output_file), "en")

    wb = load_workbook(str(output_file))
    ws = wb.active

    expected = ["Nation", "Name", "Type", "Rarity", "Abilities",
                "Set", "Quantity", "Credits", "Attack", "Defense", "Description"]

    for i, header in enumerate(expected, 1):
        assert ws.cell(1, i).value == header


class TestTranslationLoader:
    """Tests for TranslationLoader class."""

    def test_translate_headers_without_language_set(self) -> None:
        """Test that headers default to English when no language set."""
        translator = TranslationLoader()
        headers = ["Name", "Nation", "Type"]

        result = translator.translate_headers(headers)

        # Default language is 'en', should return English headers
        assert result == ["Name", "Nation", "Type"]

    def test_translate_headers_russian(self) -> None:
        """Test that headers are translated to Russian."""
        translator = TranslationLoader()
        translator.language = "ru"

        headers = ["Name", "Nation", "Type"]
        result = translator.translate_headers(headers)

        assert result == ["Название", "Нация", "Тип"]

    def test_translate_headers_all_fields_russian(self) -> None:
        """Test all header fields translate correctly to Russian."""
        translator = TranslationLoader()
        translator.language = "ru"

        headers = ["Nation", "Name", "Type", "Rarity", "Abilities",
                   "Set", "Quantity", "Credits", "Attack", "Defense", "Description"]
        result = translator.translate_headers(headers)

        expected = ["Нация", "Название", "Тип", "Редкость", "Способности",
                    "Сет", "Количество", "Кредиты", "Атака", "Защита", "Описание"]
        assert result == expected

    def test_translate_headers_unknown_header(self) -> None:
        """Test unknown headers fall back to original."""
        translator = TranslationLoader()
        translator.language = "ru"

        headers = ["Name", "UnknownField"]
        result = translator.translate_headers(headers)

        # Name should be translated, UnknownField should remain unchanged
        assert result[0] == "Название"
        assert result[1] == "UnknownField"


class TestExportWithTranslatedHeaders:
    """Tests for exports with translated headers."""

    @pytest.fixture
    def translator_russian(self) -> TranslationLoader:
        """Create translator configured for Russian."""
        translator = TranslationLoader()
        translator.language = "ru"
        return translator

    def test_xlsx_with_translated_headers(
        self,
        sample_cards: list[dict[str, str]],
        tmp_path: Path,
        translator_russian: TranslationLoader,
    ) -> None:
        """Test XLSX export uses translated headers."""
        output_file = tmp_path / "test_ru.xlsx"
        export_to_xlsx(
            sample_cards, str(output_file), "ru", translator_russian
        )

        wb = load_workbook(str(output_file))
        ws = wb.active

        # Check that headers are translated (new order: Nation, Name, Type, ...)
        assert ws.cell(1, 1).value == "Нация"  # Nation
        assert ws.cell(1, 2).value == "Название"  # Name
        assert ws.cell(1, 3).value == "Тип"  # Type

    def test_csv_with_translated_headers(
        self,
        sample_cards: list[dict[str, str]],
        tmp_path: Path,
        translator_russian: TranslationLoader,
    ) -> None:
        """Test CSV export uses translated headers."""
        output_file = tmp_path / "test_ru.csv"
        export_to_csv(sample_cards, str(output_file), translator_russian)

        with open(output_file, encoding="utf-8-sig") as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)

        # Check that headers are translated (new order: Nation, Name, Type, ...)
        assert headers[0] == "Нация"  # Nation
        assert headers[1] == "Название"  # Name
        assert headers[2] == "Тип"  # Type

    def test_xlsx_without_translator(
        self, sample_cards: list[dict[str, str]], tmp_path: Path
    ) -> None:
        """Test XLSX export without translator uses English headers."""
        output_file = tmp_path / "test_en.xlsx"
        export_to_xlsx(sample_cards, str(output_file), "en")

        wb = load_workbook(str(output_file))
        ws = wb.active

        # Headers should be in English (new order: Nation, Name, ...)
        assert ws.cell(1, 1).value == "Nation"
        assert ws.cell(1, 2).value == "Name"

    def test_csv_without_translator(
        self, sample_cards: list[dict[str, str]], tmp_path: Path
    ) -> None:
        """Test CSV export without translator uses English headers."""
        output_file = tmp_path / "test_en.csv"
        export_to_csv(sample_cards, str(output_file))

        with open(output_file, encoding="utf-8-sig") as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)

        # Headers should be in English (new order: Nation, Name, ...)
        assert headers[0] == "Nation"
        assert headers[1] == "Name"


class TestSetTranslations:
    """Tests for set name translations."""

    def test_all_sets_have_translation_ids(self) -> None:
        """Test that all known sets have translation IDs."""
        translator = TranslationLoader()
        expected_sets = [
            "Base",
            "Allegiance",
            "TheatersOfWar",
            "Breakthrough",
            "WorldAtWar",
            "CovertOps",
            "BloodAndIron",
            "Legions",
            "NavalWarfare",
            "Homefront",
            "WinterWar",
        ]

        for set_name in expected_sets:
            assert set_name in translator.mappings["set"], f"Missing: {set_name}"

    def test_translate_set_with_translations(self) -> None:
        """Test set translation when translations are loaded."""
        translator = TranslationLoader()
        translator.translations = {
            "vhFlLC": "Кровь и железо",  # BloodAndIron
            "Nzwli2": "Базовый",  # Base
        }

        assert translator.translate("set", "BloodAndIron") == "Кровь и железо"
        assert translator.translate("set", "Base") == "Базовый"

    def test_translate_set_fallback(self) -> None:
        """Test set translation falls back to original when not found."""
        translator = TranslationLoader()
        # No translations loaded

        result = translator.translate("set", "BloodAndIron")
        assert result == "BloodAndIron"


class TestStripQuotes:
    """Tests for quote stripping functionality."""

    def test_strip_unicode_quotes(self) -> None:
        """Test stripping «» quotes."""
        result = TranslationLoader._strip_quotes("«Базовый»")
        assert result == "Базовый"

    def test_strip_regular_double_quotes(self) -> None:
        """Test stripping regular double quotes."""
        result = TranslationLoader._strip_quotes('"Base"')
        assert result == "Base"

    def test_strip_single_quotes(self) -> None:
        """Test stripping single quotes."""
        result = TranslationLoader._strip_quotes("'Base'")
        assert result == "Base"

    def test_no_quotes_unchanged(self) -> None:
        """Test text without quotes remains unchanged."""
        result = TranslationLoader._strip_quotes("Базовый")
        assert result == "Базовый"

    def test_empty_string(self) -> None:
        """Test empty string returns empty."""
        result = TranslationLoader._strip_quotes("")
        assert result == ""

    def test_mismatched_quotes_unchanged(self) -> None:
        """Test mismatched quotes are not stripped."""
        result = TranslationLoader._strip_quotes("«Base\"")
        assert result == "«Base\""


class TestSanitizeText:
    """Tests for text sanitization functionality."""

    def test_sanitize_removes_quotes(self) -> None:
        """Test sanitize_text removes surrounding quotes."""
        result = TranslationLoader.sanitize_text("«Базовый»")
        assert result == "Базовый"

    def test_sanitize_replaces_newlines(self) -> None:
        """Test sanitize_text replaces newlines with spaces."""
        result = TranslationLoader.sanitize_text("Line1\r\nLine2\nLine3")
        assert result == "Line1 Line2 Line3"

    def test_sanitize_removes_duplicate_spaces(self) -> None:
        """Test sanitize_text removes duplicate spaces."""
        result = TranslationLoader.sanitize_text("Text   with    spaces")
        assert result == "Text with spaces"

    def test_sanitize_empty_string(self) -> None:
        """Test sanitize_text handles empty string."""
        result = TranslationLoader.sanitize_text("")
        assert result == ""

    def test_sanitize_combined(self) -> None:
        """Test sanitize_text with multiple issues."""
        result = TranslationLoader.sanitize_text("«Text\r\n  with  issues»")
        assert result == "Text with issues"

    def test_sanitize_preserves_normal_text(self) -> None:
        """Test sanitize_text preserves normal text."""
        result = TranslationLoader.sanitize_text("Normal text here")
        assert result == "Normal text here"
