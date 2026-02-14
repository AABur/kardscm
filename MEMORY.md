# MEMORY.md - KARDS Card Collection

> Multi-agent development memory for AI assistants (Claude Code, Codex, Cursor, Gemini CLI, etc.)

---

## 1. PROJECT OVERVIEW

**What it does:** Syncs card data from the KARDS website (Russian) into SQLite and exports it to XLSX, CSV, or JSON.

**Tech stack:**
- Python 3.12
- playwright (browser automation)
- httpx (async HTTP client)
- openpyxl (Excel export)
- sqlite3 (local storage)

**Entry point:** `collection.py`

**Language scope:** Russian only with English fallback for missing text.

**Export formats:** xlsx, csv, json

---

## 2. ARCHITECTURE

```
CLI (argparse)
    |
    v
collection.py (entrypoint)
    |
    +-- scrape.py (scrape_cards)
    |       |
    |       +-- load_translations() -- fetches JS chunks from website
    |       +-- translate_value() -- translates category values
    |       +-- sanitize_text() -- decodes escapes and normalizes text
    |       +-- collect_api_data() -- intercepts GraphQL responses
    |
    +-- storage.py (SQLite)
    |       |
    |       +-- initialize_schema() -- create tables
    |       +-- upsert_cards() -- insert/update by card_id
    |       +-- fetch_cards() -- load for export
    |
    +-- exporters.py
            |
            +-- export_to_xlsx() -- Excel with Russian headers
            +-- export_to_csv() -- UTF-8 with BOM
            +-- export_to_json() -- with metadata
```

---

## 3. DATA FLOW

```
1. CLI parses arguments (--sync / --export)
       |
       v
2. scrape.py loads translations and opens collection page
       |
       v
3. Playwright intercepts GraphQL responses
       |
       v
4. parse_api_data() extracts cards and normalizes text
       |
       v
5. storage.py upserts into SQLite (collection.db)
       |
       v
6. export reads from SQLite and writes xlsx/csv/json
```

---

## 4. CRITICAL GOTCHAS

### Fragile Points (will break when website changes)

| Issue | Location | Risk | Workaround |
|-------|----------|------|------------|
| Hardcoded JS chunk ID "2840-" | scrape.py | **HIGH** | Falls back to static mappings if JS not found |
| Button text detection "LOAD MORE" | scrape.py | **MEDIUM** | Stops after 50 clicks anyway |
| GraphQL response structure | scrape.py | **MEDIUM** | Logs warning, skips malformed cards |

### Translation Loading Failure Modes

1. **JS URL not found** -> Uses static mappings
2. **HTTP timeout** -> Uses static mappings
3. **Translation ID not in JS** -> Returns original value unchanged

---

## 5. KNOWN ISSUES & TECHNICAL DEBT

### Bugs to Fix

- [ ] **Abilities field empty**: Currently always empty, needs source mapping.

### Architecture Debt

- [ ] **No schema validation for API responses**
- [ ] **Browser automation is untested**

---

## 6. USEFUL COMMANDS

### Sync

```bash
uv run python collection.py --sync
```

### Export

```bash
uv run python collection.py --export --format xlsx --file kards_cards_ru.xlsx
uv run python collection.py --export --format csv --file kards_cards_ru.csv
uv run python collection.py --export --format json --file kards_cards_ru.json
```

### Development

```bash
make format
make lint
make typecheck
make test
```

---

## 7. KEY DECISIONS & RATIONALE

| Decision | Why | Date |
|----------|-----|------|
| GraphQL interception over DOM parsing | More reliable, structured data, less fragile selectors | Jan 2025 |
| SQLite storage | Enables incremental sync and stable exports | Feb 2026 |
