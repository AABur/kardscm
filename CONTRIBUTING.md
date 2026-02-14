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

The CLI is built with [Typer](https://typer.tiangolo.com/). Entry points: `kards` (console script) or `python -m kards`.

| Command | Description |
|---------|-------------|
| `kards sync` | Fetch cards from the website and update `collection.db` |
| `kards export --format <csv\|json\|xlsx> --file <path>` | Export collection from SQLite |
| `kards update --file <path>` | Update card quantities from XLSX file |
| `kards deck import --file <path>` | Import deck from TXT file into database |
| `kards deck export --format xlsx --file <path>` | Export deck to XLSX sheet (interactive selection) |
| `kards deck export --format json --file <path>` | Export deck to JSON (interactive selection) |

## Project Structure

```
kards/
├── __init__.py         # Package initialization
├── __main__.py         # Entry point (python -m kards)
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

All language-specific data lives in `kards/config.py` as `LanguageConfig` instances.

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

Language-agnostic constants (KNOWN_MAPPINGS, EXPORT_FIELD_NAMES, DECK_CARD_PATTERN, etc.) remain in `kards/constants.py`.

### Adding a New Language

To add support for a new language (e.g. German):

1. Open `kards/config.py`
2. Create a new `LanguageConfig` instance:

```python
LANGUAGE_DE = LanguageConfig(
    code="de",
    name="German",
    keys=("de", "de-DE"),
    lang_index=2,  # find the correct index in the website JS translation arrays
    collection_url=f"{BASE_URL}/de/decks/collection",
    export_headers=["Nation", "Name", "Typ", ...],
    faction_names={"Soviet": "Sowjetunion", ...},
    deck_nation_to_db={"soviet": "Sowjetunion", ...},
    nation_display_names={"soviet": "Sowjetisch", ...},
    deck_headers=["Karte", "Typ", "Anzahl", ...],
    deck_metadata_labels=["Name", "Hauptmacht", ...],
    collection_sheet_name="Sammlung",
)
```

3. Register it in the `LANGUAGES` dictionary:

```python
LANGUAGES: dict[str, LanguageConfig] = {
    "en": LANGUAGE_EN,
    "ru": LANGUAGE_RU,
    "de": LANGUAGE_DE,
}
```

4. To find `lang_index`: inspect the JS translation file loaded from the KARDS website and locate the position of translations for your language in the arrays.

No other code changes are needed.

## Makefile Targets

```bash
make help    # see all available targets
```
