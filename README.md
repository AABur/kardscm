# KARDS Collection Manager

[![CI](https://github.com/AABur/kardscm/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/AABur/kardscm/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Manager for [KARDS](https://www.kards.com/) card game player collection and decks.
Syncs the official card catalog into SQLite and exports to XLSX, CSV, or JSON.

## Features

- Multi-language support (12 locales: en, ru, de, fr, it, es, pt, pl, ja, ko, zh, zh-Hant)
- SQLite storage with upsert on sync (preserves user-managed `quantity`)
- Export to XLSX, CSV, JSON with localized headers
- Bulk collection quantity update from an edited XLSX
- Deck add/import from KARDS client TXT format (`deck add` includes exile-card fallback and collection quantity checks)
- Deck replace, delete, and export to XLSX or JSON
- Interactive deck selection for export and delete
- Browser-based Web UI for collection browsing, filtering, and editing
- User edit mode — quantity editing with rarity caps and save-confirmation modal
- Admin mode (`--admin`) — full-field editing via modal form, with DB auto-backup
- API contract drift detection — compares live GraphQL shape against a committed baseline
- Extra-ability tags — manually curated flags for abilities not in the official API

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Installation

`kardscm` is distributed **only from GitHub**. It is not and will not
be published to PyPI — clone the repo and run it via `uv`.

```bash
git clone git@github.com:AABur/kardscm.git
cd kardscm
make sync
```

Or, for an isolated install without cloning:

```bash
pipx install git+https://github.com/AABur/kardscm.git
```

## Configuration

Pick a UI language with the global `--lang` flag — it works on every
subcommand (default is English):

```bash
kardscm --lang ru sync
kardscm --lang de export -f xlsx -o cards.xlsx
kardscm --lang zh-Hant web
```

Supported codes: `en`, `ru`, `de`, `fr`, `it`, `es`, `pt`, `pl`, `ja`,
`ko`, `zh`, `zh-Hant`. Locales other than `en` and `ru` ship as
scaffolds. Scaffold files set `code`, `name`, `locale_key`, and
`collection_sheet_name`; untranslated keys are **omitted** so the
loader falls back to English and logs them via `fallback_warnings` on
stderr. Keys present with an empty string value (`""`) are treated as
valid translations and do **not** trigger fallback — scaffold authors
should omit keys rather than blank them.

To add or refine a locale, drop a `<code>.toml` into
`kardscm/locales/`. Missing keys fall back to English; the loader
discovers `*.toml` files at import time.

## Usage

### Sync card catalog

```bash
kardscm sync                              # interactive: review and approve changes
kardscm sync --diff-only                  # dry-run: print + write report, do not modify DB
kardscm sync --yes                        # auto-approve everything (CI / scripting)
kardscm sync --diff-report ./out.md       # custom report path
```

Sync fetches the full catalog (including reserved and spawnable cards),
diffs it against the local DB, and groups changes into four categories:
**new cards**, **changed characteristics** (cost, attack, defense, operation
cost, abilities, ability text), **reserve transitions** (in/out), and
**removed cards**. Each non-empty category is shown to you and prompts a
single y/N. Any "no" aborts the sync — the DB is left untouched. A
Markdown diff report (`./sync-diff-<UTC-iso>.md` by default) is written
whenever the diff is non-empty.

Sync also runs **API contract drift detection**: it compares the observed
shape of the GraphQL response (top-level node keys, JSON keys with
presence ratios, distinct enum values for faction/type/rarity/set/
attributes, card count) against `kardscm/data/api_baseline.json`. On any
divergence, sync writes a `sync-schema-diff-<UTC-iso>.md` report and a
companion `sync-schema-observed-*.json` snapshot to the current directory
and continues — drift never aborts a sync.

### Manage the API baseline

```bash
kardscm baseline init      # fetch live API → overwrite the committed baseline
kardscm baseline accept    # promote the latest sync-schema-observed-*.json
```

Use `init` once after cloning the repo or after intentional API changes.
Use `accept` after reviewing a `sync-schema-diff-*.md` report and updating
any constants/translations to acknowledge the new API shape — the latest
observed snapshot in cwd is validated and copied to the baseline file.

### Export collection

```bash
kardscm export -f xlsx -o cards.xlsx
kardscm export -f csv -o cards.csv
kardscm export -f json -o cards.json
```

### Update card quantities from XLSX

```bash
kardscm update -i cards.xlsx
```

Edit the `quantity` column in the XLSX exported above and feed it back with
`update`. Cards are matched by `faction + title`; whitespace differences
(NBSP, double spaces) are normalized automatically. Other columns are ignored.
Unmatched rows are logged as warnings and skipped.

### Browse and edit in the browser

```bash
kardscm web                        # open at http://127.0.0.1:8765
kardscm web --port 9000            # custom port
kardscm web --no-browser           # don't auto-open the browser
kardscm --lang ru web              # Russian UI
kardscm --lang ru web --admin      # admin mode (full-field editing)
```

The web UI shows the full collection with filterable columns (faction, type,
rarity, set, kredits, text search, spawnable/reserved/owned toggles) and a
sortable card table. Click any row to view card details and the card image.

**User edit mode** — click **Edit** in the page header to enable inline quantity
editing. Each cell saves immediately on change. When you click **Save**, a
confirmation modal shows the before/after diff; you can confirm, continue
editing, or undo all changes. Rarity caps are enforced automatically (Standard 4
/ Limited 3 / Special 2 / Elite 1).

**Admin mode** (`--admin` / `-A`) additionally exposes a modal form for every
editable field: stats (kredits, attack, defense, operationCost), all ability and
extra-ability flags, categories (faction, type, rarity, set), the `reserved`
flag, and localized title/text (active locale only). Admin mode:
- backs up the database to a timestamped sibling file before the server starts
- shows a red banner in the browser with the backup path
- is restricted to localhost and refuses to start on any other host

### Add a deck

```bash
kardscm deck add deck.txt
kardscm deck add *.txt                 # add many at once; errors are batched
kardscm deck add deck.txt -u           # also sync collection quantities to deck
kardscm deck add deck.txt -r           # replace existing deck with same name
```

`deck add` is the primary way to save a deck. It:

- looks up cards by faction first, then falls back to the exile field
- fails if any card is missing from the collection (shows which ones)
- with `--update`/`-u`, raises collection quantities to match the deck
- with `--replace`/`-r`, overwrites an existing deck with the same name
- continues past failures when multiple files are given and prints a summary

The deck TXT file must use card names matching the configured language.

### Import a deck

```bash
kardscm deck import -i deck.txt
```

Simpler single-file alternative to `deck add`: no exile fallback, no quantity
check, no `--replace`. Prefer `deck add` for day-to-day use.

### Delete a deck

```bash
kardscm deck delete
```

Lists saved decks, prompts for selection and confirmation.

### Export a deck

```bash
kardscm deck export -f xlsx -o deck.xlsx
kardscm deck export -f json -o deck.json
```

Interactively prompts for a deck when more than one is saved.

## Typical workflow

End-to-end loop for keeping collection and decks in sync:

```bash
# 1. Pull the card catalog (first run or after a patch)
kardscm sync

# 2a. Open the browser UI and edit quantities inline (recommended)
kardscm web

# — or — 2b. Export to XLSX, edit the `quantity` column, push back
kardscm export -f xlsx -o cards.xlsx
# ... edit cards.xlsx ...
kardscm update -i cards.xlsx

# 4. Save decks exported from the KARDS client
kardscm deck add my-deck.txt

# 5. If the collection is short on copies, let the deck top it up
kardscm deck add my-deck.txt -u

# 6. Replace a deck after rebuilding it in the client
kardscm deck add my-deck.txt -r
```

## Deck file format

The deck TXT file exported from the KARDS client looks like this:

```
My Deck Name
Major power: soviet
Ally: germany
HQ: some_hq_name

soviet:
4x (1K) Card Name One
2x (3K) Card Name Two

germany:
3x (2K) Card Name Three

%%DECKCODE...
```

- First non-empty line is the deck name
- `Major power:` (required), `Ally:`, `HQ:` are metadata lines
- Nation sections start with `nation:` header
- Cards follow the format: `<qty>x (<cost>K) <name>`
- Deck code line (starting with `%%`) is optional

## Development

```bash
make sync-dev   # install all dependencies including dev tools
make check      # run all checks (format, lint, typecheck, test)
make test       # run tests only
make lint       # run ruff linter
make format     # format code with ruff
make typecheck  # run mypy
make clean      # clean cache files
```

## Output

- Database: `collection.db` (created on first sync)
- Exports: filenames specified via `-o` option

## Notes

- Data is obtained from the official KARDS website.
- The scrape targets the collection page in the configured language and falls back to English when needed.
- `deck add`/`deck import` require a synced collection — every card in the deck file must already exist in the database.
- Card lookups normalize whitespace (NBSP, double spaces) so titles from the KARDS API always match user input.
- `sync` preserves user-managed `quantity` on upsert; re-syncing never resets edited quantities.
- Card abilities (Blitz, Guard, Fury, etc.) are translated according to the configured language.
- Web UI quantity editing enforces rarity caps: Standard 4 / Limited 3 / Special 2 / Elite 1.
- Admin mode (`--admin`) is localhost-only and auto-backs up the database before starting.

## License

MIT
