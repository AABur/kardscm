# Card Collection

## Environment
- Python managed via `uv` (not pip directly)
- Package name: `kards-manager` (version 0.2.0)
- Entry points: `python -m kards` or `kards` (console script)
- Tests: `uv run pytest` or `make test`

## Usage Commands
- Sync: `uv run kards sync`
- Export: `uv run kards export --format xlsx --file cards.xlsx`
- Update: `uv run kards update --file cards.xlsx`
- Import deck: `uv run kards deck import --file deck.txt`
- Export deck: `uv run kards deck export --format xlsx --file deck.xlsx`
- Short form: `uv run python -m kards sync`

## Useful Commands
- `make help` — list available commands
- `make lint` — check code (ruff, mypy)
- `make format` — format code
- `make run` — run the application

## Project Structure
```
kards/
├── __init__.py         # Package initialization (__version__)
├── __main__.py         # Entry point for python -m kards
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
- **Config**: `kards.config` — `LanguageConfig` frozen dataclass with all language-specific data
  - Registry: `LANGUAGES` dict (`"en"` → `LANGUAGE_EN`, `"ru"` → `LANGUAGE_RU`)
  - `get_language_config()` reads `config.ini` and returns the active `LanguageConfig`
  - Commands call `get_language_config()` internally — no language threading through CLI
- **Scraping**: `kards.scraping` collects GraphQL responses using Playwright
  - `browser.py`: Page automation and API data collection
  - `localization.py`: Translation loading and text sanitization (takes `LanguageConfig`)
  - `scraper.py`: Parses API responses into card dictionaries (takes `LanguageConfig`)
- **Storage**: `kards.storage` manages SQLite database
  - CRUD operations with upsert logic
  - Quantity updates by nation/name
  - Deck storage (schema, insert/fetch for decks and deck cards)
- **Export**: `kards.export` writes formatted files
  - Excel (XLSX) with styling and filters
  - CSV with UTF-8 BOM for Windows Excel
  - JSON with metadata
  - Deck export to XLSX sheet and JSON
  - All headers and labels come from `LanguageConfig`
- **Import**: `kards.importing` parses deck files
  - TXT deck file parser
- **CLI**: `kards.cli` provides Typer-based command-line interface
  - Console script: `kards`
  - Module entry: `python -m kards`
  - Commands: `sync`, `export`, `update`, `deck import`, `deck export`
- **Commands**: `kards.commands` contains business logic
  - Extracted from cli.py for separation of concerns
  - Functions: `sync_collection`, `export_collection`, `update_collection`, `import_deck`, `export_deck`
  - Each command loads `LanguageConfig` via `get_language_config()`

## Code Patterns
- Language-specific data from `kards.config` (`LanguageConfig`), language-agnostic constants from `kards.constants`
- No emojis in log messages
- Imports at top of file (not inline in exception handlers)
- Import from package: `from kards.config import ...`, `from kards.constants import ...`
- Type hints using TypedDict from `kards.models`
