"""Tests for scrape sanitization helpers."""

import pytest

from kardscm.scraping.localization import sanitize_text


@pytest.mark.parametrize(
    ("input_text", "expected"),
    [
        # Original tests
        (r"\xabСоюз\xbb", "«Союз»"),
        (
            r"Размещение: Наносит 1 урона врагу.\r\n "
            r"Уничтожение: Если сейчас ход врага, добавьте копию себе в руку.",
            "Размещение: Наносит 1 урона врагу. "
            "Уничтожение: Если сейчас ход врага, добавьте копию себе в руку.",
        ),
        # Empty string
        ("", ""),
        # No special characters
        ("plain text without escapes", "plain text without escapes"),
        # Multiple escape sequences in a row
        (r"\xab\xbb\xab\xbb", "«»«»"),
        # Unicode beyond Latin (Cyrillic, CJK)
        ("Привет мир 你好世界", "Привет мир 你好世界"),
        # Only whitespace normalization (duplicate spaces)
        ("hello   world", "hello world"),
        # Tabs and mixed whitespace
        ("hello\t\tworld", "hello world"),
        # Newlines in raw text (not escaped)
        ("line1\nline2\r\nline3", "line1 line2 line3"),
    ],
    ids=[
        "hex_quotes",
        "newlines_in_text",
        "empty",
        "no_escapes",
        "multiple_escapes",
        "unicode_beyond_latin",
        "duplicate_spaces",
        "tabs",
        "raw_newlines",
    ],
)
def test_sanitize_text(input_text: str, expected: str) -> None:
    assert sanitize_text(input_text) == expected
