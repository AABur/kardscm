# Contributing

## Development Setup

```bash
make sync-dev
```

This installs all dependencies including dev tools (ruff, mypy, pytest) and Playwright's Chromium.

## Code Quality

```bash
make format       # format code with ruff
make lint         # run ruff linter
make typecheck    # run mypy type checker
make test         # run tests with pytest + coverage
make check        # all of the above
```

## CLI Reference

The CLI is built with [Typer](https://typer.tiangolo.com/). Entry points: `kardscm` (console script) or `python -m kardscm`.

| Command | Description |
|---------|-------------|
| `kardscm sync` | Fetch cards from the website and update `collection.db` |
| `kardscm export --format <csv\|json\|xlsx> --file <path>` | Export collection from SQLite |
| `kardscm update --file <path>` | Update card quantities from XLSX file |
| `kardscm deck import --file <path>` | Import deck from TXT file into database |
| `kardscm deck export --format xlsx --file <path>` | Export deck to XLSX sheet (interactive selection) |
| `kardscm deck export --format json --file <path>` | Export deck to JSON (interactive selection) |

## Project Structure

```
kardscm/
├── __init__.py         # Package initialization
├── __main__.py         # Entry point (python -m kardscm)
├── config.py           # Language configuration (LanguageConfig dataclass)
├── cli.py              # Typer CLI declarations
├── commands.py         # Business logic (sync, export, import, deck)
├── constants.py        # Language-agnostic constants (URLs, mappings)
├── models.py           # TypedDict definitions
├── helpers.py          # Utility functions
├── scraping/           # Scraping functionality
│   ├── scraper.py      # API data parsing
│   ├── localization.py # Translation loading and text processing
│   └── browser.py      # Playwright automation
├── storage/            # Database layer
│   └── database.py     # SQLite operations (cards + decks)
├── export/             # Export functionality
│   └── exporters.py    # CSV/XLSX/JSON exporters + deck export
└── importing/          # Import functionality
    └── parser.py       # Deck TXT file parser
tests/                  # pytest suites
config.ini.example      # Language configuration template
```

## Architecture

- **config.py** — `LanguageConfig` frozen dataclass holding all language-specific data (headers, nation names, URLs, translation indices). Registry of language configs (`LANGUAGE_EN`, `LANGUAGE_RU`) and `get_language_config()` reader for `config.ini`
- **scraping/** — Playwright browser automation collects GraphQL responses from the KARDS website; parses API data into card dictionaries using `LanguageConfig` for localization
- **storage/** — SQLite CRUD layer with upsert logic for cards and deck storage
- **export/** — XLSX (with styling and filters), CSV (UTF-8 BOM), and JSON exporters; deck export as XLSX sheet or JSON. All headers and labels come from `LanguageConfig`
- **importing/** — parser for KARDS client deck TXT format
- **cli.py** — Typer-based CLI with commands: `sync`, `export`, `update`, `deck import`, `deck export`
- **commands.py** — business logic; loads `LanguageConfig` at the start of each command

## Language System

All language-specific data lives in `kardscm/config.py` as `LanguageConfig` instances.

Each `LanguageConfig` contains:
- `code` / `name` — language identifier and display name
- `keys` — API response keys to prioritize (e.g. `("ru", "ru-RU")`)
- `lang_index` — position in the website's JS translation arrays
- `collection_url` — URL for the collection page
- `export_headers` — column headers for XLSX/CSV exports
- `faction_names` — display names for nations
- `deck_nation_to_db` — mapping from deck file nation keys to DB names
- `nation_display_names` — adjective forms for deck export sections
- `deck_headers` / `deck_metadata_labels` — deck export labels
- `collection_sheet_name` — XLSX worksheet title

Language-agnostic constants (KNOWN_MAPPINGS, EXPORT_FIELD_NAMES, DECK_CARD_PATTERN, etc.) remain in `kardscm/constants.py`.

### Adding a New Language

1. Create `kardscm/locales/<code>.toml` (e.g. `de.toml` for German).
2. Use `kardscm/locales/en.toml` as the schema reference. Top-level keys: `code`, `name`, `locale_key`, `collection_sheet_name`, `export_headers`, `deck_headers`, `deck_metadata_labels`. Sections: `[factions]`, `[types]`, `[rarities]`, `[sets]`, `[abilities]`, `[nation_display_names]`, `[ui_strings]`, `[diff_headers]`.
3. Any key you omit falls back to the English value, and the loader records a warning that surfaces on CLI (stderr) and web UI (yellow strip at the page top). Partially-translated locales are valid.
4. Set `language = <code>` in `config.ini` to activate the locale.

No code changes needed. No tests required for new locale files — the loader is already covered by `tests/test_locales.py`.

## Makefile Targets

```bash
make help    # see all available targets
```
