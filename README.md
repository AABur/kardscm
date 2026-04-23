# KARDS Collection Manager

Manager for [KARDS](https://www.kards.com/) card game player collection and decks.
Syncs the official card catalog into SQLite and exports to XLSX, CSV, or JSON.

## Features

- Multi-language support (English and Russian)
- SQLite storage with upsert on sync (preserves user-managed `quantity`)
- Export to XLSX, CSV, JSON with localized headers
- Bulk collection quantity update from an edited XLSX
- Deck add/import from KARDS client TXT format (with exile-card fallback and collection quantity checks)
- Deck replace, delete, and export to XLSX or JSON
- Interactive deck selection for export and delete

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

Edit the `quantity` column in the XLSX exported above and feed it back with
`update`. Cards are matched by `faction + title`; whitespace differences
(NBSP, double spaces) are normalized automatically. Other columns are ignored.
Unmatched rows are logged as warnings and skipped.

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

# 2. Export collection to XLSX and edit the `quantity` column in your editor
kardscm export -f xlsx -o cards.xlsx
# ... edit cards.xlsx ...

# 3. Push edited quantities back into the database
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

## License

MIT
