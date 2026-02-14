# KARDS Card Collection

Sync the official KARDS card catalog (Russian) into SQLite and export it to XLSX, CSV, or JSON.

## Features

- Russian-only scrape with English fallback when Russian text is missing.
- SQLite storage with upsert on sync (`collection.db`).
- Export to `xlsx`, `csv`, `json` with Russian headers.
- Stable, reproducible exports.

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
uv run python collection.py --sync
```

### 3. Export from SQLite

```bash
# XLSX
uv run python collection.py --export --format xlsx --file kards_cards_ru.xlsx

# CSV
uv run python collection.py --export --format csv --file kards_cards_ru.csv

# JSON
uv run python collection.py --export --format json --file kards_cards_ru.json
```

## CLI

- `--sync` — fetch cards from the website and update `collection.db`.
- `--export --format <csv|json|xlsx> --file <path>` — export data from SQLite.

## Output

- Database: `collection.db` (created on first sync)
- Exports: file specified via `--file`

Note: `Quantity` and `Abilities` are kept empty for now.

## Project Structure

```
collection.py   - CLI entrypoint (sync/export)
scrape.py       - scraping and translation helpers
storage.py      - SQLite schema and queries
exporters.py    - export helpers (xlsx/csv/json)
tests/          - pytest suites
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
```

## Notes

- Data is obtained from the official KARDS website.
- The scrape targets the Russian collection page and falls back to English when needed.
