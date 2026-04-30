"""Tests for kardscm.export.exporters."""

from __future__ import annotations

import csv
import json

from openpyxl import load_workbook

from kardscm.export import export_to_csv, export_to_json, export_to_xlsx
from kardscm.locales import LANGUAGE_EN


def _sample_cards() -> list[dict]:
    """Sample translated card dicts for export tests."""
    return [
        {
            "faction": "USA",
            "title": "Alpha",
            "type": "Infantry",
            "rarity": "Standard",
            "attributes": "Guard",
            "set": "Base",
            "quantity": 2,
            "kredits": 1,
            "attack": 1,
            "defense": 2,
            "text": "Test card",
        },
        {
            "faction": "Germany",
            "title": "Panzer IV",
            "type": "Tank",
            "rarity": "Limited",
            "attributes": "Blitz",
            "set": "Base",
            "quantity": 1,
            "kredits": 4,
            "attack": 3,
            "defense": 4,
            "text": "Tank card",
        },
    ]


class TestExportToXlsx:
    def test_creates_file(self, tmp_path):
        out = tmp_path / "cards.xlsx"
        cards = _sample_cards()
        headers = LANGUAGE_EN.export_headers

        export_to_xlsx(cards, str(out), headers)

        assert out.exists()
        wb = load_workbook(str(out))
        ws = wb.active
        header_values = [cell.value for cell in ws[1]]
        assert header_values == headers
        assert ws.cell(row=2, column=2).value == "Alpha"

    def test_correct_row_count(self, tmp_path):
        out = tmp_path / "cards.xlsx"
        cards = _sample_cards()
        export_to_xlsx(cards, str(out), LANGUAGE_EN.export_headers)

        wb = load_workbook(str(out))
        ws = wb.active
        assert ws.max_row == 3

    def test_numeric_fields_as_int(self, tmp_path):
        out = tmp_path / "cards.xlsx"
        cards = _sample_cards()
        export_to_xlsx(cards, str(out), LANGUAGE_EN.export_headers)

        wb = load_workbook(str(out))
        ws = wb.active
        qty_col = LANGUAGE_EN.export_headers.index("Quantity") + 1
        assert ws.cell(row=2, column=qty_col).value == 2

    def test_freeze_panes(self, tmp_path):
        out = tmp_path / "cards.xlsx"
        export_to_xlsx(_sample_cards(), str(out), LANGUAGE_EN.export_headers)

        wb = load_workbook(str(out))
        ws = wb.active
        assert ws.freeze_panes == "A2"


class TestExportToCsv:
    def test_utf8_bom(self, tmp_path):
        out = tmp_path / "cards.csv"
        export_to_csv(_sample_cards(), str(out), LANGUAGE_EN.export_headers)

        raw = out.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"

    def test_content(self, tmp_path):
        out = tmp_path / "cards.csv"
        cards = _sample_cards()
        export_to_csv(cards, str(out), LANGUAGE_EN.export_headers)

        with open(str(out), newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert rows[0] == LANGUAGE_EN.export_headers
        assert rows[1][0] == "USA"
        assert rows[1][1] == "Alpha"
        assert len(rows) == 3

    def test_creates_file(self, tmp_path):
        out = tmp_path / "cards.csv"
        export_to_csv(_sample_cards(), str(out), LANGUAGE_EN.export_headers)
        assert out.exists()


class TestExportToJson:
    def test_structure(self, tmp_path):
        out = tmp_path / "cards.json"
        cards = _sample_cards()
        export_to_json(cards, str(out), "en", "English")

        data = json.loads(out.read_text(encoding="utf-8"))
        assert "metadata" in data
        assert "cards" in data
        assert data["metadata"]["language"] == "en"
        assert data["metadata"]["language_name"] == "English"
        assert data["metadata"]["total_cards"] == 2
        assert len(data["cards"]) == 2

    def test_card_content(self, tmp_path):
        out = tmp_path / "cards.json"
        cards = _sample_cards()
        export_to_json(cards, str(out), "en", "English")

        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["cards"][0]["title"] == "Alpha"

    def test_creates_file(self, tmp_path):
        out = tmp_path / "cards.json"
        export_to_json(_sample_cards(), str(out), "en", "English")
        assert out.exists()


class TestExportEmptyCards:
    def test_xlsx_empty(self, tmp_path):
        out = tmp_path / "empty.xlsx"
        export_to_xlsx([], str(out), LANGUAGE_EN.export_headers)
        assert out.exists()
        wb = load_workbook(str(out))
        ws = wb.active
        assert ws.max_row == 1

    def test_csv_empty(self, tmp_path):
        out = tmp_path / "empty.csv"
        export_to_csv([], str(out), LANGUAGE_EN.export_headers)
        assert out.exists()
        with open(str(out), newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 1

    def test_json_empty(self, tmp_path):
        out = tmp_path / "empty.json"
        export_to_json([], str(out), "en", "English")
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["metadata"]["total_cards"] == 0
        assert data["cards"] == []
