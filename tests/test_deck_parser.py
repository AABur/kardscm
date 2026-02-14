"""Tests for deck file parser."""

from pathlib import Path

import pytest

from kards.importing.parser import parse_deck_file

EXAMPLE_DECK_CONTENT = """\
Советская колода
Major power: soviet
Ally: usa
HQ: СТАЛИНГРАД

soviet:
1x (1K) 16-й СТРЕЛКОВЫЙ ПОЛК
1x (2K) ПАРТИЗАНЫ
1x (1K) МОБИЛИЗАЦИЯ
1x (3K) ОТ НАРОДА
1x (2K) ЗА РОДИНУ
1x (4K) КВ-1
1x (3K) Т-34
1x (5K) ИС-2
1x (2K) ЗАГРАДОТРЯД
1x (3K) ШТУРМОВИК ИЛ-2
1x (4K) КАТЮША
1x (1K) СНАЙПЕР
1x (2K) РАЗВЕДЧИК
1x (3K) ПОЛЕВОЙ ГОСПИТАЛЬ
1x (2K) МИНОМЁТ
1x (1K) ПЕХОТИНЕЦ
1x (3K) ПРОТИВОТАНКОВОЕ РУЖЬЁ
1x (2K) ПОЛИТРУК
1x (4K) ГВАРДИЯ
1x (1K) ПРИЗЫВ
1x (3K) ВОЗДУШНЫЙ ДЕСАНТ

usa:
1x (4K) M4 SHERMAN
1x (3K) МОРСКИЕ ПЕХОТИНЦЫ
1x (5K) B-17 ЛЕТАЮЩАЯ КРЕПОСТЬ
1x (2K) ДЕСАНТНИКИ
1x (3K) РЕЙНДЖЕРЫ
1x (1K) ЛЕНД-ЛИЗ
1x (4K) P-51 МУСТАНГ
1x (2K) ИНЖЕНЕРЫ

%%45|7E8B00FF
"""


@pytest.fixture()
def example_deck_file(tmp_path: Path) -> Path:
    deck_file = tmp_path / "deck_soviet_example.txt"
    deck_file.write_text(EXAMPLE_DECK_CONTENT, encoding="utf-8")
    return deck_file


def test_parse_valid_deck_file(example_deck_file: Path) -> None:
    deck = parse_deck_file(str(example_deck_file))

    assert deck["name"] == "Советская колода"
    assert deck["major_power"] == "soviet"
    assert deck["ally"] == "usa"
    assert deck["hq"] == "СТАЛИНГРАД"
    assert deck["deck_code"] is not None
    assert deck["deck_code"].startswith("%%")
    assert len(deck["cards"]) == 29


def test_parse_deck_cards_structure(example_deck_file: Path) -> None:
    deck = parse_deck_file(str(example_deck_file))

    soviet_cards = [c for c in deck["cards"] if c["nation"] == "soviet"]
    usa_cards = [c for c in deck["cards"] if c["nation"] == "usa"]

    assert len(soviet_cards) == 21
    assert len(usa_cards) == 8

    first = soviet_cards[0]
    assert first["name"] == "16-й СТРЕЛКОВЫЙ ПОЛК"
    assert first["quantity"] == 1
    assert first["cost"] == 1


def test_parse_deck_missing_name(tmp_path: Path) -> None:
    deck_file = tmp_path / "bad.txt"
    deck_file.write_text("Major power: soviet\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Deck name is missing"):
        parse_deck_file(str(deck_file))


def test_parse_deck_missing_major_power(tmp_path: Path) -> None:
    deck_file = tmp_path / "bad.txt"
    deck_file.write_text("My Deck\nAlly: usa\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Major power is missing"):
        parse_deck_file(str(deck_file))


def test_parse_deck_minimal(tmp_path: Path) -> None:
    deck_file = tmp_path / "minimal.txt"
    deck_file.write_text(
        "Test Deck\nMajor power: germany\n\ngermany:\n2x (3K) PANZER IV\n",
        encoding="utf-8",
    )
    deck = parse_deck_file(str(deck_file))

    assert deck["name"] == "Test Deck"
    assert deck["major_power"] == "germany"
    assert deck["ally"] is None
    assert deck["hq"] is None
    assert deck["deck_code"] is None
    assert len(deck["cards"]) == 1
    assert deck["cards"][0]["name"] == "PANZER IV"
    assert deck["cards"][0]["quantity"] == 2
    assert deck["cards"][0]["cost"] == 3
