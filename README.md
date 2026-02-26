# KARDS Collection Manager

Manager for [KARDS](https://www.kards.com/) card game player collection and decks.
Syncs the official card catalog into SQLite and exports to XLSX, CSV, or JSON.

## Features

- Multi-language support (English and Russian)
- SQLite storage with upsert on sync
- Export to XLSX, CSV, JSON with localized headers
- Deck import from KARDS client TXT format
- Deck export to XLSX or JSON
- Interactive deck selection for export

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
git clone git@github.com:AABur/kardscm.git
cd kardscm
make sync
```

## Configuration

Copy the example configuration and set your language:

```bash
cp config.ini.example config.ini
```

Edit `config.ini`:

```ini
[settings]
language = en
```

Supported languages: `en` (English, default), `ru` (Russian).

Changing the language requires deleting `collection.db` and re-running sync.

> Only English and Russian are supported out of the box.
> See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on adding a new language.

## Usage

### Sync card catalog

```bash
kardscm sync
```

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

### Import a deck

```bash
kardscm deck import -i deck.txt
```

The deck TXT file must use card names matching the configured language.

### Export a deck

```bash
kardscm deck export -f xlsx -o cards.xlsx
kardscm deck export -f json -o deck.json
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
- Deck import requires a synced collection (cards must exist in the database).
- Card abilities (Blitz, Guard, Fury, etc.) are translated according to the configured language.

## License

MIT
