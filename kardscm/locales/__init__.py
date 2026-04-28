"""Locale loader — discovers *.toml in this package directory at import time."""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

_LOCALES_DIR = Path(__file__).parent

_SECTION_TO_FIELD: dict[str, str] = {
    "factions": "faction_names",
    "types": "type_names",
    "rarities": "rarity_names",
    "sets": "set_names",
    "abilities": "ability_names",
    "nation_display_names": "nation_display_names",
    "ui_strings": "ui_strings",
    "diff_headers": "diff_headers",
}

_TOP_LEVEL_SCALARS = ("code", "name", "locale_key", "collection_sheet_name")
_TOP_LEVEL_LISTS = ("export_headers", "deck_headers", "deck_metadata_labels")


@dataclass(frozen=True)
class LanguageConfig:
    """Language-specific configuration."""

    code: str
    name: str
    locale_key: str
    export_headers: list[str] = field(default_factory=list)
    faction_names: dict[str, str] = field(default_factory=dict)
    type_names: dict[str, str] = field(default_factory=dict)
    rarity_names: dict[str, str] = field(default_factory=dict)
    set_names: dict[str, str] = field(default_factory=dict)
    nation_display_names: dict[str, str] = field(default_factory=dict)
    deck_headers: list[str] = field(default_factory=list)
    deck_metadata_labels: list[str] = field(default_factory=list)
    collection_sheet_name: str = "Collection"
    ability_names: dict[str, str] = field(default_factory=dict)
    diff_headers: dict[str, str] = field(default_factory=dict)
    ui_strings: dict[str, str] = field(default_factory=dict)
    # Populated by the TOML loader for keys missing or malformed in a non-EN
    # locale file; empty for fully translated locales and static instances.
    fallback_warnings: list[str] = field(default_factory=list)


def _load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def _build_en(raw: dict) -> LanguageConfig:
    missing: list[str] = []
    for key in _TOP_LEVEL_SCALARS + _TOP_LEVEL_LISTS:
        if key not in raw:
            missing.append(key)
    for section in _SECTION_TO_FIELD:
        if section not in raw or not isinstance(raw[section], dict):
            missing.append(f"[{section}]")
    if missing:
        raise ValueError(f"en.toml is incomplete; missing: {', '.join(missing)}")

    kwargs: dict = {k: raw[k] for k in _TOP_LEVEL_SCALARS}
    for k in _TOP_LEVEL_LISTS:
        kwargs[k] = list(raw[k])
    for section, field_name in _SECTION_TO_FIELD.items():
        kwargs[field_name] = dict(raw[section])
    return LanguageConfig(fallback_warnings=[], **kwargs)


def _build_with_fallback(code: str, raw: dict, en: LanguageConfig) -> LanguageConfig:
    warnings: list[str] = []

    # `code` comes from the file stem, not the TOML body.
    scalars: dict[str, str] = {"code": raw.get("code", code)}
    for key in _TOP_LEVEL_SCALARS:
        if key == "code":
            continue
        if key in raw:
            scalars[key] = raw[key]
        else:
            scalars[key] = getattr(en, key)
            warnings.append(key)

    lists: dict[str, list[str]] = {}
    for key in _TOP_LEVEL_LISTS:
        val = raw.get(key)
        if isinstance(val, list) and all(isinstance(x, str) for x in val):
            lists[key] = list(val)
        else:
            lists[key] = list(getattr(en, key))
            warnings.append(key)

    sections: dict[str, dict[str, str]] = {}
    for section, field_name in _SECTION_TO_FIELD.items():
        en_section: dict[str, str] = getattr(en, field_name)
        raw_section = raw.get(section)
        if not isinstance(raw_section, dict):
            sections[field_name] = dict(en_section)
            warnings.append(f"[{section}]")
            continue
        merged = dict(en_section)
        for k, v in raw_section.items():
            if isinstance(v, str):
                merged[k] = v
        for k in en_section:
            if k not in raw_section:
                warnings.append(f"{section}.{k}")
        sections[field_name] = merged

    kwargs: dict[str, Any] = {**scalars, **lists, **sections}
    return LanguageConfig(**kwargs, fallback_warnings=warnings)


def _build_registry(locales_dir: Path) -> dict[str, LanguageConfig]:
    en_path = locales_dir / "en.toml"
    if not en_path.exists():
        sys.exit(f"FATAL: {en_path} is missing — package is broken.")
    try:
        en_raw = _load_toml(en_path)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        sys.exit(f"FATAL: {en_path} is malformed: {exc}")
    try:
        en = _build_en(en_raw)
    except ValueError as exc:
        sys.exit(f"FATAL: {exc}")

    registry: dict[str, LanguageConfig] = {"en": en}
    for path in sorted(locales_dir.glob("*.toml")):
        if path.name.startswith("."):
            continue
        if path.name == "en.toml":
            continue
        code = path.stem
        try:
            raw = _load_toml(path)
        except (tomllib.TOMLDecodeError, OSError) as exc:
            cfg = _build_with_fallback(code, {}, en)
            registry[code] = replace(
                cfg,
                fallback_warnings=[f"file unreadable: {type(exc).__name__}"],
            )
            continue
        registry[code] = _build_with_fallback(code, raw, en)
    return registry


LANGUAGES: dict[str, LanguageConfig] = _build_registry(_LOCALES_DIR)
LANGUAGE_EN: LanguageConfig = LANGUAGES["en"]
LANGUAGE_RU: LanguageConfig = LANGUAGES["ru"]
