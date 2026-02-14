"""Tests for deck file parser."""

from pathlib import Path

import pytest

from kards.importing.parser import parse_deck_file

EXAMPLE_DECK = Path("tmp/deck_soviet_example.txt")


def test_parse_valid_deck_file() -> None:
    deck = parse_deck_file(str(EXAMPLE_DECK))

    assert deck["name"] == "Советская колода"
    assert deck["major_power"] == "soviet"
    assert deck["ally"] == "usa"
    assert deck["hq"] == "СТАЛИНГРАД"
    assert deck["deck_code"] is not None
    assert deck["deck_code"].startswith("%%")
    assert len(deck["cards"]) == 29


def test_parse_deck_cards_structure() -> None:
    deck = parse_deck_file(str(EXAMPLE_DECK))

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
