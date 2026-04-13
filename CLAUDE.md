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
- Add deck(s): `uv run kardscm deck add deck.txt` or `uv run kardscm deck add *.txt -u`
- Replace deck: `uv run kardscm deck add deck.txt -r`
- Export deck: `uv run kardscm deck export --format xlsx --file deck.xlsx`
- Analyze deck: `uv run kardscm deck analyze` or `uv run kardscm deck analyze -d detailed`
- Record matches: `uv run kardscm match add`
- Short form: `uv run python -m kardscm sync`

## Useful Commands
- `make help` — list available commands
- `make check` — full check (ruff format, ruff check, mypy, pytest)
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
├── commands.py         # Business logic (sync, export, import, deck, match, analyze)
├── config.py           # Language + advisor configuration (LanguageConfig, AdvisorConfig)
├── constants.py        # Language-agnostic constants (URLs, defaults)
├── models.py           # TypedDict definitions (CardDict, ProbeData, MatchRecord, DeckStats)
├── helpers.py          # Utility functions (parse_int, to_text, sanitize_text)
├── scraping/           # Scraping functionality
│   ├── __init__.py     # Exports scrape_cards (sync orchestration)
│   ├── probe.py        # Playwright one-shot GraphQL interceptor
│   ├── fetcher.py      # httpx GraphQL paginator
│   └── normalizer.py   # API node → CardDict transformer
├── storage/            # Database layer
│   ├── __init__.py     # Exports all database functions
│   └── database.py     # SQLite operations (new schema with API field names)
├── export/             # Export functionality
│   ├── __init__.py     # Exports export functions
│   └── exporters.py    # CSV/XLSX/JSON exporters with translate_card_for_export
├── importing/          # Import functionality
│   ├── __init__.py     # Exports parse_deck_file
│   └── parser.py       # Deck TXT file parser
└── advisor/            # LLM advisor for deck analysis
    ├── __init__.py     # Exports build_analysis_context, get_llm_response
    ├── llm.py          # Provider dispatch (openai/anthropic/google)
    ├── context.py      # Context assembly for analysis prompts
    └── prompts.py      # System prompt template and depth modifiers
tests/                  # pytest tests
```

## Architecture
- **Config**: `kardscm.config` — `LanguageConfig` frozen dataclass with all language-specific data
  - Registry: `LANGUAGES` dict (`"en"` → `LANGUAGE_EN`, `"ru"` → `LANGUAGE_RU`)
  - `get_language_config()` reads `config.ini` and returns the active `LanguageConfig`
  - `locale_key` field (`"en-EN"` / `"ru-RU"`) for extracting from JSON title/text dicts
  - Static translation mappings: `faction_names`, `type_names`, `rarity_names`, `set_names`, `ability_names`
  - `deck_nation_to_db` maps deck nation keys to API faction names (e.g. `"soviet"` → `"Soviet"`)
  - Commands call `get_language_config()` internally — no language threading through CLI
  - `AdvisorConfig` frozen dataclass: `provider`, `model`, `depth`
  - `get_advisor_config()` reads `[advisor]` section from config.ini
- **Scraping**: `kardscm.scraping` fetches cards via direct GraphQL (synchronous)
  - `probe.py`: One-shot Playwright intercept — opens browser, captures first GraphQL POST
  - `fetcher.py`: httpx paginator — uses probe data to fetch all cards via offset/cursor pagination
  - `normalizer.py`: Transforms raw API nodes into CardDict (title/text/attributes as JSON strings)
  - `scrape_cards()`: Orchestrates probe → fetch → normalize pipeline
- **Storage**: `kardscm.storage` manages SQLite database
  - DB columns use API field names (camelCase): `cardId`, `faction`, `title`, `kredits`, etc.
  - `title` and `text` stored as JSON strings with locale keys
  - `attributes` stored as JSON array string
  - `quantity` is user-managed, preserved on upsert
  - Schema version check: detects old `nation` column → error with migration instructions
  - Card lookup by faction + `json_extract(title, ...)` for localized name matching
  - `matches` table with FK CASCADE to decks for match tracking
  - `insert_match`, `fetch_matches_by_deck`, `compute_deck_stats` functions
- **Export**: `kardscm.export` writes formatted files
  - `translate_card_for_export()`: Converts raw DB card to localized export dict at export time
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
  - Commands: `sync`, `export`, `update`, `deck import/add/delete/export/analyze`, `match add`
  - `sync` is synchronous (no asyncio)
- **Commands**: `kardscm.commands` contains business logic
  - Extracted from cli.py for separation of concerns
  - Functions: `sync_collection`, `export_collection`, `update_collection`, `import_deck`, `add_deck`, `export_deck`, `remove_deck`, `add_match`, `analyze_deck`
  - `export_collection` fetches raw DB cards, translates each via `translate_card_for_export`, then exports
  - `update_collection` reverse-maps localized faction names to API names for DB lookup
  - Each command loads `LanguageConfig` via `get_language_config()`
  - `add_deck` supports `--replace` flag to overwrite existing decks
  - `analyze_deck` assembles context from deck/cards/stats/rules and calls LLM
- **Advisor**: `kardscm.advisor` provides LLM-powered deck analysis
  - `llm.py`: Provider dispatch — thin wrappers for OpenAI, Anthropic, Google
  - `context.py`: Assembles user prompt from deck data, cards, stats, rules
  - `prompts.py`: System prompt template and depth modifiers (concise/standard/detailed)
  - API keys loaded from `.env` via python-dotenv
## Code Patterns
- `add_deck` raises `RuntimeError` (not `SystemExit`) — allows CLI batch loop to collect errors; `import_deck` raises `SystemExit` (fail-fast)
- English originals stored in DB — translation only at export time via static mappings
- Language-specific data from `kardscm.config` (`LanguageConfig`), language-agnostic constants from `kardscm.constants`
- No emojis in log messages
- Imports at top of file (not inline in exception handlers)
- Import from package: `from kardscm.config import ...`, `from kardscm.constants import ...`
- Type hints using TypedDict from `kardscm.models`
- Card abilities translated via `LanguageConfig.ability_names`; unknown/internal attributes (e.g. `BecomesVeteran:*`) are filtered out
