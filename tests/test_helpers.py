"""Tests for kardscm.helpers utility functions."""

import pytest

from kardscm.helpers import decode_escapes, parse_int, sanitize_text, to_text


@pytest.mark.parametrize(
    ("input_val", "expected"),
    [
        ("42", 42),
        (None, None),
        ("", None),
        ("abc", None),
        (" 7 ", 7),
        ("0", 0),
        ("-3", -3),
        ("3.5", None),
    ],
    ids=["valid", "none", "empty", "invalid", "whitespace", "zero", "negative", "float_string"],
)
def test_parse_int(input_val, expected):
    assert parse_int(input_val) == expected


@pytest.mark.parametrize(
    ("input_val", "expected"),
    [
        (None, ""),
        (42, "42"),
        ("hello", "hello"),
        (0, "0"),
        ("", ""),
    ],
    ids=["none", "int_value", "string", "zero", "empty_string"],
)
def test_to_text(input_val, expected):
    assert to_text(input_val) == expected


class TestDecodeEscapes:
    def test_empty(self):
        assert decode_escapes("") == ""

    def test_no_escapes(self):
        assert decode_escapes("hello world") == "hello world"

    def test_newline(self):
        assert decode_escapes("hello\\nworld") == "hello\nworld"

    def test_tab(self):
        assert decode_escapes("hello\\tworld") == "hello\tworld"

    def test_unicode(self):
        assert decode_escapes("\\u0041") == "A"

    def test_hex(self):
        assert decode_escapes("\\x41") == "A"


class TestSanitizeText:
    def test_empty(self):
        assert sanitize_text("") == ""

    def test_newlines_replaced(self):
        assert sanitize_text("hello\nworld") == "hello world"

    def test_multiple_spaces_collapsed(self):
        assert sanitize_text("hello   world") == "hello world"

    def test_escapes_decoded(self):
        assert sanitize_text("hello\\nworld") == "hello world"

    def test_crlf(self):
        assert sanitize_text("hello\r\nworld") == "hello world"

    def test_none_passthrough(self):
        assert sanitize_text(None) is None
