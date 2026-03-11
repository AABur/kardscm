"""Tests for kardscm.config — get_language_config() and get_advisor_config()."""

from __future__ import annotations

import logging

from kardscm.config import (
    LANGUAGE_EN,
    LANGUAGE_RU,
    AdvisorConfig,
    get_advisor_config,
    get_language_config,
)


def _write_ini(tmp_path, content: str) -> str:
    """Write a config.ini and return its path."""
    ini = tmp_path / "config.ini"
    ini.write_text(content, encoding="utf-8")
    return str(ini)


def test_missing_config_returns_english(tmp_path):
    """No config file -> returns LANGUAGE_EN."""
    result = get_language_config(str(tmp_path / "nonexistent.ini"))
    assert result is LANGUAGE_EN


def test_valid_en_config(tmp_path):
    """language=en -> LANGUAGE_EN."""
    path = _write_ini(tmp_path, "[settings]\nlanguage=en\n")
    assert get_language_config(path) is LANGUAGE_EN


def test_valid_ru_config(tmp_path):
    """language=ru -> LANGUAGE_RU."""
    path = _write_ini(tmp_path, "[settings]\nlanguage=ru\n")
    assert get_language_config(path) is LANGUAGE_RU


def test_unsupported_language_falls_back(tmp_path, caplog):
    """language=xx -> LANGUAGE_EN + warning."""
    path = _write_ini(tmp_path, "[settings]\nlanguage=xx\n")
    with caplog.at_level(logging.WARNING, logger="kardscm.config"):
        result = get_language_config(path)
    assert result is LANGUAGE_EN
    assert "Unsupported language 'xx'" in caplog.text


def test_language_case_insensitive(tmp_path):
    """language=RU -> LANGUAGE_RU (strip + lower)."""
    path = _write_ini(tmp_path, "[settings]\nlanguage=RU\n")
    assert get_language_config(path) is LANGUAGE_RU


def test_language_with_whitespace(tmp_path):
    """language= ru  -> LANGUAGE_RU."""
    path = _write_ini(tmp_path, "[settings]\nlanguage= ru \n")
    assert get_language_config(path) is LANGUAGE_RU


def test_missing_settings_section(tmp_path):
    """INI without [settings] -> fallback to en."""
    path = _write_ini(tmp_path, "[other]\nkey=value\n")
    assert get_language_config(path) is LANGUAGE_EN


def test_missing_language_key(tmp_path):
    """[settings] without language key -> fallback to en."""
    path = _write_ini(tmp_path, "[settings]\nother_key=value\n")
    assert get_language_config(path) is LANGUAGE_EN


# --- AdvisorConfig tests ---


def test_advisor_defaults_no_file(tmp_path):
    result = get_advisor_config(str(tmp_path / "nonexistent.ini"))
    assert result == AdvisorConfig()
    assert result.provider == "openai"
    assert result.model == "gpt-4o"
    assert result.depth == "standard"


def test_advisor_defaults_no_section(tmp_path):
    path = _write_ini(tmp_path, "[settings]\nlanguage=en\n")
    result = get_advisor_config(path)
    assert result == AdvisorConfig()


def test_advisor_custom_values(tmp_path):
    path = _write_ini(
        tmp_path,
        "[advisor]\nprovider = anthropic\nmodel = claude-sonnet-4-20250514\ndepth = detailed\n",
    )
    result = get_advisor_config(path)
    assert result.provider == "anthropic"
    assert result.model == "claude-sonnet-4-20250514"
    assert result.depth == "detailed"


def test_advisor_partial_values(tmp_path):
    path = _write_ini(tmp_path, "[advisor]\nprovider = google\n")
    result = get_advisor_config(path)
    assert result.provider == "google"
    assert result.model == "gpt-4o"
    assert result.depth == "standard"
