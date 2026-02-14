# Card Collection

## Environment
- Python managed via `uv` (not pip directly)
- Package name: `kardscm` (version 0.2.0)
- Entry points: `python -m kardscm` or `kardscm` (console script)
- Tests: `uv run pytest` or `make test`

## Usage Commands
- Sync: `uv run kardscm sync`
- Export: `uv run kardscm export --format xlsx --file cards.xlsx`
- Update: `uv run kardscm update --file cards.xlsx`
- Import deck: `uv run kardscm deck import --file deck.txt`
- Export deck: `uv run kardscm deck export --format xlsx --file deck.xlsx`
- Short form: `uv run python -m kardscm sync`

## Useful Commands
- `make help` — list available commands
- `make lint` — check code (ruff, mypy)
- `make format` — format code
- `make run` — run the application

## Gotchas
- `uv sync` alone skips dev deps; use `uv sync --dev` before running tests

## Project Structure
```
kardscm/
├── __init__.py         # Package initialization (__version__)
├── __main__.py         # Entry point for python -m kardscm
├── cli.py              # Typer CLI declarations
├── commands.py         # Business logic (sync, export, import, deck)
├── config.py           # Language configuration (LanguageConfig dataclass)
├── constants.py        # Language-agnostic constants (URLs, mappings, defaults)
├── models.py           # TypedDict definitions (CardDict)
├── helpers.py          # Utility functions (parse_int, to_text)
├── scraping/           # Scraping functionality
│   ├── __init__.py     # Exports scrape_cards
│   ├── scraper.py      # Main orchestration (parse_api_data, build_card)
│   ├── localization.py # Translation and text processing
│   └── browser.py      # Playwright automation
├── storage/            # Database layer
│   ├── __init__.py     # Exports all database functions
│   └── database.py     # SQLite operations
├── export/             # Export functionality
│   ├── __init__.py     # Exports export functions
│   └── exporters.py    # CSV/XLSX/JSON exporters
└── importing/          # Import functionality
    ├── __init__.py     # Exports parse_deck_file
    └── parser.py       # Deck TXT file parser
tests/                  # pytest tests
```

## Architecture
- **Config**: `kardscm.config` — `LanguageConfig` frozen dataclass with all language-specific data
  - Registry: `LANGUAGES` dict (`"en"` → `LANGUAGE_EN`, `"ru"` → `LANGUAGE_RU`)
  - `get_language_config()` reads `config.ini` and returns the active `LanguageConfig`
  - Commands call `get_language_config()` internally — no language threading through CLI
- **Scraping**: `kardscm.scraping` collects GraphQL responses using Playwright
  - `browser.py`: Page automation and API data collection
  - `localization.py`: Translation loading and text sanitization (takes `LanguageConfig`)
  - `scraper.py`: Parses API responses into card dictionaries (takes `LanguageConfig`)
- **Storage**: `kardscm.storage` manages SQLite database
  - CRUD operations with upsert logic
  - Quantity updates by nation/name
  - Deck storage (schema, insert/fetch for decks and deck cards)
- **Export**: `kardscm.export` writes formatted files
  - Excel (XLSX) with styling and filters
  - CSV with UTF-8 BOM for Windows Excel
  - JSON with metadata
  - Deck export to XLSX sheet and JSON
  - All headers and labels come from `LanguageConfig`
- **Import**: `kardscm.importing` parses deck files
  - TXT deck file parser
- **CLI**: `kardscm.cli` provides Typer-based command-line interface
  - Console script: `kardscm`
  - Module entry: `python -m kardscm`
  - Commands: `sync`, `export`, `update`, `deck import`, `deck export`
- **Commands**: `kardscm.commands` contains business logic
  - Extracted from cli.py for separation of concerns
  - Functions: `sync_collection`, `export_collection`, `update_collection`, `import_deck`, `export_deck`
  - Each command loads `LanguageConfig` via `get_language_config()`

## Code Patterns
- Language-specific data from `kardscm.config` (`LanguageConfig`), language-agnostic constants from `kardscm.constants`
- No emojis in log messages
- Imports at top of file (not inline in exception handlers)
- Import from package: `from kardscm.config import ...`, `from kardscm.constants import ...`
- Type hints using TypedDict from `kardscm.models`
