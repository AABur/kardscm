"""Tests for kardscm.locales — TOML-based locale loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU, LANGUAGES, _build_registry

# ---------------------------------------------------------------------------
# Minimal but complete EN fixture for tmp_path tests.
# Must contain ALL 8 sections and ALL top-level keys.
# ---------------------------------------------------------------------------
_MINIMAL_EN = """\
code = "en"
name = "English"
locale_key = "en-EN"
collection_sheet_name = "Collection"
export_headers = ["Nation", "Name"]
deck_headers = ["Card", "Qty"]
deck_metadata_labels = ["Name"]

[factions]
Soviet = "Soviet Union"

[types]
infantry = "Infantry"

[rarities]
Standard = "Standard"

[sets]
Base = "Base"

[abilities]
alpine = "Alpine"
mobilize = "Mobilize"
salvage = "Salvage"

[extra_abilities]
pincer = "Pincer"

[nation_display_names]
soviet = "Soviet"
finland = "Finnish"

[ui_strings]
page_title = "kardscm collection"
modal_close = "close"

[diff_headers]
title = "Sync diff"
new = "New cards"
"""


def _write(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")


def _en(tmp_path: Path) -> None:
    _write(tmp_path, "en.toml", _MINIMAL_EN)


# ---------------------------------------------------------------------------
# Tests against the real shipped package locale files
# ---------------------------------------------------------------------------


def test_languages_registry_contains_en_and_ru() -> None:
    assert "en" in LANGUAGES
    assert "ru" in LANGUAGES
    assert LANGUAGES["en"] is LANGUAGE_EN
    assert LANGUAGES["ru"] is LANGUAGE_RU


def test_en_loads_complete() -> None:
    cfg = LANGUAGE_EN
    assert cfg.code == "en"
    assert cfg.faction_names != {}
    assert cfg.ability_names != {}
    assert cfg.ui_strings != {}
    assert cfg.diff_headers != {}
    assert cfg.fallback_warnings == []


def test_ru_loads_complete() -> None:
    cfg = LANGUAGE_RU
    assert cfg.code == "ru"
    assert cfg.fallback_warnings == []
    # Bug fixes that were applied in bootstrap
    assert cfg.nation_display_names["finland"] == "Финские"
    assert cfg.ability_names["mobilize"] == "Мобилизация"
    assert cfg.ability_names["salvage"] == "Утилизация"


# ---------------------------------------------------------------------------
# Tests using _build_registry(tmp_path) for isolation
# ---------------------------------------------------------------------------


def test_partial_language_per_key_fallback(tmp_path: Path) -> None:
    _en(tmp_path)
    _write(
        tmp_path,
        "xx.toml",
        '[abilities]\nalpine = "Alpinisch"\n',
    )
    registry = _build_registry(tmp_path)
    cfg = registry["xx"]
    assert cfg.ability_names["alpine"] == "Alpinisch"
    # 'mobilize' not present in xx.toml → EN fallback
    assert cfg.ability_names["mobilize"] == "Mobilize"
    assert "abilities.mobilize" in cfg.fallback_warnings
    assert "abilities.salvage" in cfg.fallback_warnings


def test_partial_language_section_fallback(tmp_path: Path) -> None:
    _en(tmp_path)
    # xx.toml has no sections at all
    _write(tmp_path, "xx.toml", 'code = "xx"\nname = "Test"\nlocale_key = "xx-XX"\n')
    registry = _build_registry(tmp_path)
    cfg = registry["xx"]
    en = registry["en"]
    assert cfg.ability_names == en.ability_names
    assert "[abilities]" in cfg.fallback_warnings


def test_broken_toml_falls_back(tmp_path: Path) -> None:
    _en(tmp_path)
    _write(tmp_path, "xx.toml", "not valid = toml !!!")
    registry = _build_registry(tmp_path)
    cfg = registry["xx"]
    en = registry["en"]
    assert cfg.ability_names == en.ability_names
    assert any("file unreadable:" in w for w in cfg.fallback_warnings)


def test_en_broken_raises(tmp_path: Path) -> None:
    _write(tmp_path, "en.toml", "not valid = toml !!!")
    with pytest.raises(SystemExit):
        _build_registry(tmp_path)


def test_en_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        _build_registry(tmp_path)


def test_en_incomplete_raises(tmp_path: Path) -> None:
    # en.toml is valid TOML but missing [types] section
    _write(
        tmp_path,
        "en.toml",
        'code = "en"\nname = "English"\nlocale_key = "en-EN"\n'
        'collection_sheet_name = "Collection"\n'
        "export_headers = []\ndeck_headers = []\ndeck_metadata_labels = []\n"
        '[factions]\nSoviet = "Soviet Union"\n'
        '[rarities]\nStandard = "Standard"\n'
        '[sets]\nBase = "Base"\n'
        '[abilities]\nalpine = "Alpine"\n'
        '[nation_display_names]\nsoviet = "Soviet"\n'
        '[ui_strings]\npage_title = "p"\n'
        '[diff_headers]\ntitle = "d"\n',
    )
    with pytest.raises(SystemExit):
        _build_registry(tmp_path)


def test_registry_built_from_filesystem(tmp_path: Path) -> None:
    _en(tmp_path)
    _write(
        tmp_path,
        "de.toml",
        'code = "de"\nname = "Deutsch"\nlocale_key = "de-DE"\n'
        'collection_sheet_name = "Sammlung"\n'
        "export_headers = []\ndeck_headers = []\ndeck_metadata_labels = []\n",
    )
    registry = _build_registry(tmp_path)
    assert "de" in registry
    assert registry["de"].code == "de"
    assert registry["de"].ability_names == registry["en"].ability_names  # EN fallback


def test_registry_skips_dotfiles(tmp_path: Path) -> None:
    _en(tmp_path)
    _write(tmp_path, ".draft.toml", 'code = "draft"\nname = "Draft"\n')
    registry = _build_registry(tmp_path)
    assert ".draft" not in registry
    assert "draft" not in registry


def test_en_scalar_wrong_type_raises(tmp_path: Path) -> None:
    # en.toml has a scalar field that is not a string (code = 123)
    _write(
        tmp_path,
        "en.toml",
        "code = 123\n"
        'name = "English"\nlocale_key = "en-EN"\ncollection_sheet_name = "Collection"\n'
        "export_headers = []\ndeck_headers = []\ndeck_metadata_labels = []\n"
        '[factions]\nSoviet = "Soviet Union"\n[types]\ninfantry = "Infantry"\n'
        '[rarities]\nStandard = "Standard"\n[sets]\nBase = "Base"\n'
        '[abilities]\nalpine = "Alpine"\n[nation_display_names]\nsoviet = "Soviet"\n'
        '[ui_strings]\npage_title = "p"\n[diff_headers]\ntitle = "d"\n',
    )
    with pytest.raises(SystemExit):
        _build_registry(tmp_path)


def test_en_list_field_wrong_type_raises(tmp_path: Path) -> None:
    # en.toml has export_headers as a plain string instead of a list
    _write(
        tmp_path,
        "en.toml",
        'code = "en"\nname = "English"\nlocale_key = "en-EN"\n'
        'collection_sheet_name = "Collection"\n'
        'export_headers = "Nation, Name"\ndeck_headers = []\ndeck_metadata_labels = []\n'
        '[factions]\nSoviet = "Soviet Union"\n[types]\ninfantry = "Infantry"\n'
        '[rarities]\nStandard = "Standard"\n[sets]\nBase = "Base"\n'
        '[abilities]\nalpine = "Alpine"\n[nation_display_names]\nsoviet = "Soviet"\n'
        '[ui_strings]\npage_title = "p"\n[diff_headers]\ntitle = "d"\n',
    )
    with pytest.raises(SystemExit):
        _build_registry(tmp_path)


def test_locale_code_body_differs_from_stem_warns(tmp_path: Path) -> None:
    # Non-EN TOML has `code` in body that differs from the file stem → warning recorded.
    _en(tmp_path)
    _write(
        tmp_path,
        "xx.toml",
        'code = "yy"\n'  # body says "yy" but stem is "xx"
        'name = "Test"\nlocale_key = "xx-XX"\ncollection_sheet_name = "Test"\n'
        "export_headers = []\ndeck_headers = []\ndeck_metadata_labels = []\n",
    )
    registry = _build_registry(tmp_path)
    cfg = registry["xx"]
    assert cfg.code == "xx"  # always from file stem
    assert "code" in cfg.fallback_warnings
