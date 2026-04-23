# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-04-24

### Added
- `deck add` command supports `--update` / `-u` to raise collection
  quantities to match the deck.
- `deck add` command supports `--replace` / `-r` to overwrite an
  existing saved deck with the same name.
- `deck add` accepts multiple files; failures are batched and reported
  at the end.
- `deck delete` interactive selection with a "delete all" option.
- Whitespace normalization (`sanitize_text`) on card-title lookups so
  NBSP and double-space variants match consistently.
- `AGENTS.md` at the repo root defining agent operating rules;
  `CLAUDE.md` and `GEMINI.md` now reference it.

### Changed
- README expanded with a typical end-to-end workflow, deck commands,
  and the canonical deck TXT file format.
- Scraper now uses a static GraphQL probe (no interactive browser
  scroll required for a normal sync).

### Fixed
- Deck import correctly falls back through the exile field when a card
  is not found under the primary faction.

[Unreleased]: https://github.com/AABur/kardscm/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/AABur/kardscm/releases/tag/v0.3.0
