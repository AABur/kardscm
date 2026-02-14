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
make run-sync
```

### Export collection

```bash
make run-export-xlsx
make run-export-csv
make run-export-json
```

### Update card quantities from XLSX

```bash
make run-update
```

### Import a deck

```bash
make run-import-deck FILE=deck.txt
```

The deck TXT file must use card names matching the configured language.

### Export a deck

```bash
make run-export-deck-xlsx
make run-export-deck-json
```

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
- Exports: default filenames defined in Makefile

## Notes

- Data is obtained from the official KARDS website.
- The scrape targets the collection page in the configured language and falls back to English when needed.
- Deck import requires a synced collection (cards must exist in the database).
- The "Abilities" / "Способности" field is currently empty — the KARDS API does not expose this data.

## License

MIT
