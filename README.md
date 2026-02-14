# KARDS Manager

Manager for [KARDS](https://www.kards.com/) card game player collection and decks. Syncs the official card catalog (Russian) into SQLite and exports to XLSX, CSV, or JSON. Supports deck import from the game client and deck export.

## Features

- Russian-only scrape with English fallback when Russian text is missing.
- SQLite storage with upsert on sync (`collection.db`).
- Export to `xlsx`, `csv`, `json` with Russian headers.
- Deck import from KARDS client TXT export format.
- Deck export to XLSX (as a sheet in existing file) or JSON.
- Interactive deck selection for export.

## Requirements

- Python 3.12+
- uv

## Quick Start

### 1. Install dependencies

```bash
uv sync
uv run python -m playwright install chromium
```

### 2. Sync catalog into SQLite

```bash
uv run kards sync
```

### 3. Export collection

```bash
# XLSX
uv run kards export --format xlsx --file kards_cards_ru.xlsx

# CSV
uv run kards export --format csv --file kards_cards_ru.csv

# JSON
uv run kards export --format json --file kards_cards_ru.json
```

### 4. Update quantities from XLSX

```bash
uv run kards update --file kards_cards_ru.xlsx
```

### 5. Import a deck

```bash
uv run kards deck import --file deck.txt
```

### 6. Export a deck

```bash
# Add deck sheet to existing XLSX
uv run kards deck export --format xlsx --file kards_cards_ru.xlsx

# Export deck to JSON
uv run kards deck export --format json --file deck.json
```

## CLI

| Command | Description |
|---------|-------------|
| `kards sync` | Fetch cards from the website and update `collection.db` |
| `kards export --format <csv\|json\|xlsx> --file <path>` | Export collection from SQLite |
| `kards update --file <path>` | Update card quantities from XLSX file |
| `kards deck import --file <path>` | Import deck from TXT file into database |
| `kards deck export --format xlsx --file <path>` | Export deck to XLSX sheet (interactive selection) |
| `kards deck export --format json --file <path>` | Export deck to JSON (interactive selection) |

## Deck TXT Format

The input format matches the KARDS client deck export:

```
Deck Name
Major power: soviet
Ally: usa
HQ: СТАЛИНГРАД

soviet:
1x (1K) 16-й СТРЕЛКОВЫЙ ПОЛК
2x (3K) ОТ НАРОДА

usa:
3x (4K) M4 SHERMAN

%%45|7E8B...
```

## Output

- Database: `collection.db` (created on first sync)
- Exports: file specified via `--file`

## Project Structure

```
kards/
├── __init__.py         # Package initialization
├── __main__.py         # Entry point (python -m kards)
├── cli.py              # Typer CLI declarations
├── commands.py         # Business logic (sync, export, import, deck)
├── constants.py        # Constants (URLs, mappings, defaults)
├── models.py           # TypedDict definitions
├── helpers.py          # Utility functions
├── scraping/           # Scraping functionality
│   ├── scraper.py      # API data parsing
│   ├── localization.py # Translation and text processing
│   └── browser.py      # Playwright automation
├── storage/            # Database layer
│   └── database.py     # SQLite operations (cards + decks)
├── export/             # Export functionality
│   └── exporters.py    # CSV/XLSX/JSON exporters + deck export
└── importing/          # Import functionality
    └── parser.py       # Deck TXT file parser
tests/                  # pytest suites
```

## Development

```bash
# Install dev tools
uv sync --all-extras

# Code quality
make format
make lint
make typecheck
make test

# Run targets
make run-sync
make run-export-xlsx
make run-import-deck FILE=deck.txt
make run-export-deck-xlsx
make run-export-deck-json
```

## Notes

- Data is obtained from the official KARDS website.
- The scrape targets the Russian collection page and falls back to English when needed.
- Deck import requires a synced collection (cards must exist in the database).
