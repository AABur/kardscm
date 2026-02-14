"""Tests for scrape sanitization helpers."""

from kards.scraping.localization import sanitize_text


def test_sanitize_decodes_hex_quotes() -> None:
    value = r"\xabСоюз\xbb"
    assert sanitize_text(value) == "Союз"


def test_sanitize_decodes_newlines() -> None:
    value = (
        r"Размещение: Наносит 1 урона врагу.\r\n "
        r"Уничтожение: Если сейчас ход врага, добавьте копию себе в руку."
    )
    expected = (
        "Размещение: Наносит 1 урона врагу. "
        "Уничтожение: Если сейчас ход врага, добавьте копию себе в руку."
    )
    assert sanitize_text(value) == expected
