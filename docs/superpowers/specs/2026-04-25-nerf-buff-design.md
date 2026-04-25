# P2: Nerf/Buff Detection + Reserve Tracking — Design

**Status:** approved, ready for implementation
**Date:** 2026-04-25
**Target version:** 0.4.0
**Branch:** `design/2.0-nerf-buff` (this spec only; implementation tasks
branch separately from `main` after merge)

## Context

KARDS regularly issues balance patches that change card cost, attack,
defense, ability text, and keywords. KARDS also moves cards in and out of
"reserve" — reserved cards exist in the catalog but cannot be used in
deck-building. Patch-notes examples (April 2026 update): cost rebalances,
keyword swaps such as `Mobilize → Shock`, ability-text rewrites, stat
adjustments.

Today `sync_collection` calls `upsert_cards` which silently overwrites every
API field except `quantity`. Reserved and spawnable cards are filtered out at
the GraphQL layer (`showSpawnables=False`, `showReserved=False`). The user
has no way to see what changed between syncs — a card can be nerfed and
disappear from view between two `sync` invocations with no record.

P2 makes sync interactive and observable, with a focus on giving the user a
clear, approveable diff before any DB writes happen.

## Non-goals

- A `card_history` archive table. Single-shot Markdown report per sync is
  sufficient for the user's workflow.
- Export integration (a "changed since last sync" column in XLSX/CSV/JSON).
  Deferred to a later phase.
- Deck-export warnings ("these cards in your deck were nerfed since you
  built it"). Deferred.
- Showing exiles. `showExiles` stays `False` — exiles are a separate concept
  that the user did not ask for and is unrelated to the buff/nerf workflow.
- Per-card interactive prompts. Approval is bulk per category, not per card.

## User-facing behavior

`uv run kardscm sync` becomes interactive when there is anything to report:

1. Fetches all cards (now including reserved and spawnable).
2. Compares to the current DB state.
3. If there are no differences, logs `No changes` and exits.
4. Otherwise prints a four-section console report:
   - **New cards** — present in API, absent from DB.
   - **Changed characteristics** — same `cardId`, one or more compared fields
     differ.
   - **Reserve transitions** — `reserved` flipped, listed as two sub-lists:
     "moved to reserve" and "returned from reserve".
   - **Removed cards** — present in DB, absent from API response.
5. For each non-empty category, prompts a single `y/N` covering the whole
   list.
6. Any `n` aborts the entire sync. The DB is left untouched. A Markdown
   report is still written.
7. On full approval, applies the writes (`upsert_cards` + `delete_cards` if
   the removed category was approved), updates `last_sync` metadata, and
   writes the Markdown report.

A `--diff-only` flag runs steps 1–4 and writes the report file, then exits
without prompting and without writing to the DB. Useful for previewing what
the next real sync will do, or for CI/automation.

A `--yes` flag auto-approves every category. Useful for scripting; the diff
is still printed and the report is still written.

## Compared fields

Per matching `cardId`, the diff engine compares these and only these fields:

| Field           | How compared                                              |
|-----------------|-----------------------------------------------------------|
| `kredits`       | numeric equality                                          |
| `attack`        | numeric equality (treats None == None)                    |
| `defense`       | numeric equality (treats None == None)                    |
| `operationCost` | numeric equality (treats None == None)                    |
| `attributes`    | JSON-deserialized, compared as a set (order-independent)  |
| `text`          | extract value at `LanguageConfig.locale_key`, compare str |

`reserved` is read from both records but routed to its own category, not the
generic "changed" list.

Other API fields (`title`, `imageUrl`, `thumbUrl`, `importId`, `image`,
`type`, `faction`, `rarity`, `set`, `can_create`, `exile`) are still
upserted in DB but not surfaced in the diff. Rationale:

- `title`, `type`, `faction`, `rarity`, `set` — almost never change; a
  rename does not affect gameplay.
- `imageUrl`, `thumbUrl`, `image`, `importId` — internal references, churn
  is noise.
- `can_create`, `exile` — internal/rare; not worth the report space.

Comparing `text` only at the active locale guards against false positives
when KARDS adds a new server-side locale: a Russian-only user sees no diff
when a German translation is rolled out.

## GraphQL changes

`kardscm/constants.py:GRAPHQL_VARIABLES` flips:

```python
"showSpawnables": True,   # was False
"showReserved": True,     # was False
"showExiles":   False,    # unchanged
```

The captured GraphQL query already declares these as variables and the
fetcher pipes them unchanged into every paginated request, so no other
scrape-layer code changes.

Spawnables (cards spawned by other cards as tokens) will appear in the DB.
They have their own `cardId` and stats and live alongside collectible cards.
Quantity stays at zero for them since the user cannot collect them. This is
fine — `quantity` is preserved by upsert; nothing forces a write.

## Reject behavior

A `n` answer at any prompt aborts the whole sync. No partial application —
a sync that the user partially distrusts is a sync the user cannot reason
about. The Markdown report is still written so the user has a permanent
record of what they declined.

## Empty-diff path

If `compute_diff` returns an empty report (no new, changed, reserved-in,
reserved-out, or removed entries), sync proceeds silently:

- No prompts.
- No report file is written.
- `last_sync` metadata is updated to the current timestamp.
- Single log line `No changes`.

This keeps repeat syncs cheap and quiet.

## Diff report file

Default path: `./sync-diff-<UTC-iso-timestamp>.md` in the current working
directory (e.g. `sync-diff-2026-04-25T14-32-11Z.md`). Overridable via
`--diff-report PATH`. Not written to `docs/` to avoid polluting the repo.

Format: Markdown with one `##` header per non-empty category, a faction
sub-grouping, then a bullet list. Examples per category:

```markdown
## Changed characteristics

### Soviet
- **CHAR B1 BIS** — attributes: `[Mobilize, Heavy Armor 2]` →
  `[Shock, Blitz, Heavy Armor 2]`; text: "...full English diff..."
```

Localized labels (faction names, category headings) come from
`LanguageConfig`.

## Module layout

### `kardscm/constants.py` (modified)
GraphQL variable flip described above.

### `kardscm/models.py` (modified)
Add `FieldChange`, `CardChange`, `DiffReport` TypedDicts.

### `kardscm/diff.py` (new)
Pure logic, no IO, no DB, no prompts:

- `compute_diff(old_cards, new_cards, locale_key) -> DiffReport`
- `format_console_report(report, lang_config) -> str`
- `format_markdown_report(report, lang_config, timestamp) -> str`

### `kardscm/storage/database.py` (modified)
Add `fetch_all_cards(conn) -> list[dict]` and
`delete_cards(conn, card_ids) -> None`. Existing `upsert_cards` is unchanged.

### `kardscm/commands.py` (modified)
Rewrite `sync_collection` to load old cards, compute the diff, drive the
interactive loop or `--diff-only` shortcut, and apply writes only on full
approval. Signature gains keyword-only `diff_only`, `yes`,
`diff_report_path`.

### `kardscm/cli.py` (modified)
`sync` Typer command gains `--diff-only`, `--yes`, `--diff-report PATH`.

## Reused, not reinvented

- `kardscm.config.LanguageConfig.locale_key` — gives `"en-EN"` or `"ru-RU"`
  for `text` comparison.
- `kardscm.config.LanguageConfig.faction_names` — for localized faction
  labels in both report formats.
- `kardscm.helpers.to_text` — already extracts a localized string from a
  JSON-encoded dict; reuse for `text` comparison.
- `typer.confirm` — for y/N prompts.

## Test plan

`tests/test_diff.py` (new):

- empty diff when old equals new
- numeric field changes flagged with correct old/new
- `attributes` change flagged as set diff (order ignored)
- `text` change flagged for current locale only (no false positive when an
  English-only update is rolled out for a `ru-RU` user)
- `reserved 0→1` lands in `reserved_in`, `1→0` in `reserved_out`
- API-only `cardId` lands in `new`; DB-only lands in `removed`

`tests/test_storage.py` (extended):

- `fetch_all_cards` round-trips `upsert_cards` data
- `delete_cards` removes only specified ids; quantity for surviving cards is
  intact

`tests/test_commands.py` (extended) with `compute_diff` mocked:

- empty diff: no prompts, no report file, `last_sync` updated
- non-empty diff with `diff_only=True`: report written, neither
  `upsert_cards` nor `delete_cards` called
- non-empty diff, user rejects at first prompt: report written, no DB
  writes, `last_sync` not updated
- non-empty diff, user approves all: `upsert_cards` called;
  `delete_cards` called only when the removed category was non-empty AND
  approved

## Implementation tasks

This spec replaces the original Phase 2 task breakdown
(`docs/superpowers/plans/2026-04-24-execution-plan.md`). New task list:

- **2.0** — this design spec (one PR, this branch).
- **2.1** — `feat: include reserved+spawnable in sync` (constants flip,
  test that GRAPHQL_VARIABLES has expected values).
- **2.2** — `feat: compute and render sync diff` (models, `diff.py`,
  storage helpers, tests). No CLI wiring.
- **2.3** — `feat: make sync interactive with diff approval`
  (`commands.py` rewrite, CLI flags, integration tests).
- **2.4** — release: `CHANGELOG [0.4.0]`, version bump, tag, release.

The original plan's `card_history` work (old Task 2.1) is deleted — no
history table per the chosen design. Old Task 2.2 (separate diff report
task) merges into 2.2 above. Old Task 2.3 (`--diff-only` flag) folds into
2.3 above.

## Verification (per task)

1. `make check` green before every PR.
2. Manual smoke after Task 2.3:
   - `uv run kardscm sync --diff-only` on a populated DB → report file
     written, no DB or `last_sync` change.
   - Mutate one card via SQLite (`UPDATE cards SET kredits = kredits + 1
     WHERE cardId = '<id>';`) then `uv run kardscm sync` → exactly one
     change shown; `n` keeps the mutation, `y` reverts to API value.
   - `SELECT COUNT(*) FROM cards WHERE reserved = 1;` > 0 after the first
     sync with new constants.

## Open questions

None. All design questions resolved during the planning session on
2026-04-25.
