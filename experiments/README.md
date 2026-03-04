# Experiments

Local-only workspace for research experiments with the KARDS collection data.

## Rules

- Import from `kardscm` package freely: `from kardscm.config import ...`
- Keep experiments self-contained in subfolders
- No production code changes

## Structure

```
experiments/
├── README.md
├── card-schema/    — KARDS API schema exploration
└── synergies/      — Nation synergy analysis
```

---

## card-schema

Explored the KARDS card API: fetched raw GraphQL data, documented the JSON schema,
generated TypeScript types, and computed card distribution statistics.

### Files

| File | Description |
|------|-------------|
| `dump_raw_cards.py` | Fetches API data via Playwright and splits by nation |
| `cards_*.json` | Raw card data per nation (9 files) |
| `kards_card_schema.json` | JSON Schema (draft-07) for card data |
| `kards_card_types.ts` | TypeScript type definitions |
| `SCHEMA.md` | Full schema documentation |
| `STATISTICS.md` | Card distribution statistics |

### How to run

```bash
# Fetch fresh card data from kards.com (requires browser)
uv run python experiments/card-schema/dump_raw_cards.py
```

---

## synergies

Analyzed nation-specific synergy mechanics (Alpine, Salvage, Sissi, Exile,
Resistance, Naval) extracted from the raw card data.

### Files

| File | Description |
|------|-------------|
| `extract_synergies.py` | Analysis script — reads card-schema data, writes outputs |
| `nation_synergies.json` | Structured synergy data (output) |
| `synergies_report.md` | Human-readable report with deckbuilding tips (output) |

### How to run

```bash
# Requires card-schema/cards_*.json to exist first
uv run python experiments/synergies/extract_synergies.py
```
