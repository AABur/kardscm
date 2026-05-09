"""Tests for kardscm.helpers.extract_locale."""

import pytest

from kardscm.helpers import extract_locale


def test_returns_locale_value_when_present():
    raw = '{"ru-RU": "\\u041f\\u0440\\u0438\\u0432\\u0435\\u0442", "en-EN": "Hello"}'
    assert extract_locale(raw, "ru-RU") == "Привет"


def test_returns_default_when_locale_missing_without_en_fallback():
    raw = '{"en-EN": "Hello"}'
    assert extract_locale(raw, "ru-RU") == ""
    assert extract_locale(raw, "ru-RU", default="X") == "X"


def test_returns_en_fallback_when_locale_missing_and_en_fallback_enabled():
    raw = '{"en-EN": "Hello"}'
    assert extract_locale(raw, "ru-RU", en_fallback=True) == "Hello"


def test_en_fallback_returns_default_when_neither_present():
    raw = '{"de-DE": "Hallo"}'
    assert extract_locale(raw, "ru-RU", default="X", en_fallback=True) == "X"


def test_returns_default_on_empty_or_none():
    assert extract_locale("", "ru-RU", default="d") == "d"
    assert extract_locale(None, "ru-RU", default="d") == "d"


def test_returns_default_on_malformed_json():
    assert extract_locale("not-json", "ru-RU", default="d") == "d"
    assert extract_locale('{"unclosed":', "ru-RU", default="d") == "d"


def test_returns_default_when_decoded_is_not_dict():
    # JSON-string ("Foo"), JSON-list, JSON-int — none are dict-shaped.
    assert extract_locale('"Foo"', "ru-RU", default="d") == "d"
    assert extract_locale("[1, 2, 3]", "ru-RU", default="d") == "d"
    assert extract_locale("42", "ru-RU", default="d") == "d"


def test_non_string_raw_is_stringified():
    assert extract_locale(42, "ru-RU") == "42"
    assert extract_locale([1, 2], "ru-RU") == "[1, 2]"


def test_falsy_value_at_locale_uses_en_fallback_when_enabled():
    # Empty string at the active locale should not block en-EN fallback.
    raw = '{"ru-RU": "", "en-EN": "Hello"}'
    assert extract_locale(raw, "ru-RU", en_fallback=True) == "Hello"
    assert extract_locale(raw, "ru-RU") == ""


@pytest.mark.parametrize(
    ("raw", "locale_key", "kwargs", "expected"),
    [
        ('{"ru-RU": "abc"}', "ru-RU", {}, "abc"),
        ('{"en-EN": "X"}', "ru-RU", {"en_fallback": True}, "X"),
        ('{"en-EN": "X"}', "ru-RU", {"en_fallback": True, "default": "fb"}, "X"),
        ("", "ru-RU", {"default": "fb"}, "fb"),
        ("invalid", "ru-RU", {"default": "fb"}, "fb"),
    ],
    ids=["direct", "en-fallback", "en-fallback-with-default", "empty", "malformed"],
)
def test_extract_locale_table(raw, locale_key, kwargs, expected):
    assert extract_locale(raw, locale_key, **kwargs) == expected
