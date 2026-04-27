# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Inline quantity editing on each row, autosaved to the local DB on
  blur/change — replaces the `export → edit xlsx → update` cycle.
- Card detail modal (description + image) opens on row click.
- `--port`, `--host`, `--no-browser`, and `--lang` flags on
  `kardscm web`. `--lang en|ru` overrides `config.ini` for one run.
- Fully translatable UI chrome (page title, filter placeholder,
  toggle labels, modal labels, "Cost" column header) via the new
  `LanguageConfig.ui_strings` field. English remains the fallback
  when no `config.ini` is present.
- Visual save indicator: the quantity cell flashes green for ~600ms
  after each autosave so the persistence is no longer invisible.

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

[Unreleased]: https://github.com/AABur/kardscm/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/AABur/kardscm/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/AABur/kardscm/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/AABur/kardscm/releases/tag/v0.3.0
