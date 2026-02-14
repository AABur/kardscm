"""Tests for collection export behavior."""

from pathlib import Path

import pytest
from openpyxl import Workbook

from kards.commands import export_collection
from kards.config import LANGUAGE_RU
from kards.export import add_deck_sheet, export_deck_to_json


def test_export_requires_data(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"
    output_path = tmp_path / "out.csv"

    with pytest.raises(SystemExit, match="Run 'kards sync' first"):
        export_collection("csv", str(output_path), db_path=str(db_path))


_DECK_META = {
    "name": "Test Deck",
    "major_power": "soviet",
    "ally": "usa",
    "hq": "СТАЛИНГРАД",
    "deck_code": "%%CODE",
}

_DECK_CARDS = [
    {
        "nation": "Soviet",
        "name": "16-й СТРЕЛКОВЫЙ ПОЛК",
        "type": "Пехота",
        "rarity": "Стандартная",
        "set_name": "Базовый",
        "credits": 1,
        "attack": 1,
        "defense": 2,
        "description": "Test",
        "deck_quantity": 2,
        "deck_cost": 1,
    },
]


def test_add_deck_sheet() -> None:
    wb = Workbook()
    lang = LANGUAGE_RU
    add_deck_sheet(
        wb, _DECK_META, _DECK_CARDS,
        lang.deck_headers,
        lang.deck_metadata_labels,
        lang.deck_nation_to_db,
        lang.nation_display_names,
    )

    assert "Test Deck" in wb.sheetnames
    ws = wb["Test Deck"]
    assert ws.cell(row=1, column=1).value == "Название"
    assert ws.cell(row=1, column=2).value == "Test Deck"
    assert ws.cell(row=2, column=2).value == "Советский Союз"
    assert ws.cell(row=3, column=2).value == "США"
    assert ws.cell(row=7, column=1).value == "Карта"
    assert ws.cell(row=8, column=1).value == "Советские"
    assert ws.cell(row=9, column=1).value == "16-й СТРЕЛКОВЫЙ ПОЛК"


def test_export_deck_to_json(tmp_path: Path) -> None:
    import json

    output = tmp_path / "deck.json"
    export_deck_to_json(_DECK_META, _DECK_CARDS, str(output))

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["deck"]["name"] == "Test Deck"
    assert "deck_code" not in data["deck"]
    assert len(data["cards"]) == 1
    assert data["cards"][0]["deck_quantity"] == 2
