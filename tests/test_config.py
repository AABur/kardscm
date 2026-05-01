"""Tests for kardscm.config — get_language_config()."""

from __future__ import annotations

import logging

from kardscm.config import get_language_config
from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU, LANGUAGES


def test_none_returns_english():
    """No argument -> LANGUAGE_EN."""
    assert get_language_config() is LANGUAGE_EN


def test_empty_string_returns_english():
    """Empty/whitespace -> LANGUAGE_EN."""
    assert get_language_config("") is LANGUAGE_EN
    assert get_language_config("   ") is LANGUAGE_EN


def test_explicit_en():
    """'en' -> LANGUAGE_EN."""
    assert get_language_config("en") is LANGUAGE_EN


def test_explicit_ru():
    """'ru' -> LANGUAGE_RU."""
    assert get_language_config("ru") is LANGUAGE_RU


def test_de_loads_from_registry():
    """'de' -> registry entry (regardless of fallback state)."""
    cfg = get_language_config("de")
    assert cfg is LANGUAGES["de"]
    assert cfg.code == "de"


def test_unsupported_language_falls_back(caplog):
    """Unknown code -> LANGUAGE_EN + warning."""
    with caplog.at_level(logging.WARNING, logger="kardscm.config"):
        result = get_language_config("xx")
    assert result is LANGUAGE_EN
    assert "Unsupported language 'xx'" in caplog.text


def test_strip_whitespace():
    """Surrounding whitespace stripped before lookup."""
    assert get_language_config("  ru  ") is LANGUAGE_RU


def test_case_sensitive_for_compound_codes(caplog):
    """Compound codes (e.g. 'zh-Hant') match exactly; 'zh-hant' would fall back."""
    if "zh-Hant" in LANGUAGES:
        assert get_language_config("zh-Hant") is LANGUAGES["zh-Hant"]
    with caplog.at_level(logging.WARNING, logger="kardscm.config"):
        result = get_language_config("RU")
    # 'RU' (uppercase) is not a registry key; fall back warns.
    if "RU" not in LANGUAGES:
        assert result is LANGUAGE_EN
