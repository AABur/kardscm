# Card Collection

## Environment
- Python managed via `uv` (not pip directly)
- Package name: `kards-manager` (version 0.2.0)
- Entry points: `python -m kards` or `kards` (console script)
- Tests: `uv run pytest` or `make test`

## Usage Commands
- Sync: `uv run python -m kards --sync`
- Export: `uv run python -m kards --export --format xlsx --file cards.xlsx`
- Update: `uv run python -m kards --update --file cards.xlsx`
- Import deck: `uv run python -m kards --import-deck --file deck.txt`
- Export deck: `uv run python -m kards --export-deck --file deck.xlsx`
- Short form: `uv run kards --sync`

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
├── cli.py              # CLI implementation (sync/export/update/deck)
├── constants.py        # All constants (URLs, mappings, defaults)
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
- **Scraping**: `kards.scraping` collects GraphQL responses using Playwright
  - `browser.py`: Page automation and API data collection
  - `localization.py`: Translation loading and text sanitization
  - `scraper.py`: Parses API responses into card dictionaries
- **Storage**: `kards.storage` manages SQLite database
  - CRUD operations with upsert logic
  - Quantity updates by nation/name
  - Deck storage (schema, insert/fetch for decks and deck cards)
- **Export**: `kards.export` writes formatted files
  - Excel (XLSX) with styling and filters
  - CSV with UTF-8 BOM for Windows Excel
  - JSON with metadata
  - Deck export to XLSX sheet and JSON
- **Import**: `kards.importing` parses deck files
  - TXT deck file parser
- **CLI**: `kards.cli` provides command-line interface
  - Console script: `kards`
  - Module entry: `python -m kards`
  - Deck commands: `--import-deck`, `--export-deck`

## Code Patterns
- Use module-level constants from `kards.constants` (avoid duplication)
- No emojis in log messages
- Imports at top of file (not inline in exception handlers)
- Import from package: `from kards.constants import ...`
- Type hints using TypedDict from `kards.models`
