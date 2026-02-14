# MEMORY.md - KARDS Manager

> Multi-agent development memory for AI assistants (Claude Code, Codex, Cursor, Gemini CLI, etc.)

---

## 1. PROJECT OVERVIEW

**What it does:** Syncs card data from the KARDS website (Russian) into SQLite and exports to XLSX, CSV, or JSON. Imports and exports player decks.

**Package:** `kards-manager` v0.2.0

**Tech stack:**
- Python 3.12
- playwright (browser automation for card scraping)
- httpx (async HTTP for loading translations from JS)
- openpyxl (Excel read/write)
- sqlite3 (local storage)

**Entry point:** `kards.cli:run` (console script `kards` or `python -m kards`)

**Language scope:** Russian only with English fallback for missing text.

**Export formats:** xlsx, csv, json (collection); xlsx sheet, json (decks)

---

## 2. ARCHITECTURE

```
CLI (kards.cli — Typer)
  │
  ├── kards.commands         — business logic (sync, export, update, deck import/export)
  │
  ├── kards.scraping
  │     ├── browser.py      — Playwright: open page, intercept GraphQL
  │     ├── localization.py  — load_translations(), translate_value(), sanitize_text()
  │     └── scraper.py       — parse_api_data(), build_card()
  │
  ├── kards.storage
  │     └── database.py      — SQLite: cards, metadata, decks, deck_cards
  │
  ├── kards.export
  │     └── exporters.py     — XLSX/CSV/JSON collection + deck sheet/JSON
  │
  └── kards.importing
        └── parser.py        — parse_deck_file() from TXT
```

**Key public functions:**
- `scraping`: `scrape_cards()` — full scrape pipeline (browser → translations → parse)
- `storage`: `upsert_cards()`, `fetch_cards()`, `insert_deck()`, `insert_deck_cards()`, `fetch_all_decks()`, `fetch_deck_cards()`, `find_card_id_by_nation_name()`, `find_deck_by_name()`
- `export`: `export_to_xlsx()`, `export_to_csv()`, `export_to_json()`, `add_deck_sheet()`, `export_deck_to_json()`
- `importing`: `parse_deck_file()`

**Shared modules:**
- `constants.py` — URLs, mappings, export headers, deck constants
- `models.py` — TypedDict definitions (`CardDict`, `ParsedDeck`, etc.)
- `helpers.py` — `parse_int()`, `to_text()`

---

## 3. DATA FLOW

### Collection sync
```
1. kards sync
2. scraping.browser: Playwright opens collection page, intercepts GraphQL
3. scraping.localization: load_translations() fetches JS, builds translation dict
4. scraping.scraper: parse_api_data() + translate → list of card dicts
5. storage: upsert_cards() into SQLite, set_metadata("last_sync")
```

### Collection export
```
1. kards export --format <fmt> --file <path>
2. storage: fetch_cards() from SQLite
3. export: export_to_xlsx/csv/json()
```

### Deck import
```
1. kards deck import --file deck.txt
2. importing.parser: parse_deck_file() → ParsedDeck (name, metadata, cards)
3. find_deck_by_name() checks for duplicates
4. For each card: DECK_NATION_TO_DB maps nation → DB name, find_card_id_by_nation_name()
5. storage: insert_deck() + insert_deck_cards()
```

### Deck export
```
1. kards deck export --format <fmt> --file <path>
2. storage: fetch_all_decks() → interactive selection → fetch_deck_cards()
3. export: add_deck_sheet() to XLSX or export_deck_to_json()
```

---

## 4. CRITICAL GOTCHAS

### Fragile Points (will break when website changes)

| Issue | Location | Risk | Workaround |
|-------|----------|------|------------|
| Hardcoded JS chunk ID "2840-" | localization.py | **HIGH** | Falls back to static mappings if JS not found |
| Button text detection "LOAD MORE" | browser.py | **MEDIUM** | Stops after max clicks |
| GraphQL response structure | scraper.py | **MEDIUM** | Logs warning, skips malformed cards |

### Translation Loading Failure Modes

1. **JS URL not found** -> Uses static mappings from KNOWN_MAPPINGS
2. **HTTP timeout** -> Uses static mappings
3. **Translation ID not in JS** -> Returns original value unchanged

### Deck Import Preconditions

- Cards **must exist** in `collection.db` before deck import (run `kards sync` first)
- `DECK_NATION_TO_DB` maps deck nation codes (`soviet`, `usa`, etc.) to DB nation names (`Советский Союз`, `США`, etc.)
- If any card is not found in the collection, import fails with a list of missing cards
- Duplicate deck names are rejected (checked via `find_deck_by_name()`)

---

## 5. KNOWN ISSUES & TECHNICAL DEBT

### Bugs to Fix

- [ ] **Abilities field empty**: Currently always empty, needs source mapping from API.

### Architecture Debt

- [ ] **No schema validation for API responses**
- [ ] **Browser automation is untested** (requires live website)

---

## 6. USEFUL COMMANDS

### CLI

```bash
# Sync collection
uv run kards sync

# Export collection
uv run kards export --format xlsx --file kards_cards_ru.xlsx
uv run kards export --format csv --file kards_cards_ru.csv
uv run kards export --format json --file kards_cards_ru.json

# Update quantities from XLSX
uv run kards update --file kards_cards_ru.xlsx

# Import deck
uv run kards deck import --file deck.txt

# Export deck (XLSX sheet / JSON)
uv run kards deck export --format xlsx --file kards_cards_ru.xlsx
uv run kards deck export --format json --file deck.json
```

### Make targets

```bash
make run-sync                   # Sync cards into SQLite
make run-export-xlsx            # Export to XLSX
make run-export-csv             # Export to CSV
make run-export-json            # Export to JSON
make run-update                 # Update quantities from XLSX
make run-import-deck FILE=deck.txt  # Import deck from TXT
make run-export-deck-xlsx       # Export deck as XLSX sheet
make run-export-deck-json       # Export deck to JSON
```

### Development

```bash
make format      # Format code (ruff)
make lint        # Lint (ruff)
make typecheck   # Type check (mypy)
make test        # Run tests (pytest + coverage)
make check       # All of the above
```

---

## 7. KEY DECISIONS & RATIONALE

| Decision | Why | Date |
|----------|-----|------|
| GraphQL interception over DOM parsing | More reliable, structured data, less fragile selectors | Jan 2025 |
| SQLite storage | Enables incremental sync and stable exports | Feb 2026 |
| Package structure with submodules | Separation of concerns, testability, maintainability | Feb 2026 |
| Typer CLI with subcommands | Replaces argparse flags, proper `sync`/`export`/`deck import`/`deck export` commands | Feb 2026 |
| Business logic in commands.py | Separates CLI declarations from business logic | Feb 2026 |
| Deck import/export | Manage player decks alongside collection | Feb 2026 |
| DECK_NATION_TO_DB mapping | Deck file uses English codes, DB stores Russian nation names | Feb 2026 |
| NATION_DISPLAY_NAMES mapping | Localized nation names for deck sheet headers | Feb 2026 |

---

## 8. DB SCHEMA

```sql
-- Card collection
cards (
    card_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    nation TEXT, type TEXT, rarity TEXT, abilities TEXT,
    set_name TEXT, quantity INTEGER, credits INTEGER,
    attack INTEGER, defense INTEGER, description TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)

-- Key-value store for sync timestamps etc.
metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)

-- Imported decks
decks (
    deck_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    major_power TEXT NOT NULL, ally TEXT, hq TEXT,
    deck_code TEXT,
    imported_at TEXT DEFAULT CURRENT_TIMESTAMP
)

-- Cards in a deck (references cards and decks)
deck_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL → decks(deck_id) ON DELETE CASCADE,
    card_id TEXT NOT NULL → cards(card_id),
    quantity INTEGER NOT NULL, cost INTEGER NOT NULL,
    UNIQUE(deck_id, card_id)
)
```

---

## 9. NATION MAPPINGS

Two separate mappings in `constants.py`:

**DECK_NATION_TO_DB** — maps deck file nation codes to database nation names (for card lookup):
```
soviet → Советский Союз    usa → США
britain → Великобритания    germany → Германия
japan → Япония             france → Франция
italy → Италия             poland → Польша
finland → Finland
```

**NATION_DISPLAY_NAMES** — maps nation codes to localized display names (for deck export sheet headers):
```
soviet → Советские    usa → Американские
britain → Британские   germany → Германские
japan → Японские      france → Французские
italy → Итальянские   poland → Польские
```
