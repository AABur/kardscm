# Locale extraction to TOML — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move per-language card metadata from Python literals in `kardscm/config.py` to `kardscm/locales/*.toml` files so new languages can be added without code changes.

**Architecture:** Create `kardscm/locales/__init__.py` that declares `LanguageConfig`, scans `*.toml` at import, builds each language with per-key EN fallback, and exposes `LANGUAGES`/`LANGUAGE_EN`/`LANGUAGE_RU` singletons. `kardscm/config.py` becomes thin (only `get_language_config()` + type re-export). All callers update imports mechanically.

**Tech Stack:** Python 3.12, stdlib `tomllib`, `dataclasses.replace`, `typer.echo`, FastAPI/Jinja2 templates, pytest, `uv run pytest`

---

## File map

| Action | File | Responsibility |
|---|---|---|
| Create | `kardscm/locales/__init__.py` | `LanguageConfig` declaration + TOML loader + `LANGUAGES` registry |
| Create | `kardscm/locales/en.toml` | EN locale data (canonical baseline) |
| Create | `kardscm/locales/ru.toml` | RU locale data (with 3 bug fixes) |
| Create | `tests/test_locales.py` | Loader unit tests |
| Modify | `kardscm/config.py` | Delete literals; import from locales; re-export `LanguageConfig` type |
| Modify | `kardscm/commands.py` | Add `_emit_locale_warnings()` helper; call after `get_language_config()` in 6 functions |
| Modify | `kardscm/web/app.py` | Switch `LANGUAGES` import; register Jinja global |
| Modify | `kardscm/web/templates/base.html` | Add warning strip block |
| Modify | `kardscm/web/static/main.css` | Add `.locale-warning-strip` CSS rule |
| Modify | `tests/test_config.py` | Update 1 import line |
| Modify | `tests/test_collection_export.py` | Update 1 import line |
| Modify | `tests/test_diff.py` | Update 1 import line |
| Modify | `tests/test_translate.py` | Update 1 import line |
| Modify | `tests/test_exporters.py` | Update 1 import line |
| Modify | `tests/test_commands.py` | Update 1 import line |
| Modify | `tests/web/test_routes.py` | Update 1 import line + add 2 warning strip tests |
| Modify | `config.ini` | Drop stale comment |
| Modify | `README.md` | Drop DB-reset note; update "Adding a new language" |
| Modify | `CONTRIBUTING.md` | Rewrite "Adding a New Language" section |
| Modify | `CHANGELOG.md` | Add Unreleased / 0.5.1 entry |

---

### Task 1: Add `fallback_warnings` field to `LanguageConfig`

**Files:**
- Modify: `kardscm/config.py:16-33`

This is an additive change. All existing `LanguageConfig` construction works unchanged because the field has a default factory.

- [ ] **Step 1: Edit `kardscm/config.py`** — add `fallback_warnings` as the last field in `LanguageConfig`:

```python
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
    fallback_warnings: list[str] = field(default_factory=list)
```

- [ ] **Step 2: Run the test suite to confirm no regressions**

```bash
uv run pytest -x -q
```

Expected: all 263 tests pass. The new field is invisible to existing tests (default `[]`).

- [ ] **Step 3: Commit**

```bash
git add kardscm/config.py
git commit -m "feat: add fallback_warnings field to LanguageConfig"
```

---

### Task 2: Write failing loader tests

**Files:**
- Create: `tests/test_locales.py`

All tests import from `kardscm.locales` which doesn't exist yet — they fail with `ModuleNotFoundError`.

- [ ] **Step 1: Create `tests/test_locales.py`** with the following content:

```python
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
        'export_headers = []\ndeck_headers = []\ndeck_metadata_labels = []\n'
        "[factions]\nSoviet = \"Soviet Union\"\n"
        "[rarities]\nStandard = \"Standard\"\n"
        "[sets]\nBase = \"Base\"\n"
        "[abilities]\nalpine = \"Alpine\"\n"
        "[nation_display_names]\nsoviet = \"Soviet\"\n"
        "[ui_strings]\npage_title = \"p\"\n"
        "[diff_headers]\ntitle = \"d\"\n",
        # Note: [types] is intentionally absent
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
```

- [ ] **Step 2: Run to confirm they all fail**

```bash
uv run pytest tests/test_locales.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'kardscm.locales'` (or similar). All tests collected and failing is the goal.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_locales.py
git commit -m "test: add failing tests for locale loader"
```

---

### Task 3: Create `kardscm/locales/__init__.py`

**Files:**
- Create: `kardscm/locales/__init__.py`

This file declares `LanguageConfig` (moved from `config.py`), the full loader, and the package-level singletons.

- [ ] **Step 1: Create the directory and `__init__.py`**

```bash
mkdir kardscm/locales
```

Create `kardscm/locales/__init__.py` with this exact content:

```python
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

    return LanguageConfig(
        **scalars,
        **lists,
        **sections,
        fallback_warnings=warnings,
    )


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
```

- [ ] **Step 2: Run only the module-load check** (en.toml doesn't exist yet — this should `SystemExit`)

```bash
uv run python -c "import kardscm.locales" 2>&1 | head -5
```

Expected: `FATAL: .../kardscm/locales/en.toml is missing — package is broken.`

---

### Task 4: Create `kardscm/locales/en.toml`

**Files:**
- Create: `kardscm/locales/en.toml`

Verbatim mirror of `LANGUAGE_EN` at `kardscm/config.py:36-143`. No semantic changes.

- [ ] **Step 1: Create `kardscm/locales/en.toml`**:

```toml
code = "en"
name = "English"
locale_key = "en-EN"
collection_sheet_name = "Collection"

export_headers = [
    "Nation", "Name", "Type", "Rarity", "Abilities", "Set",
    "Quantity", "Credits", "Attack", "Defense", "Description",
]
deck_headers = ["Card", "Type", "Quantity", "Credits", "Attack", "Defense"]
deck_metadata_labels = ["Name", "Major power", "Ally", "HQ", "Code"]

[factions]
Soviet = "Soviet Union"
USA = "USA"
Britain = "Britain"
Germany = "Germany"
Japan = "Japan"
France = "France"
Italy = "Italy"
Poland = "Poland"
Finland = "Finland"

[types]
infantry = "Infantry"
tank = "Tank"
artillery = "Artillery"
fighter = "Fighter"
order = "Order"
countermeasure = "Countermeasure"

[rarities]
Standard = "Standard"
Limited = "Limited"
Special = "Special"
Elite = "Elite"

[sets]
Base = "Base"
Allegiance = "Allegiance"
TheatersOfWar = "Theaters of War"
Breakthrough = "Breakthrough"
WorldAtWar = "World at War"
CovertOps = "Covert Ops"
BloodAndIron = "Blood and Iron"
Legions = "Legions"
NavalWarfare = "Naval Warfare"
Homefront = "Homefront"
WinterWar = "Winter War"

[abilities]
alpine = "Alpine"
ambush = "Ambush"
blitz = "Blitz"
bond = "Bond"
covert = "Covert"
fury = "Fury"
guard = "Guard"
heavyArmor1 = "Heavy Armor 1"
heavyArmor2 = "Heavy Armor 2"
heavyArmor3 = "Heavy Armor 3"
intel1 = "Intel 1"
intel2 = "Intel 2"
intel3 = "Intel 3"
mobilize = "Mobilize"
salvage = "Salvage"
shock = "Shock"
smokescreen = "Smokescreen"

[nation_display_names]
soviet = "Soviet"
usa = "American"
britain = "British"
germany = "German"
japan = "Japanese"
france = "French"
italy = "Italian"
poland = "Polish"
finland = "Finnish"

[ui_strings]
page_title = "kardscm collection"
search_placeholder = "search by name…"
toggle_spawnable = "spawnable"
toggle_reserved = "reserved"
toggle_owned = "only owned"
col_cost = "Cost"
card_id_label = "cardId"
saved_hint = "saves automatically (Tab/Enter)"
modal_close = "close"

[diff_headers]
title = "Sync diff"
new = "New cards"
changed = "Changed characteristics"
reserved_in = "Moved to reserve"
reserved_out = "Returned from reserve"
removed = "Removed cards"
```

- [ ] **Step 2: Verify `en.toml` loads**

```bash
uv run python -c "from kardscm.locales import LANGUAGE_EN; print(LANGUAGE_EN.code, LANGUAGE_EN.faction_names)"
```

Expected: `en {'Soviet': 'Soviet Union', 'USA': 'USA', ...}`

---

### Task 5: Create `kardscm/locales/ru.toml`

**Files:**
- Create: `kardscm/locales/ru.toml`

Mirror of `LANGUAGE_RU` at `kardscm/config.py:146-258` with three bug fixes applied.

- [ ] **Step 1: Create `kardscm/locales/ru.toml`** with these corrections vs the Python source:
  - `[nation_display_names].finland = "Финские"` (was missing)
  - `[abilities].mobilize = "Мобилизация"` (was `"Моблизация"`)
  - `[abilities].salvage = "Утилизация"` (was `"Утилизауия"`)

Full content:

```toml
code = "ru"
name = "Russian"
locale_key = "ru-RU"
collection_sheet_name = "Коллекция"

export_headers = [
    "Нация", "Название", "Тип", "Редкость", "Способности", "Сет",
    "Количество", "Кредиты", "Атака", "Защита", "Описание",
]
deck_headers = ["Карта", "Тип", "Количество", "Кредиты", "Атака", "Защита"]
deck_metadata_labels = ["Название", "Основная нация", "Союзная нация", "Штаб", "Код"]

[factions]
Soviet = "Советский Союз"
USA = "США"
Britain = "Великобритания"
Germany = "Германия"
Japan = "Япония"
France = "Франция"
Italy = "Италия"
Poland = "Польша"
Finland = "Финляндия"

[types]
infantry = "Пехота"
tank = "Танк"
artillery = "Артиллерия"
fighter = "Истребитель"
order = "Приказ"
countermeasure = "Контрмера"

[rarities]
Standard = "Стандартная"
Limited = "Лимитированная"
Special = "Специальная"
Elite = "Элитная"

[sets]
Base = "Базовый"
Allegiance = "Верность"
TheatersOfWar = "Театры войны"
Breakthrough = "Прорыв"
WorldAtWar = "Мировая война"
CovertOps = "Тайные операции"
BloodAndIron = "Кровь и железо"
Legions = "Легионы"
NavalWarfare = "Морская война"
Homefront = "Тыл"
WinterWar = "Зимняя война"

[abilities]
alpine = "Альпийский"
ambush = "Засада"
blitz = "Блиц"
bond = "Узы"
covert = "Скрытность"
fury = "Ярость"
guard = "Охрана"
heavyArmor1 = "Тяжёлая броня 1"
heavyArmor2 = "Тяжёлая броня 2"
heavyArmor3 = "Тяжёлая броня 3"
intel1 = "Разведка 1"
intel2 = "Разведка 2"
intel3 = "Разведка 3"
mobilize = "Мобилизация"
salvage = "Утилизация"
shock = "Штурм"
smokescreen = "Дымовая завеса"

[nation_display_names]
soviet = "Советские"
usa = "Американские"
britain = "Британские"
germany = "Германские"
japan = "Японские"
france = "Французские"
italy = "Итальянские"
poland = "Польские"
finland = "Финские"

[ui_strings]
page_title = "Коллекция kardscm"
search_placeholder = "поиск по названию…"
toggle_spawnable = "спаунятся"
toggle_reserved = "в резерве"
toggle_owned = "только мои"
col_cost = "Стоимость"
card_id_label = "cardId"
saved_hint = "сохраняется автоматически (Tab/Enter)"
modal_close = "закрыть"

[diff_headers]
title = "Изменения синхронизации"
new = "Новые карты"
changed = "Изменённые характеристики"
reserved_in = "Ушли в резерв"
reserved_out = "Вернулись из резерва"
removed = "Удалённые карты"
```

- [ ] **Step 2: Run the loader tests**

```bash
uv run pytest tests/test_locales.py -v
```

Expected: all 10 tests pass. Fix any failures before proceeding.

- [ ] **Step 3: Commit**

```bash
git add kardscm/locales/
git commit -m "feat: add locales loader and TOML files for EN and RU"
```

---

### Task 6: Migrate caller imports (7 test files + web/app.py)

**Files:**
- Modify: `tests/test_config.py:7`
- Modify: `tests/test_collection_export.py:12`
- Modify: `tests/test_diff.py:7`
- Modify: `tests/test_translate.py:7`
- Modify: `tests/test_exporters.py:10`
- Modify: `tests/test_commands.py:24`
- Modify: `tests/web/test_routes.py:11`
- Modify: `kardscm/web/app.py:16`

Update import paths **before** removing the literals from `config.py`. At this point `config.py` still exports everything, so the test suite stays green after each sub-step.

- [ ] **Step 1: Update `tests/test_config.py`** — change line 7:

```python
# Before:
from kardscm.config import LANGUAGE_EN, LANGUAGE_RU, get_language_config
# After:
from kardscm.config import get_language_config
from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU
```

- [ ] **Step 2: Update `tests/test_collection_export.py`** — change line 12:

```python
# Before:
from kardscm.config import LANGUAGE_RU
# After:
from kardscm.locales import LANGUAGE_RU
```

- [ ] **Step 3: Update `tests/test_diff.py`** — change line 7:

```python
# Before:
from kardscm.config import LANGUAGE_EN, LANGUAGE_RU
# After:
from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU
```

- [ ] **Step 4: Update `tests/test_translate.py`** — change line 7:

```python
# Before:
from kardscm.config import LANGUAGE_EN, LANGUAGE_RU
# After:
from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU
```

- [ ] **Step 5: Update `tests/test_exporters.py`** — change line 10:

```python
# Before:
from kardscm.config import LANGUAGE_EN
# After:
from kardscm.locales import LANGUAGE_EN
```

- [ ] **Step 6: Update `tests/test_commands.py`** — change line 24:

```python
# Before:
from kardscm.config import LANGUAGE_EN
# After:
from kardscm.locales import LANGUAGE_EN
```

- [ ] **Step 7: Update `tests/web/test_routes.py`** — change line 11:

```python
# Before:
from kardscm.config import LANGUAGE_EN, LANGUAGE_RU
# After:
from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU
```

- [ ] **Step 8: Update `kardscm/web/app.py`** — change line 16:

```python
# Before:
from kardscm.config import LANGUAGES, LanguageConfig, get_language_config
# After:
from kardscm.config import LanguageConfig, get_language_config
from kardscm.locales import LANGUAGES
```

- [ ] **Step 9: Run the full test suite**

```bash
uv run pytest -x -q
```

Expected: all 263+ tests pass. At this point `config.py` still has the Python literals, so both old and new import paths resolve correctly.

- [ ] **Step 10: Commit**

```bash
git add tests/ kardscm/web/app.py
git commit -m "refactor: migrate import paths from kardscm.config to kardscm.locales"
```

---

### Task 7: Remove literals from `kardscm/config.py`

**Files:**
- Modify: `kardscm/config.py`

Now that all callers import from `kardscm.locales`, the Python literals and dataclass declaration in `config.py` are dead code. Replace the entire file with the thin version. `LanguageConfig` is re-exported as a type convenience (callers type-hint with it); data singletons are NOT re-exported.

- [ ] **Step 1: Replace `kardscm/config.py`** with this complete content:

```python
"""Language configuration management."""

from __future__ import annotations

import configparser
import logging
from pathlib import Path

from kardscm.locales import LANGUAGE_EN, LANGUAGES, LanguageConfig

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.ini"

__all__ = ["LanguageConfig", "get_language_config", "CONFIG_FILE"]


def get_language_config(config_path: str = CONFIG_FILE) -> LanguageConfig:
    """Load language configuration from config.ini.

    Returns:
        LanguageConfig for the configured language. Defaults to English.
    """
    path = Path(config_path)

    if not path.exists():
        return LANGUAGE_EN

    config = configparser.ConfigParser()
    config.read(path)

    code = config.get("settings", "language", fallback="en").strip().lower()
    if code not in LANGUAGES:
        logger.warning("Unsupported language '%s', falling back to English", code)
        return LANGUAGE_EN

    return LANGUAGES[code]
```

- [ ] **Step 2: Run the full test suite**

```bash
uv run pytest -x -q
```

Expected: all tests pass. Callers already import from `kardscm.locales`, so removing the literals from `config.py` causes no breakage.

- [ ] **Step 3: Run mypy**

```bash
uv run mypy kardscm/
```

Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add kardscm/config.py
git commit -m "refactor: remove LanguageConfig literals from config.py"
```

---

### Task 8: Add CLI locale warning helper

**Files:**
- Modify: `kardscm/commands.py`
- Modify: `tests/test_commands.py` (add 3 new tests)

- [ ] **Step 1: Add failing tests for `_emit_locale_warnings`** — append to `tests/test_commands.py`:

```python
# ---------------------------------------------------------------------------
# Locale warning tests
# ---------------------------------------------------------------------------


def test_emit_locale_warnings_silent_when_no_warnings(capsys) -> None:
    from kardscm.commands import _emit_locale_warnings

    _emit_locale_warnings(LANGUAGE_EN)
    assert capsys.readouterr().err == ""


def test_emit_locale_warnings_emits_to_stderr(capsys) -> None:
    from dataclasses import replace

    from kardscm.commands import _emit_locale_warnings

    cfg = replace(LANGUAGE_EN, fallback_warnings=["abilities.mobilize", "ui_strings.modal_close"])
    _emit_locale_warnings(cfg)
    captured = capsys.readouterr()
    assert "Locale 'en': 2 key(s)" in captured.err
    assert "abilities.mobilize" in captured.err
    assert captured.out == ""


def test_emit_locale_warnings_truncates_after_five(capsys) -> None:
    from dataclasses import replace

    from kardscm.commands import _emit_locale_warnings

    keys = [f"section.key{i}" for i in range(8)]
    cfg = replace(LANGUAGE_EN, fallback_warnings=keys)
    _emit_locale_warnings(cfg)
    captured = capsys.readouterr()
    assert "8 key(s)" in captured.err
    assert "… and 3 more" in captured.err
```

- [ ] **Step 2: Run to confirm new tests fail**

```bash
uv run pytest tests/test_commands.py -k "emit" -v
```

Expected: `ImportError: cannot import name '_emit_locale_warnings'`.

- [ ] **Step 3: Add `_emit_locale_warnings` to `kardscm/commands.py`** — insert after `_safe_timestamp()` (around line 63):

```python
def _emit_locale_warnings(cfg: LanguageConfig) -> None:
    if not cfg.fallback_warnings:
        return
    keys = cfg.fallback_warnings
    summary = ", ".join(keys[:5])
    suffix = f", … and {len(keys) - 5} more" if len(keys) > 5 else ""
    typer.echo(
        f"Locale '{cfg.code}': {len(keys)} key(s) fell back to English "
        f"({summary}{suffix}).",
        err=True,
    )
```

- [ ] **Step 4: Wire warning into each command** — add `_emit_locale_warnings(lang_config)` on the line immediately after every `lang_config = get_language_config()` call **in top-level command functions** (not in `_read_xlsx_quantities`).

Locations to update (reference the function they belong to):

```python
# sync_collection (line ~206):
lang_config = get_language_config()
_emit_locale_warnings(lang_config)   # add this

# export_collection (line ~258):
lang_config = get_language_config()
_emit_locale_warnings(lang_config)   # add this

# update_collection (line ~295):
lang_config = get_language_config()
_emit_locale_warnings(lang_config)   # add this

# import_deck (line ~336):
lang_config = get_language_config()
_emit_locale_warnings(lang_config)   # add this

# add_deck (line ~391):
lang_config = get_language_config()
_emit_locale_warnings(lang_config)   # add this

# export_deck (line ~566):
lang_config = get_language_config()
_emit_locale_warnings(lang_config)   # add this
```

Do NOT add it inside `_read_xlsx_quantities` (line 143) — that is a private helper.

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_commands.py -v -q
```

Expected: all pass (existing tests use `mock_config.return_value = LANGUAGE_EN` which has `fallback_warnings=[]`, so `_emit_locale_warnings` is a no-op for them).

- [ ] **Step 6: Commit**

```bash
git add kardscm/commands.py tests/test_commands.py
git commit -m "feat: emit locale fallback warnings to stderr in CLI commands"
```

---

### Task 9: Web locale warning strip

**Files:**
- Modify: `kardscm/web/templates/base.html`
- Modify: `kardscm/web/static/main.css`
- Modify: `kardscm/web/app.py` (register Jinja global)
- Modify: `tests/web/test_routes.py` (add 2 tests)

- [ ] **Step 1: Add failing tests** — append to `tests/web/test_routes.py`:

```python
class TestLocaleWarningStrip:
    def test_strip_visible_when_warnings_present(self, db_path: Path) -> None:
        from dataclasses import replace

        cfg = replace(LANGUAGE_EN, fallback_warnings=["abilities.mobilize"])
        app = create_app(db_path, lang_config=cfg)
        client = TestClient(app)
        r = client.get("/")
        assert r.status_code == 200
        assert 'class="locale-warning-strip"' in r.text
        assert "abilities.mobilize" in r.text

    def test_strip_absent_when_no_warnings(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert "locale-warning-strip" not in r.text
```

- [ ] **Step 2: Run to confirm new tests fail**

```bash
uv run pytest tests/web/test_routes.py -k "strip" -v
```

Expected: `test_strip_visible_when_warnings_present` fails (strip not in HTML); `test_strip_absent_when_no_warnings` passes (strip already not present).

- [ ] **Step 3: Register Jinja global in `kardscm/web/app.py`** — add one line after `templates = Jinja2Templates(...)` (line 115):

```python
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["fallback_warnings"] = cfg.fallback_warnings  # add this
```

- [ ] **Step 4: Update `kardscm/web/templates/base.html`**:

```html
<!doctype html>
<html lang="{{ lang }}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>kardscm</title>
    <link rel="stylesheet" href="/static/main.css">
    <script src="/static/htmx.min.js" defer></script>
  </head>
  <body>
    {% if fallback_warnings %}
      <div class="locale-warning-strip" role="status">
        Locale <code>{{ lang }}</code>:
        {{ fallback_warnings|length }} key(s) fell back to English.
        <details>
          <summary>show keys</summary>
          <ul>{% for w in fallback_warnings %}<li><code>{{ w }}</code></li>{% endfor %}</ul>
        </details>
      </div>
    {% endif %}
    <main>
      {% block content %}{% endblock %}
    </main>
    <div id="modal"></div>
  </body>
</html>
```

- [ ] **Step 5: Append CSS to `kardscm/web/static/main.css`**:

```css
.locale-warning-strip {
  background: #fff3cd;
  border-bottom: 1px solid #f0c674;
  padding: .5rem 1rem;
  font-size: .9em;
}
.locale-warning-strip details {
  display: inline;
}
.locale-warning-strip summary {
  display: inline;
  cursor: pointer;
  margin-left: .5em;
}
```

- [ ] **Step 6: Run web tests**

```bash
uv run pytest tests/web/ -v
```

Expected: all pass, including the two new strip tests.

- [ ] **Step 7: Commit**

```bash
git add kardscm/web/templates/base.html kardscm/web/static/main.css kardscm/web/app.py tests/web/test_routes.py
git commit -m "feat: show locale fallback warning strip in web UI"
```

---

### Task 10: Documentation updates

**Files:**
- Modify: `config.ini`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `CHANGELOG.md`

No tests for docs. Make targeted edits only.

- [ ] **Step 1: Update `config.ini`** — replace the header comments:

```ini
[settings]
# Supported languages: see kardscm/locales/*.toml
language = ru
```

(Remove the two old comment lines: `# Supported languages: en, ru` and `# Changing language requires deleting collection.db and re-running sync`)

- [ ] **Step 2: Update `README.md`** — find the block around lines 56-62 and replace:

```markdown
Supported languages: every `*.toml` in `kardscm/locales/` is a language. To add one,
drop `<code>.toml` into that directory and set `language = <code>` in `config.ini`.
Missing keys fall back to English with a runtime warning.
```

Remove the sentence "Changing the language requires deleting `collection.db` and re-running sync." entirely.

Also replace the reference to CONTRIBUTING.md for adding a language (line ~62):
```markdown
> See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on adding a new language.
```
becomes:
```markdown
> To add a new language: drop `<code>.toml` into `kardscm/locales/` and set `language = <code>` in `config.ini`. Missing keys fall back to English with a runtime warning.
```

- [ ] **Step 3: Update `CONTRIBUTING.md`** — find the "Adding a New Language" section (around line 88) and replace the entire section body:

```markdown
### Adding a New Language

1. Create `kardscm/locales/<code>.toml` (e.g. `de.toml` for German).
2. Use `kardscm/locales/en.toml` as the schema reference. All top-level keys and sections must be present for a full translation; any key you omit falls back to the English value.
3. A partially-translated locale is valid — the loader records which keys fell back and surfaces a warning on CLI (stderr) and web UI (yellow strip at page top).
4. Set `language = <code>` in `config.ini` to activate the locale.

No code changes needed. No tests required for new locale files — the loader is already covered by `tests/test_locales.py`.
```

- [ ] **Step 4: Update `CHANGELOG.md`** — add a new section at the top (after `## [Unreleased]` or before the latest release):

```markdown
## [0.5.1] — Unreleased

### Changed
- Refactored: per-language data extracted from Python literals to TOML files in `kardscm/locales/`. Adding a new language no longer requires editing Python source — drop a `<code>.toml` file and restart.
- `LanguageConfig` dataclass moved from `kardscm/config.py` to `kardscm/locales/__init__.py`. The import path `from kardscm.config import LanguageConfig` continues to work.

### Fixed
- RU locale: missing `finland` entry in `nation_display_names` (was falling back to internal key).
- RU locale: typo `"Моблизация"` → `"Мобилизация"` in `ability_names.mobilize`.
- RU locale: typo `"Утилизауия"` → `"Утилизация"` in `ability_names.salvage`.

### Added
- Non-blocking locale diagnostics: missing or malformed locale keys fall back to English and surface a warning on CLI (stderr) and web UI (yellow strip).
```

- [ ] **Step 5: Commit**

```bash
git add config.ini README.md CONTRIBUTING.md CHANGELOG.md
git commit -m "docs: update language docs for TOML locale system"
```

---

### Task 11: Final verification

- [ ] **Step 1: Full check**

```bash
make check
```

Expected: ruff format, ruff check, mypy, pytest all pass. Coverage ≥94%.

- [ ] **Step 2: Smoke test RU export**

```bash
uv run kardscm export --format xlsx --file /tmp/check.xlsx
```

Expected: exits cleanly, no stderr warnings (RU locale is complete). Open the file and confirm header row is in Russian and `Нация` is present.

- [ ] **Step 3: Smoke test fallback warning**

```bash
# Temporarily comment out mobilize = "Мобилизация" in kardscm/locales/ru.toml
uv run kardscm export --format xlsx --file /tmp/check.xlsx 2>&1 | grep Locale
```

Expected: `Locale 'ru': 1 key(s) fell back to English (abilities.mobilize).`

```bash
# Restore the line in ru.toml
```

- [ ] **Step 4: Smoke test web UI**

```bash
uv run kardscm web --lang ru
```

Expected: server starts, opens in browser with no yellow strip. RU UI strings visible (`Коллекция kardscm`, etc.).

- [ ] **Step 5: Final commit (if any lint fixes were needed)**

If `make check` required any fixes, commit them:

```bash
git add -p
git commit -m "fix: address lint warnings after locale extraction"
```

Otherwise no commit needed — work is complete on `feat/locale-extract`.
