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


@pytest.mark.parametrize(
    ("input_val", "expected"),
    [
        ("", ""),
        ("hello world", "hello world"),
        ("hello\\nworld", "hello\nworld"),
        ("hello\\tworld", "hello\tworld"),
        ("\\u0041", "A"),
        ("\\x41", "A"),
    ],
    ids=["empty", "no_escapes", "newline", "tab", "unicode", "hex"],
)
def test_decode_escapes(input_val, expected):
    assert decode_escapes(input_val) == expected


@pytest.mark.parametrize(
    ("input_val", "expected"),
    [
        ("", ""),
        ("hello\nworld", "hello world"),
        ("hello   world", "hello world"),
        ("hello\\nworld", "hello world"),
        ("hello\r\nworld", "hello world"),
        (None, None),
    ],
    ids=[
        "empty",
        "newlines_replaced",
        "spaces_collapsed",
        "escapes_decoded",
        "crlf",
        "none_passthrough",
    ],
)
def test_sanitize_text(input_val, expected):
    assert sanitize_text(input_val) == expected
