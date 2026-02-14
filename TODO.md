# TODO Plan (collection.py refactor)

## Stage 1 (Scaffold, no behavior change yet)
- [x] Copy `kards_final_scraper.py` to `collection.py` (leave original untouched).
- [x] Rename internal identifiers to remove legacy `kards_final_scraper` wording.
- [x] Add new CLI skeleton: `--sync` and `--export --format --file` (no-op for now).
- [x] Freeze outputs to English-only docs/comments (no Russian in code).

## Stage 2 (Module split)
- [x] Define target module layout and responsibilities.
- [x] Extract export helpers into `exporters.py` with explicit inputs.
- [x] Extract translation + scrape flow into `scrape.py` functions.
- [x] Add `storage.py` placeholder with SQLite connection helpers.
- [x] Keep a thin `collection.py` CLI entrypoint that calls modules.

## Stage 3 (Russian-only scrape)
- [x] Remove multi-language configuration and mappings in `scrape.py`.
- [x] Hardcode Russian collection URL.
- [x] Localized fields: Russian first, fallback to English.
- [x] Export headers in Russian.

## Stage 4 (SQLite storage)
- [x] Define schema for cards table (including Abilities, Quantity).
- [x] Implement upsert by card ID.
- [x] Add metadata table for last sync timestamp.

## Stage 5 (Commands)
- [x] Implement `--sync` to fetch and upsert into `collection.db`.
- [x] Implement `--export --format <csv|json|xlsx> --file <name>` from SQLite.

## Stage 6 (Docs + polish)
- [x] Update README with new CLI, Russian-only scope, and SQLite workflow.
- [x] Update CLAUDE or CONTRIBUTION if references to old CLI remain.
- [x] Add tests for storage (schema, upsert, fetch) and CLI validation.

## Stage 7 (Abilities)
- [ ] Populate Abilities field.
