"""Tests for kardscm.helpers utility functions."""

import pytest

from kardscm.helpers import parse_int, to_text


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
