# Card Collection

## Environment
- Python managed via `uv` (not pip directly)
- Sync: `uv run python collection.py --sync`
- Export: `uv run python collection.py --export --format xlsx --file cards.xlsx`
- Tests: `uv run pytest` or `make test`

## Useful Commands
- `make help` — list available commands
- `make lint` — check code (ruff, mypy)
- `make format` — format code

## Project Structure
- `collection.py` — CLI entrypoint (sync/export)
- `scrape.py` — scraping and translation helpers
- `storage.py` — SQLite storage helpers
- `exporters.py` — export helpers
- `tests/` — pytest tests

## Architecture
- `scrape.py` collects GraphQL responses from the collection page
- `storage.py` stores cards in SQLite with upsert
- `exporters.py` writes CSV/XLSX/JSON with Russian headers

## Code Patterns
- Use module-level constants for shared data (avoid duplication)
- No emojis in log messages
- Imports at top of file (not inline in exception handlers)
