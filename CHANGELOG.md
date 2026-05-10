# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Web UI Sync flow**: a **Sync** button in the page header opens a
  confirmation modal, runs the same fetch + diff the CLI does (with a
  spinner during the request), and shows a categorized preview (new /
  changed / reserve transitions / removed). Apply persists the
  changes and writes the Markdown diff report; Cancel leaves the DB
  untouched. Empty diffs collapse to a single "no changes" notice and
  only update `last_sync` metadata.
- **Web UI Export flow**: an **Export** button opens a format
  selector (XLSX, CSV, JSON). The browser downloads the file
  directly; the server only uses a tempfile that is cleaned up after
  the response is sent.
- New CLI helpers `commands.fetch_and_compute_diff` and
  `commands.apply_sync_changes` extracted from `sync_collection` so
  the web routes can reuse the same logic without duplicating it.
- `nav_sync`, `nav_export`, `sync_*`, and `export_*` UI strings added
  to all 12 locale TOMLs.

### Added

- **User edit mode**: in-page **Edit** toggle exposes per-card quantity editing
  with per-cell autosave. A save-confirmation modal shows a before/after diff
  with **Confirm** / **Continue editing** / **Undo** actions.
- **Admin mode** (`kardscm web --admin` / `-A`): full-field editing via a modal
  form covering stats (kredits, attack, defense, operationCost), all ability and
  extra-ability flags, categories (faction, type, rarity, set), the `reserved`
  flag, and localized title/text (active locale only). Admin routes are not
  registered at all without the flag. Mode is restricted to localhost and fails
  at startup otherwise.
- **Rarity quantity caps**: Standard 4 / Limited 3 / Special 2 / Elite 1 —
  enforced server-side on every quantity write and reflected in the HTML input
  `max` attribute.
- `RARITY_MAX_QUANTITY` constant in `kardscm.constants`.
- `kardscm/storage/backup.py`: `backup_database()` — copies the SQLite file to
  a timestamped sibling (`.bak.YYYYMMDDTHHMMSSZ`) before the admin server starts.
- Visible red admin banner in the browser UI showing the backup path.

## [0.8.0] - 2026-05-05

### Added

- **API contract drift detection**: every `sync` compares the observed GraphQL
  response shape (node keys, JSON key presence ratios, enum distinct values,
  card count) against `kardscm/data/api_baseline.json`. Deviations are written
  to `sync-schema-diff-TIMESTAMP.md` without aborting the sync.
- `kardscm baseline init` — fetch the live API and overwrite the committed
  baseline.
- `kardscm baseline accept` — promote the latest `sync-schema-observed-*.json`
  in cwd to the baseline file.

## [0.7.3] - 2026-05-05

### Fixed

- Naval extra-ability seed: populated cards from user screenshots; corrected
  several misclassified entries.

## [0.7.2] - 2026-05-05

### Fixed

- Extra-ability seed data corrections; auto-reapply seed after admin edits to
  keep data consistent.

## [0.7.1] - 2026-05-05

### Fixed

- Extra-ability seed bootstrap: seed was skipped on `init` when no flags were
  set yet; fixed to always run.

## [0.7.0] - 2026-05-05

### Added

- **Extra abilities** (`extra_ability_*` columns): manually curated boolean tags
  for cards with special roles not expressed in the official API (e.g. naval
  units). Idempotent migration adds the columns and seeds known values on schema
  init.
- WebUI: card description field included in text search.
- WebUI: ability filter added to the filters bar.

## [0.6.2] - 2026-05-04

### Added

- WebUI: full-text search extended to include the card description field.

## [0.6.1] - 2026-05-04

### Added

- WebUI: **ability filter** — checkboxes in the filters bar for each of the 17
  known abilities (Stage 3).

## [0.6.0] - 2026-05-03

### Added

- **Binary `ability_*` columns** replace the `attributes` JSON blob (Stage 2).
  Breaking schema migration: existing databases are backed up automatically and
  recreated; users must re-run `kardscm sync` after upgrading.

### Changed

- WebUI initial release moved to this version (previously mis-dated to v0.5.0 in
  the changelog stub). The web command and all its flags (`--port`, `--host`,
  `--no-browser`, translatable UI) shipped with this migration.

## [0.5.2] - 2026-05-02

### Changed

- **TOML locale system**: all per-language data extracted from Python literals to
  `kardscm/locales/*.toml`. Adding a new locale no longer requires editing Python
  source — drop a `<code>.toml` in the directory.
- `LanguageConfig` dataclass moved to `kardscm/locales/__init__.py`;
  `from kardscm.config import LanguageConfig` still works via re-export.
- **`--lang` global flag** replaces `config.ini` on every subcommand.
  12 locales: `en`, `ru`, `de`, `fr`, `it`, `es`, `pt`, `pl`, `ja`, `ko`,
  `zh`, `zh-Hant`. Unknown codes warn and fall back to English.

### Added

- `scripts/generate_locale.py`: developer tool to bootstrap a locale TOML from a
  live kards.com page.
- Non-blocking locale diagnostics: missing keys fall back to English and surface a
  warning in CLI (stderr) and web UI (yellow strip).
- Finalized locale files for `en`, `ja`, `ko`, `zh`, `zh-Hant`.

### Removed

- `config.ini`, `config.ini.example`, and the `configparser` dependency.

## [0.5.0] - 2026-04-27

### Added

- `kardscm web` subcommand: a local browser UI for the collection.
  FastAPI + Jinja2 + HTMX, server-rendered, no JS build pipeline.
  Defaults to `127.0.0.1:8765`, auto-opens the system browser.
- Filters bar (top): nation, type, rarity, set, kredits, text search,
  plus `spawnable` / `reserved` / `only owned` toggles. All filters
  combine with AND, applied instantly via HTMX partials.
- Excel-like card table with sortable columns (faction, title, type,
  rarity, set, quantity, kredits, operationCost, attack, defense).
- Card detail modal (description + image) opens on row click.
- `--port`, `--host`, `--no-browser` flags on `kardscm web`.
- Translatable UI chrome (page title, filter labels, column headers) via
  `LanguageConfig.ui_strings`.
- Visual save indicator: quantity cell flashes green for ~600 ms after
  each autosave.

## [0.4.0] - 2026-04-25

### Added

- Interactive `sync`: review and approve diffs before any DB writes.
  Four categories — new cards, changed characteristics, reserve
  transitions, removed cards — are listed and bulk-approved per
  category. Any rejection aborts the sync.
- `sync --diff-only` for a dry-run that prints the diff and writes a
  Markdown report without modifying the database.
- `sync --yes` to auto-approve every category (CI / scripting).
- `sync --diff-report PATH` to override the default report path
  (`./sync-diff-<UTC-iso>.md`).
- Reserved and spawnable cards are now included in sync; reserve
  transitions surface as a dedicated diff category.

### Changed

- `sync` no longer silently overwrites changed card characteristics.
  Cards moved to or returned from reserve are highlighted; cost,
  attack, defense, operation cost, abilities, and ability-text changes
  appear in the diff with old → new values.

## [0.3.0] - 2026-04-24

### Added

- `deck add` command supports `--update` / `-u` to raise collection
  quantities to match the deck.
- `deck add` command supports `--replace` / `-r` to overwrite an
  existing saved deck with the same name.
- `deck add` accepts multiple files; failures are batched and reported
  at the end.
- `deck delete` interactive selection with a "delete all" option.
- `AGENTS.md` at the repo root defining agent operating rules;
  `CLAUDE.md` and `GEMINI.md` now reference it.

### Changed

- README expanded with a typical end-to-end workflow, deck commands,
  and the canonical deck TXT file format.
- Scraper now uses a static GraphQL probe (no interactive browser
  scroll required for a normal sync).

### Fixed

- Card title lookups now ignore NBSP and double-space variants that
  previously caused mismatches between deck files and the database.

[Unreleased]: https://github.com/AABur/kardscm/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/AABur/kardscm/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/AABur/kardscm/compare/v0.7.3...v0.8.0
[0.7.3]: https://github.com/AABur/kardscm/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/AABur/kardscm/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/AABur/kardscm/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/AABur/kardscm/compare/v0.6.2...v0.7.0
[0.6.2]: https://github.com/AABur/kardscm/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/AABur/kardscm/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/AABur/kardscm/compare/v0.5.2...v0.6.0
[0.5.2]: https://github.com/AABur/kardscm/compare/v0.5.0...v0.5.2
[0.5.0]: https://github.com/AABur/kardscm/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/AABur/kardscm/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/AABur/kardscm/releases/tag/v0.3.0
