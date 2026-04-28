# Locale extraction to TOML — Design

**Status:** ready for review
**Date:** 2026-04-29
**Target version:** 0.5.1
**Branch:** `feat/locale-extract`

## Context

All per-language card metadata (faction names, ability names, UI strings, export headers, deck headers, set names, etc.) currently lives as Python literals inside `kardscm/config.py` — `LANGUAGE_EN` and `LANGUAGE_RU`, ~220 lines of dict and list literals each. Adding a new language today requires editing Python source and re-releasing the package. The data is also tightly coupled to the dataclass declaration, so contributors who only want to translate must read code instead of editing data.

This refactor moves all per-language data into `kardscm/locales/<code>.toml` files so:

- New languages = drop a TOML file. No code changes, no rebuild.
- Missing or malformed keys fall back to English with a non-fatal warning surfaced both on CLI (stderr) and in the web UI (yellow strip under the body).
- Three latent RU bugs get fixed in the bootstrap step (one missing key, two typos).

Baseline at branch tip (`faaf91c`): 263 tests green, coverage 94%, ruff/mypy clean.

## Non-goals

- A user-facing locale-management command (e.g. `kardscm locale validate`). Loader warnings are sufficient for the current contributor workflow.
- Hot-reload of locale files. Eager load at import is fine for a CLI tool.
- A third locale in this PR. The refactor must support adding one, but only EN and RU ship with `0.5.1`.
- DB migration. Card lookups already use `locale_key` via `json_extract`; no schema change.
- Translating language metadata itself (`name`, `code`). Locale `name` stays in the locale's own language ("English", "Russian", "Deutsch") — that's how language pickers conventionally work.

## User-facing behavior

### CLI
```bash
$ uv run kardscm sync                       # uses language from config.ini
$ uv run kardscm export --format xlsx --file cards.xlsx
```
If the active locale is missing keys or unreadable, the command runs to completion using English fallbacks. After the command finishes, a single line is printed to **stderr**:
```
Locale 'ru': 2 key(s) fell back to English (abilities.mobilize, ui_strings.modal_close).
```
For more than five fallbacks, the line lists the first five followed by `… and N more`.

### Web
The yellow `<div class="locale-warning-strip">` appears at the very top of every page when `fallback_warnings` is non-empty:
```
Locale ru: 2 key(s) fell back to English. [▸ show keys]
```
Clicking `show keys` expands a `<details>` block listing every fallen-back key. Strip absent when locale is complete.

### Failure modes (developer-visible)

- `en.toml` missing or malformed → process exits with `SystemExit(1)` and a clear error message ("kardscm/locales/en.toml is the canonical baseline and must be present and valid"). EN is not optional.
- Non-EN TOML missing → that language is simply absent from `LANGUAGES`. `get_language_config()` falls back to EN with a `logger.warning("Unsupported language 'xx'…")` (existing behavior).
- Non-EN TOML malformed → language is registered with the EN baseline plus a single warning entry `file unreadable: TOMLDecodeError` and the rest of the keys derived from EN. The user can still launch the CLI and see the warning strip, but the locale data shown is English.

## Locked design decisions (recap from plan)

| Dimension | Decision |
|---|---|
| Source format | TOML (stdlib `tomllib`) |
| File scope | One file per language = entire `LanguageConfig` |
| Validation | Granular per-key fallback to EN. EN broken/missing → `SystemExit`. Non-EN broken/incomplete → load EN value, append message to `cfg.fallback_warnings`. |
| CLI surface | Non-blocking stderr after `get_language_config()` |
| Web surface | Top-of-page yellow strip in `templates/base.html` via Jinja global `fallback_warnings`. English text. |
| Discovery | Auto-scan `kardscm/locales/*.toml`, skip dotfiles |
| Load timing | Eager at import of `kardscm.locales` |
| Re-export | None. `kardscm.config` does not re-export `LANGUAGE_EN` / `LANGUAGE_RU` / `LANGUAGES`. Single source of truth = `kardscm.locales`. |
| `LanguageConfig` field | New `fallback_warnings: list[str] = field(default_factory=list)` |

### Clarification to the plan

The plan stated: "`kardscm/config.py` keeps `LanguageConfig` dataclass + `get_language_config()`. `kardscm/locales/__init__.py` owns loading + `LANGUAGES` registry."

To avoid a circular import (`kardscm.locales` needs `LanguageConfig`; `kardscm.config.get_language_config()` needs `LANGUAGES`), this spec moves the `LanguageConfig` dataclass to `kardscm/locales/__init__.py`. `kardscm/config.py` becomes thin: `CONFIG_FILE` constant + `get_language_config()`. No lazy imports anywhere. Public usage `from kardscm.locales import LanguageConfig`.

## Module structure (after refactor)

```
kardscm/
├── config.py                   # CONFIG_FILE + get_language_config(). NO data.
├── locales/
│   ├── __init__.py             # LanguageConfig dataclass + LANGUAGES + loader
│   ├── en.toml                 # canonical baseline (must be exhaustive)
│   └── ru.toml                 # russian translations
├── constants.py                # unchanged (DECK_NATION_TO_DB etc.)
└── ...                         # rest unchanged
```

## TOML schema

Top-level scalar / list keys (all required for EN; non-EN falls back per-key):

| TOML key | LanguageConfig field | Type |
|---|---|---|
| `code` | `code` | str |
| `name` | `name` | str |
| `locale_key` | `locale_key` | str |
| `collection_sheet_name` | `collection_sheet_name` | str |
| `export_headers` | `export_headers` | list[str] |
| `deck_headers` | `deck_headers` | list[str] |
| `deck_metadata_labels` | `deck_metadata_labels` | list[str] |

Sections (each maps to a `dict[str, str]` field):

| TOML section | LanguageConfig field |
|---|---|
| `[factions]` | `faction_names` |
| `[types]` | `type_names` |
| `[rarities]` | `rarity_names` |
| `[sets]` | `set_names` |
| `[abilities]` | `ability_names` |
| `[nation_display_names]` | `nation_display_names` |
| `[ui_strings]` | `ui_strings` |
| `[diff_headers]` | `diff_headers` |

Section ↔ field rename mapping is held in a private `_SECTION_TO_FIELD: dict[str, str]` constant inside `kardscm/locales/__init__.py`.

### Example (`kardscm/locales/en.toml` excerpt)

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
# ... etc

[abilities]
alpine = "Alpine"
# ... etc
```

## Loader algorithm

`kardscm/locales/__init__.py`:

```python
from __future__ import annotations

import logging
import sys
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

logger = logging.getLogger(__name__)

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
    """Build EN config. EN is canonical — missing keys raise."""
    missing: list[str] = []
    for key in _TOP_LEVEL_SCALARS + _TOP_LEVEL_LISTS:
        if key not in raw:
            missing.append(key)
    for section in _SECTION_TO_FIELD:
        if section not in raw or not isinstance(raw[section], dict):
            missing.append(f"[{section}]")
    if missing:
        raise ValueError(
            f"en.toml is incomplete; missing: {', '.join(missing)}"
        )

    kwargs: dict = {k: raw[k] for k in _TOP_LEVEL_SCALARS}
    for k in _TOP_LEVEL_LISTS:
        kwargs[k] = list(raw[k])
    for section, field_name in _SECTION_TO_FIELD.items():
        kwargs[field_name] = dict(raw[section])
    return LanguageConfig(fallback_warnings=[], **kwargs)


def _build_with_fallback(
    code: str, raw: dict, en: LanguageConfig
) -> LanguageConfig:
    """Build a non-EN config; fall back to EN per-key with warnings."""
    warnings: list[str] = []

    # `code` always reflects the file stem (caller authority) even if missing
    # in TOML. Not warned — filename is canonical.
    scalars: dict[str, str] = {"code": raw.get("code", code)}

    # Other scalars: missing → EN value + warning.
    for key in _TOP_LEVEL_SCALARS:
        if key == "code":
            continue
        if key in raw:
            scalars[key] = raw[key]
        else:
            scalars[key] = getattr(en, key)
            warnings.append(key)

    # Lists: present → use as-is; missing/wrong type → EN list + warning.
    lists: dict[str, list[str]] = {}
    for key in _TOP_LEVEL_LISTS:
        val = raw.get(key)
        if isinstance(val, list) and all(isinstance(x, str) for x in val):
            lists[key] = list(val)
        else:
            lists[key] = list(getattr(en, key))
            warnings.append(key)

    # Dict sections: per-key fallback.
    sections: dict[str, dict[str, str]] = {}
    for section, field_name in _SECTION_TO_FIELD.items():
        en_section = getattr(en, field_name)
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
    """Discover *.toml in locales_dir and build the registry."""
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
                fallback_warnings=[f"file unreadable: {type(exc).__name__}"]
                + cfg.fallback_warnings,
            )
            continue
        registry[code] = _build_with_fallback(code, raw, en)
    return registry


LANGUAGES: dict[str, LanguageConfig] = _build_registry(_LOCALES_DIR)
LANGUAGE_EN: LanguageConfig = LANGUAGES["en"]
LANGUAGE_RU: LanguageConfig = LANGUAGES["ru"]
```

> **Note:** `LANGUAGE_RU = LANGUAGES["ru"]` is a static module-level binding that assumes `ru.toml` ships with the package. The `tests/test_locales.py::test_ru_loads_complete` test is the canonical check that this assumption holds; a missing `ru.toml` would surface as both a test failure and an `ImportError` at runtime. If we ever drop RU from the shipped package, drop the constant in the same commit.

### `kardscm/config.py` (post-refactor)

```python
"""Language configuration management."""

from __future__ import annotations

import configparser
import logging
from pathlib import Path

from kardscm.locales import LANGUAGE_EN, LANGUAGES, LanguageConfig

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.ini"


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

`LanguageConfig` is re-exported from `kardscm.config` *only because* the old import path `from kardscm.config import LanguageConfig` is heavily used as a type. Data singletons (`LANGUAGE_EN`, `LANGUAGE_RU`, `LANGUAGES`) are NOT re-exported.

## CLI warning surface

A private helper lives in `kardscm/commands.py`:

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

Wiring: each command function (`sync_collection`, `export_collection`, `update_collection`, `import_deck`, `export_deck`) calls `_emit_locale_warnings(cfg)` immediately after `cfg = get_language_config()`. Emitting at command start guarantees the user sees the warning even if the command crashes mid-flight. Typer's `--help` short-circuits before the body runs, so help output is unaffected.

Rejected alternatives: emitting inside `get_language_config()` (harder to test under capsys; fires twice if a command calls the function twice); emitting from a Typer callback (couples warnings to Typer's lifecycle, breaks under direct `python -c "from kardscm.commands import ..."` invocation in tests).

## Web warning surface

`kardscm/web/templates/base.html`:

```jinja
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

`kardscm/web/static/main.css` — append:
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

`kardscm/web/app.py` (`create_app`) — register the global once:
```python
templates.env.globals["fallback_warnings"] = lang_config.fallback_warnings
```

## Bootstrap migration (one-time content)

Both files are written by hand (not generated). Bootstrap = take the current `LANGUAGE_EN` / `LANGUAGE_RU` literals symbol-for-symbol, plus three RU-only fixes.

### `kardscm/locales/en.toml` content

Verbatim mirror of `LANGUAGE_EN` at `kardscm/config.py:36-143`. No semantic changes.

### `kardscm/locales/ru.toml` content

Verbatim mirror of `LANGUAGE_RU` at `kardscm/config.py:146-258`, with these three line-level fixes:

1. `[nation_display_names]` — add the missing entry:
   ```toml
   finland = "Финские"
   ```
   Pattern matches the rest of the section (adjective masculine plural).

2. `[abilities].mobilize` — fix typo:
   ```toml
   mobilize = "Мобилизация"   # was "Моблизация"
   ```

3. `[abilities].salvage` — fix typo:
   ```toml
   salvage = "Утилизация"     # was "Утилизауия"
   ```

These three are the only semantic differences between the source-of-truth literals and the bootstrap output.

## Caller migration (mechanical)

Source files referencing the singletons or registry:

| File | Line(s) | Change |
|---|---|---|
| `kardscm/web/app.py` | 16 | `from kardscm.config import LANGUAGES, LanguageConfig, get_language_config` → `from kardscm.config import LanguageConfig, get_language_config; from kardscm.locales import LANGUAGES` |

Test files (all change is import-line only — symbol references stay identical because we re-export `LanguageConfig` from `kardscm.config` and the singletons keep the same names in `kardscm.locales`):

| File | Lines (imports) | New import |
|---|---|---|
| `tests/test_collection_export.py` | 12 | `from kardscm.locales import LANGUAGE_RU` |
| `tests/test_diff.py` | 7 | `from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU` |
| `tests/test_config.py` | 7 | `from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU` (`get_language_config` stays from `kardscm.config`) |
| `tests/test_translate.py` | 7 | `from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU` |
| `tests/test_exporters.py` | 10 | `from kardscm.locales import LANGUAGE_EN` |
| `tests/test_commands.py` | 24 | `from kardscm.locales import LANGUAGE_EN` |
| `tests/web/test_routes.py` | 11 | `from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU` |

Identity-checks (`is LANGUAGE_EN`) keep working because the registry caches singletons.

## Test plan

### New: `tests/test_locales.py`

Loader is parameterized on `locales_dir`, so tests use `tmp_path` fixtures.

| Test | Behavior |
|---|---|
| `test_en_loads_complete` | `LANGUAGES["en"]` from real package: every section non-empty, `fallback_warnings == []`. |
| `test_ru_loads_complete` | `LANGUAGES["ru"]` from real package: post-bootstrap, `fallback_warnings == []`. Asserts `nation_display_names["finland"] == "Финские"` and ability fixes. |
| `test_partial_language_per_key_fallback` | Build a tmp dir with valid `en.toml` and a `xx.toml` missing `[abilities].mobilize`. Result: `cfg.ability_names["mobilize"] == "Mobilize"` (EN value), `"abilities.mobilize" in cfg.fallback_warnings`. |
| `test_partial_language_section_fallback` | Build a tmp dir with `xx.toml` missing the entire `[abilities]` section. Result: `cfg.ability_names == LANGUAGE_EN.ability_names`, `"[abilities]" in cfg.fallback_warnings`. |
| `test_broken_toml_falls_back` | tmp dir with valid `en.toml` and `xx.toml` containing `not = valid = toml`. Result: `cfg in LANGUAGES`, `cfg.ability_names == LANGUAGE_EN.ability_names`, `cfg.fallback_warnings[0].startswith("file unreadable:")`. |
| `test_en_broken_raises` | tmp dir with malformed `en.toml`. Result: `_build_registry()` calls `sys.exit` (caught via `pytest.raises(SystemExit)`). |
| `test_en_missing_raises` | tmp dir without `en.toml`. Result: `SystemExit`. |
| `test_en_incomplete_raises` | tmp dir with `en.toml` missing `[abilities]`. Result: `SystemExit` with message naming `[abilities]`. |
| `test_registry_built_from_filesystem` | tmp dir with `en.toml` + `de.toml` (minimal: `code = "de"`, `name = "Deutsch"`, `locale_key = "de-DE"`). Result: `LANGUAGES["de"]` exists, has fallback warnings for the omitted sections. |
| `test_registry_skips_dotfiles` | tmp dir with `en.toml` and `.draft.toml`. Result: `".draft" not in LANGUAGES`. |

### Modified: `tests/test_config.py`

Single change: imports of `LANGUAGE_EN` / `LANGUAGE_RU` move from `kardscm.config` to `kardscm.locales`. Test bodies unchanged (identity-checks via `is` still work because registry caches singletons).

### Modified: `tests/web/test_routes.py`

Two changes:
1. Import line: `from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU`.
2. New test `test_warning_strip_renders_when_warnings_present`:
   ```python
   def test_warning_strip_renders_when_warnings_present(...):
       # Use a fixture that produces a LanguageConfig with non-empty warnings.
       cfg = replace(LANGUAGE_EN, fallback_warnings=["abilities.mobilize"])
       app = create_app(db_path, lang_config=cfg)
       r = client.get("/")
       assert 'class="locale-warning-strip"' in r.text
       assert "abilities.mobilize" in r.text
   ```
   Counterpart `test_warning_strip_absent_when_no_warnings` confirms strip is missing for clean `LANGUAGE_EN`.

### Modified: all other test files

Single-line import path change. No body changes.

## Documentation updates

### `config.ini`
```diff
 [settings]
-# Supported languages: en, ru
-# Changing language requires deleting collection.db and re-running sync
+# Supported languages: see kardscm/locales/*.toml
 language = ru
```

### `README.md`
- Replace lines 56-59 ("Supported languages…", "Changing the language requires deleting…", and the CONTRIBUTING.md pointer) with:
  > Supported languages: every `kardscm/locales/<code>.toml` ships as a language. To add one, drop a TOML file into that directory and set `language = <code>` in `config.ini`. Missing keys fall back to English with a runtime warning.
- Drop the line "Changing the language requires deleting `collection.db` and re-running sync" — the lookup is `locale_key`-based, no DB reset is needed.

### `CONTRIBUTING.md` — section "Adding a New Language"

Replace the entire section (`CONTRIBUTING.md:88+`):

```markdown
### Adding a New Language

1. Create `kardscm/locales/<code>.toml` (e.g. `de.toml` for German).
2. Use `kardscm/locales/en.toml` as the schema reference. Top-level keys: `code`, `name`, `locale_key`, `collection_sheet_name`, `export_headers`, `deck_headers`, `deck_metadata_labels`. Sections: `[factions]`, `[types]`, `[rarities]`, `[sets]`, `[abilities]`, `[nation_display_names]`, `[ui_strings]`, `[diff_headers]`.
3. Any key you omit will fall back to the English value, and the loader records a warning that surfaces on stderr (CLI) and as a yellow strip (web UI). Partially-translated locales are usable.
4. Set `language = <code>` in `config.ini`.

No tests need to be added for new languages — the loader is covered by `tests/test_locales.py`.
```

### `CHANGELOG.md` — Unreleased / 0.5.1

```markdown
## [0.5.1] — Unreleased

### Changed
- Refactored: per-language data extracted from Python literals to TOML files in `kardscm/locales/`. Adding a new language no longer requires editing Python source.
- `LanguageConfig` dataclass moved from `kardscm/config.py` to `kardscm/locales/__init__.py`. `from kardscm.config import LanguageConfig` continues to work via re-export.

### Fixed
- RU `nation_display_names`: added missing `finland` entry ("Финские").
- RU `ability_names.mobilize`: typo "Моблизация" → "Мобилизация".
- RU `ability_names.salvage`: typo "Утилизауия" → "Утилизация".

### Added
- Non-blocking locale fallback diagnostics: missing/malformed keys load English values and surface a stderr line on CLI and a top-of-page yellow strip in the web UI.
```

## Verification

### Lint / type / test
```bash
make check
```
Must be green. Coverage ≥94%.

### Targeted runs
```bash
uv run pytest tests/test_locales.py -v
uv run pytest tests/test_config.py -v
uv run pytest tests/web/test_routes.py -v
```

### Smoke (RU happy path)
```bash
uv run kardscm export --format xlsx --file /tmp/check.xlsx
# header "Нация" present; ability column shows "Мобилизация" (not "Моблизация")
# stderr: empty (no fallback warnings)

uv run kardscm web --lang ru
# open localhost — no yellow strip
```

### Smoke (fallback path)
```bash
# Temporarily comment out [abilities].mobilize in kardscm/locales/ru.toml.
uv run kardscm export --format xlsx --file /tmp/check.xlsx
# stderr: Locale 'ru': 1 key(s) fell back to English (abilities.mobilize).

uv run kardscm web --lang ru
# yellow strip with "abilities.mobilize" in the details list
# Restore the line.
```

## Risks / open questions

1. **`LanguageConfig` move** — re-exporting from `kardscm.config` softens this, but downstream `from kardscm.config import LanguageConfig` keeps working. If we ever want to drop the re-export later, that's a separate breaking change for `0.6.0`.
2. **Eager load at import time** — package import becomes ~1ms slower (TOML parse). Negligible.
3. **No locale validation tool** — contributors who hand-edit a TOML file with a typo only learn from the runtime warning. Acceptable for a 2-locale project; revisit if we cross 5+ locales.
4. **`config.ini` `language` key not in TOML registry** — covered by existing `get_language_config()` "Unsupported language" warning. No change.
