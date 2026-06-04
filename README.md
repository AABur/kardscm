# KARDS Collection Manager

[![CI](https://github.com/AABur/kardscm/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/AABur/kardscm/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`kardscm` is a local collection and deck manager for
[KARDS](https://www.kards.com/).

It syncs the official card catalog into a local SQLite database, lets you keep
your owned card quantities up to date, saves decks from KARDS client TXT files,
and exports collection or deck data to XLSX, CSV, or JSON.

The tool is local-first:

- no account
- no hosted service
- no PyPI package
- database stored as `collection.db` in the working directory

## Disclaimer

`kardscm` is an **unofficial fan tool**, not affiliated with or endorsed by
1939 Games ehf. KARDS and all related card names, art, and trademarks are the
property of 1939 Games ehf.

The tool is intended for **personal, non-commercial use**. Users are
responsible for complying with the
[KARDS Terms of Use](https://www.kards.com/terms-of-use).

This repository ships no card data, card art, or pre-built database. The local
SQLite catalog is built on the user's own machine.

## What It Does

- Syncs the full KARDS card catalog, including reserved and spawnable cards.
- Preserves user-managed card quantities across syncs.
- Shows catalog changes before applying them: new cards, changed stats/text,
  reserve transitions, and removed cards.
- Exports the collection to XLSX, CSV, or JSON.
- Updates card quantities from an edited XLSX export.
- Imports, adds, replaces, deletes, and exports saved decks.
- Provides a local browser UI for browsing, filtering, and editing quantities.
- Provides an admin-only local mode for full card-field correction with an
  automatic database backup.
- Tracks API contract drift against a committed baseline.
- Adds manually curated extra-ability tags for game-client-only mechanics not
  exposed by the official GraphQL API.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Installation

`kardscm` is distributed only from GitHub. It is not published to PyPI.

```bash
git clone git@github.com:AABur/kardscm.git
cd kardscm
make sync
```

For an isolated command install:

```bash
pipx install git+https://github.com/AABur/kardscm.git
```

Check the installed version with `kardscm --version` (short: `-v`).

## Quick Start

If you installed via `pipx`, run `kardscm` directly. If you cloned the
repo and ran `make sync`, prefix each command with `uv run` (or
activate `.venv` first) so the console script is found:

```bash
# 1. Sync the card catalog into collection.db.
uv run kardscm sync

# 2. Open the local browser UI and edit quantities.
uv run kardscm web

# 3. Export your collection.
uv run kardscm export -f xlsx -o cards.xlsx

# 4. Add a deck exported from the KARDS client.
uv run kardscm deck add my-deck.txt

# 5. Export a saved deck.
uv run kardscm deck export -f xlsx -o deck.xlsx
```

## Language

Use the global `--lang` (short: `-l`) flag before the subcommand:

```bash
kardscm --lang ru sync
kardscm -l de export -f xlsx -o cards.xlsx
kardscm --lang zh-Hant web
```

Supported codes: `en`, `ru`, `de`, `fr`, `it`, `es`, `pt`, `pl`, `ja`, `ko`,
`zh`, `zh-Hant`.

English and Russian are maintained. Other locale files may be partial; missing
translation keys fall back to English and are reported in the CLI or web UI.

## Sync

```bash
kardscm sync
kardscm sync --diff-only
kardscm sync --yes
kardscm sync --diff-report ./sync-report.md
```

`sync` fetches the official catalog, compares it with the local database, and
shows a diff before writing changes. Any rejected prompt aborts the sync and
leaves the database unchanged. A Markdown report is written whenever there are
changes.

`--diff-only` writes the report without modifying the database. `--yes`
(short: `-y`) auto-approves every category for scripted runs.

Sync also checks the live GraphQL response *shape* against the committed
baseline `kardscm/data/api_baseline.json`. A genuine contract change — a field
added or removed, a field becoming sparse, a new `faction`/`type`/`rarity`/
ability value, or a sharp drop in card count — **halts the sync** and writes
`sync-schema-diff-*.md` and `sync-schema-observed-*.json` to the current
directory. Normal content growth (new card sets, more cards) is not a contract
change and never blocks. After reviewing a halt, run `kardscm baseline accept`
to adopt the new shape (or `kardscm baseline init` to rebuild from the live
API), then sync again.

## Collection Export And Update

```bash
kardscm export -f xlsx -o cards.xlsx
kardscm export -f csv -o cards.csv
kardscm export -f json -o cards.json
```

To update quantities from an edited spreadsheet:

```bash
kardscm update -i cards.xlsx
```

Only the quantity column is read. Cards are matched by faction and title in the
active language. Whitespace differences such as NBSP and double spaces are
normalized.

## Web UI

```bash
kardscm web
kardscm web --port 9000        # short: -p
kardscm web --no-browser
kardscm --lang ru web
```

The web UI runs locally at `127.0.0.1:8765` by default. It provides collection
browsing, sorting, filters, card details, quantity editing, and full
**Sync** and **Export** flows so the browser is the only surface needed to
manage a collection.

Click **Edit** to enable quantity changes. Quantity writes are server-side
validated by rarity caps:

- Standard: 4
- Limited: 3
- Special: 2
- Elite: 1

Click **Sync** to pull the latest cards from the website. The flow is
two-phase:

1. Confirm the action in the modal — the server runs the same fetch +
   diff the CLI does, with a spinner while the request is in flight.
2. Review the categorized diff (new / changed / reserve transitions /
   removed) and either **Apply changes** or **Cancel**. Cancel leaves
   the database untouched; apply persists everything in one shot and
   writes a Markdown diff report next to the working directory, just
   like `kardscm sync`. When the API and the local database already
   match, the modal collapses to a single "no changes" notice and
   only `last_sync` metadata is touched.

Click **Export** to download the current collection. Pick **Excel
(.xlsx)**, **CSV**, or **JSON** — the browser receives the file
directly; nothing is written to the server filesystem. The exported
content matches `kardscm export -f <fmt>` exactly, in the active
language.

## Admin Mode

```bash
kardscm web --admin            # short: -A
kardscm --lang ru web --admin
```

Admin mode is for trusted local correction of catalog data. It exposes editable
card stats, categories, ability flags, extra-ability flags, reserved state, and
localized title/text for the active locale.

Admin mode:

- only starts on localhost
- creates a timestamped database backup before startup
- shows the backup path in a red banner
- does not register admin routes unless `--admin` is passed

## Decks

```bash
kardscm deck add deck.txt
kardscm deck add *.txt
kardscm deck add deck.txt -u
kardscm deck add deck.txt -r
kardscm deck delete
kardscm deck export -f xlsx -o deck.xlsx
kardscm deck export -f json -o deck.json
```

`deck add` is the preferred import path. It looks up cards by faction, falls
back to exile links when needed, checks collection quantities, and can update
or replace existing data:

- `--update` / `-u`: raise collection quantities to match the deck
- `--replace` / `-r`: overwrite an existing saved deck with the same name

`deck import` still exists as a simpler single-file import path, but day-to-day
use should prefer `deck add`.

## Deck File Format

KARDS client TXT decks look like this:

```text
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

Rules:

- first non-empty line is the deck name
- `Major power:` is required
- `Ally:` and `HQ:` are optional
- nation sections use `nation:` headers
- card rows use `<qty>x (<cost>K) <name>`
- the `%%` deck-code line is optional

## API Baseline

Maintainers can refresh the committed API baseline (run from a clone;
pipx users can drop the `uv run` prefix):

```bash
uv run kardscm baseline init
uv run kardscm baseline accept
```

A contract change halts the sync; use these commands to resolve it. Use
`baseline init` after intentional API changes or for a fresh rebuild from the
live API. Use `baseline accept` after reviewing the latest
`sync-schema-observed-*.json` file from a sync drift report.

## Output Files

- `collection.db`: local SQLite database
- `collection.db.bak*`: local backups
- `sync-diff-*.md`: sync reports
- `sync-schema-diff-*.md`: API drift reports
- `sync-schema-observed-*.json`: observed API snapshots
- export files: whatever path you pass with `-o`

Generated local data is intentionally not part of the repository.

## Development

Developer setup, architecture, release process, and maintainer workflows are in
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT.

The MIT license covers the source code of `kardscm` itself. It does not grant
any rights over KARDS game content, card data, or trademarks; see the
[Disclaimer](#disclaimer) section above.
