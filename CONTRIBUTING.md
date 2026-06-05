# Contributing

This project is a local Python CLI and web UI for managing a KARDS collection
and saved decks. Keep changes small, verified, and documented.

## Setup

```bash
make sync-dev
```

This installs runtime and development dependencies through `uv`.

Use `uv`, not direct `pip`, for project work.

## Commands

```bash
make help       # list available make targets
make sync       # install runtime dependencies
make sync-dev   # install runtime/dev dependencies
make run        # show kardscm CLI help
make sync-diff  # preview catalog sync without DB changes
make web        # start the local web UI
make web-admin  # start admin web UI with DB backup
make test       # pytest with coverage
make lint       # ruff check
make format     # ruff format
make typecheck  # mypy over kardscm/
make check      # format, lint, typecheck, test
make clean      # remove local caches
make release    # run checks and print the release checklist
```

Useful local runs:

```bash
uv run kardscm --help
uv run kardscm sync --diff-only
uv run kardscm web --no-browser
uv run kardscm web --admin --no-browser
uv run pytest tests/test_deck_parser.py -v
```

## Project Shape

```text
kardscm/
  cli.py              Typer command declarations
  commands/           CLI business workflows (package)
  config.py           language lookup compatibility layer
  constants.py        URLs, GraphQL query, known ability keys, DB defaults
  diff.py             sync diff computation and rendering
  helpers.py          small parsing/text helpers
  models.py           TypedDict models used across modules
  scraping/           GraphQL probe, fetch, normalization, API baseline drift
  storage/            SQLite schema, migrations, card/deck persistence, backups
  export/             collection and deck exporters
  importing/          KARDS client deck TXT parser
  locales/            TOML locale files and locale loader
  data/               committed baseline/seed data
  web/                FastAPI + Jinja2 + HTMX local web UI
tests/                pytest suite
scripts/              maintainer helpers
```

Root files are intentionally sparse:

- `README.md`: user-facing guide
- `CONTRIBUTING.md`: developer and maintainer guide
- `AGENTS.md`: coding-agent operating rules
- `CLAUDE.md`: Claude-specific pointer to `AGENTS.md`
- `CHANGELOG.md`: release history
- `Makefile`: common commands
- `pyproject.toml` / `uv.lock`: package metadata and locked dependency graph
- `LICENSE`: MIT license

Do not add a new top-level documentation tree unless there is a clear need that
does not fit README or CONTRIBUTING.

## Architecture

`kardscm` has one local source of truth: `collection.db`.

The main data flows are:

```text
official KARDS GraphQL API
  -> scraping.fetcher/probe
  -> scraping.normalizer
  -> commands.sync_collection
  -> storage.database
  -> collection.db
```

```text
collection.db
  -> export.exporters
  -> XLSX / JSON
```

```text
KARDS deck TXT
  -> importing.parser
  -> commands.add_deck (or) commands.import_deck
  -> storage.database
  -> collection.db
```

```text
collection.db
  -> web.queries / web.translate
  -> FastAPI + Jinja templates
  -> local browser UI
```

Important boundaries:

- `cli.py` should stay thin. It declares command shape and forwards to
  `commands/`.
- `commands/` owns user workflows and IO orchestration.
- `scraping/` owns raw API acquisition and normalization.
- `storage/` owns SQLite schema and persistence.
- `export/` owns file output formats.
- `web/` owns local browser routes, queries, templates, and view translation.
- `locales/` owns UI/export translations. English is the baseline.

## Database

The default database path is `collection.db` in the current working directory.
It is local user data and must not be committed.

Card columns follow the KARDS API shape where practical (`cardId`,
`operationCost`, etc.). User-managed `quantity` is preserved across syncs.

Schema initialization also handles:

- incompatible old `nation` schemas: fail with manual reset instructions
- legacy `attributes` schema: backup, recreate, and ask the user to re-sync
- extra-ability columns: idempotently add missing `extra_ability_*` columns
- extra-ability seed freshness: reapply bundled seed when its hash changes

## Sync And API Drift

`kardscm sync` fetches the catalog, computes a diff, asks for category approval,
and writes only after approval. Rejected syncs leave the DB unchanged.

The API baseline lives at:

```text
kardscm/data/api_baseline.json
```

During sync, the raw GraphQL response *shape* is compared with this committed
baseline. A contract change **halts the sync** (it raises
`ApiContractDriftError` before any DB write) and produces local files for
review:

```text
sync-schema-diff-*.md
sync-schema-observed-*.json
```

A contract change means: a top-level or JSON key added or removed, a key
becoming sparse, a new `faction`/`type`/`rarity`/ability value, or a sharp drop
(>=10%) in card count. Benign content growth — new card sets, more cards — is not
drift and never halts.

Workflow when a sync halts on drift:

1. Review the generated schema diff and observed snapshot.
2. Update code/constants/locales if the new shape needs handling.
3. Run `uv run kardscm baseline accept` to promote the latest observed snapshot.
4. Commit the baseline update with the related code or data change, then re-run
   the sync.

A from-scratch baseline is created automatically on the first sync when the
baseline file is missing; there is no separate init command.

GraphQL introspection is not assumed to be available. Treat the baseline as a
data-derived contract snapshot.

## Extra Abilities

Some KARDS mechanics are visible in the game client but are not exposed as
official GraphQL attributes. Those are tracked as manually curated
extra-ability flags.

Relevant files:

```text
kardscm/constants.py                 KNOWN_EXTRA_ABILITIES
kardscm/data/extra_abilities.toml    cardId seed lists
scripts/discover_extra_abilities.py  live GraphQL search helper
```

To update an extra ability:

```bash
uv run python scripts/discover_extra_abilities.py pincer en
```

Then edit `kardscm/data/extra_abilities.toml`. The seed is reapplied on
`kardscm sync` and when the schema initializes after the file hash changes.

When adding a new extra ability key, update all of these together:

- `KNOWN_EXTRA_ABILITIES`
- `kardscm/data/extra_abilities.toml`
- `kardscm/locales/en.toml`
- any maintained translated locale
- tests covering storage/web filtering behavior
- README or this file if the workflow changes

## Locales

Locale files live in `kardscm/locales/*.toml`.

English is the canonical baseline. Other locale files may omit keys; missing
values fall back to English and are surfaced as warnings.

When adding or changing a locale:

1. Use `kardscm/locales/en.toml` as the schema reference.
2. Omit unknown translations instead of setting them to empty strings.
3. Run `uv run pytest tests/test_locales.py -v`.
4. If user-facing language behavior changes, update `README.md`.

## Web UI

The web UI is server-rendered FastAPI + Jinja2 + HTMX. There is no JavaScript
build pipeline.

Admin mode is intentionally separate from normal user edit mode:

- normal mode edits collection quantities only
- admin mode exposes full-field editing
- admin mode only runs on localhost
- admin mode creates a DB backup before startup
- admin routes are not registered unless `--admin` is passed

The web Sync and Export flows reuse the CLI orchestrators rather than
re-implementing them:

- `commands.fetch_and_compute_diff` performs the read-only fetch + diff
  step. `commands.apply_sync_changes` performs the DB write + report
  step. `commands.sync_collection` (the CLI orchestrator) composes both
  with the typer prompts in between.
- The web `POST /sync/start` route runs `fetch_and_compute_diff` in a
  thread, stashes the result in a per-app `dict[str, SyncSession]`, and
  renders the diff modal. `POST /sync/apply/{sync_id}` reuses the
  cached cards via `apply_sync_changes`. Sessions are evicted on apply
  or cancel; abandoned sessions die with the process.
- `GET /export/{fmt}` writes a `NamedTemporaryFile`, calls the existing
  `commands.export_collection` unchanged, and returns a `FileResponse` with a
  `BackgroundTask(os.unlink, ...)` cleanup hook. The CLI export path is
  unchanged.

All blocking work (`scrape_cards`, DB writes, file writers) goes through
`asyncio.to_thread` so the event loop stays responsive.

For UI changes, inspect the rendered page in a browser before calling the work
done.

## Release Process

The package version must match in both files:

```text
pyproject.toml
kardscm/__init__.py
```

Release checklist:

1. Update `CHANGELOG.md` with a dated release entry.
2. Bump `version` in `pyproject.toml`.
3. Bump `__version__` in `kardscm/__init__.py`.
4. Run `make check`.
5. Commit the release prep.
6. Tag with `vX.Y.Z`.
7. Push `main` and the tag.
8. Create the GitHub release from the changelog notes.

`make release` runs checks and prints this checklist. It does not tag or push.

## Documentation Maintenance

Documentation is part of the change.

Update docs in the same branch when a change affects any of these:

- user workflow or command behavior -> `README.md`
- setup, architecture, maintainer workflow, release process -> `CONTRIBUTING.md`
- agent workflow or repository rules -> `AGENTS.md` / `CLAUDE.md`
- released behavior -> `CHANGELOG.md`
- Make targets -> `README.md` or `CONTRIBUTING.md`, depending on audience

Do not leave outdated docs for a later cleanup. If a change makes a documented
statement false, update or remove that statement in the same PR.

Avoid standalone docs unless the project grows past what README and
CONTRIBUTING can reasonably hold. Historical implementation plans should not be
kept as active project documentation.

## Git Hygiene

- Keep commits focused.
- Do not commit local databases, sync reports, Playwright logs, cache folders,
  or personal test data.
- Do not revert unrelated user changes in the working tree.
- Before committing, check `git status --short` and make sure only intended
  files are staged.

Known local-only paths are ignored:

```text
collection.db
.playwright-mcp/
experiments/
test_data/
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
```
