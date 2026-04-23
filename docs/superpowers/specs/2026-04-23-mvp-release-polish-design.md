# P1: MVP Release Polish — Design

**Status:** approved, ready for implementation plan
**Date:** 2026-04-23
**Branch:** `feat/rules-scrape` (to be renamed or branched for release work)

## Context

`kardscm` currently ships a complete deck/collection workflow: sync cards from
the official KARDS site, export to XLSX/CSV/JSON, update quantities from an
edited XLSX, and add/import/delete/export decks from the KARDS client TXT
format. Tests cover the main paths. The project has been developed
incrementally to version 0.2.0 and is functional enough for real daily use.

It is not yet positioned as a public tool. The GitHub repo has no description
or topics, no releases, no CI, no changelog, and no visual demo. A player
landing on the repo would not quickly understand what the tool does or how
mature it is.

The goal of P1 is to freeze the current feature set as a public MVP and
present it professionally so that a post on r/kards can reasonably point
players to the repo without further qualification.

## Non-goals

- New features (nerf/buff handling → P2, subtypes → P3, rules skill → P4)
- **PyPI publishing — explicitly out of scope, now and forever.** Users who
  want the tool install it from GitHub. This is a permanent project policy;
  it must be documented in the README.
- Reddit post draft (separate step after release)
- Web UI or LLM tooling (track A / track B, out of scope here)

## Scope — release checklist

### Repo metadata

- **GitHub description:** one-line summary, ~120 chars
- **GitHub topics:** `kards`, `kards-ccg`, `card-game`, `wwii`, `python`,
  `cli`, `sqlite`, `playwright`, `collection-manager`, `deck-manager`
- **Homepage URL:** point to repo itself (no separate site)

### Versioning

- Bump `pyproject.toml` version `0.2.0` → `0.3.0`
- `classifiers`: keep `Development Status :: 4 - Beta`
- Git tag `v0.3.0` on the release commit
- GitHub Release `v0.3.0` with notes pulled from CHANGELOG

### CHANGELOG.md

- Format: Keep a Changelog + SemVer
- First entry: `[0.3.0] - 2026-04-23`
  - `### Added` — public MVP scope, `deck add` with `--update`/`--replace`,
    `deck delete`, sanitize_text whitespace normalization, AGENTS.md
  - `### Changed` — README expanded with typical workflow
- Empty `[Unreleased]` section at the top
- Bottom: compare-URL links to GitHub

### README

- **Badges** (top, under title):
  - License: MIT
  - Python: 3.12+
  - CI: tests badge (once workflow exists)
  - Repo version (auto from releases)
- **Install section** must state clearly: install from GitHub only, no PyPI
  now or in future. Show the `git clone` path (canonical) and optionally a
  `pipx install git+...` one-liner for users who prefer an isolated env.
  Example block to include in the README:

  ```markdown
  ## Installation

  `kardscm` is distributed **only from GitHub**. It is not and will not be
  published to PyPI — clone the repo and run it via `uv`.

  ```bash
  git clone git@github.com:AABur/kardscm.git
  cd kardscm
  make sync
  ```

  Or, for an isolated install without cloning:

  ```bash
  pipx install git+https://github.com/AABur/kardscm.git
  ```
  ```
- **Asciinema demo** embedded near top: short session
  `sync → export → deck add → deck export`
  - Record via `asciinema rec`, host locally in `docs/demo.cast`
  - Embed via `asciinema.org` upload or asciicast SVG badge
- Keep existing sections (Features, Requirements, Installation, Usage,
  Typical workflow, Deck file format, Development, Notes, License)

### CI (.github/workflows/)

- Single file: `ci.yml`
- Triggers: `pull_request`, `push` to `main`
- Steps:
  1. Checkout
  2. Setup uv (`astral-sh/setup-uv@v3`)
  3. `uv sync --all-extras`
  4. `uv run ruff check .`
  5. `uv run ruff format --check .`
  6. `uv run mypy kardscm/`
  7. `uv run pytest`
- Python 3.12 only (matches `requires-python`)
- Ubuntu runner (Playwright browsers: install `chromium` via
  `uv run playwright install --with-deps chromium` before tests that need it,
  or skip browser tests in CI — evaluate which tests actually require it)

### Legal / community files

- `LICENSE` — already present (MIT)
- `CONTRIBUTING.md` — already present
- `CODE_OF_CONDUCT.md` — **not required** for MVP; skip
- Issue/PR templates — **not required** for MVP; skip

### Release sequence

1. Write CHANGELOG entry for 0.3.0
2. Bump version in `pyproject.toml`
3. Add CI workflow, verify green
4. Record asciinema demo, embed in README
5. Add README badges
6. Set GitHub description + topics (via `gh repo edit`)
7. Commit on main: `chore: prepare 0.3.0 public release`
8. Tag `v0.3.0`, push tag
9. Create GitHub Release via `gh release create v0.3.0 --notes-from-tag`

## Verification

Each item has a concrete check:

- [ ] `gh repo view AABur/kardscm --json description,repositoryTopics`
      returns non-empty
- [ ] `grep -c 'shields.io' README.md` ≥ 3
- [ ] `ls docs/demo.cast` exists or README contains asciicast embed
- [ ] `.github/workflows/ci.yml` exists, GitHub Actions shows green run
- [ ] `cat CHANGELOG.md | head -1` is `# Changelog`
- [ ] `grep '^version = "0.3.0"' pyproject.toml` matches
- [ ] `git tag --list v0.3.0` returns `v0.3.0`
- [ ] `gh release view v0.3.0` returns the release
- [ ] `make check` passes locally before tagging

## Open implementation questions

- **Asciinema host:** upload to asciinema.org (public, requires account) or
  self-host the `.cast` file in the repo + use `<asciinema-player>` embed?
  Self-host is more portable and has no third-party dependency. Decision:
  self-host, commit `docs/demo.cast`, reference from README via an
  `<img src="...svg">` or a plain code block preview — final choice to be
  made during implementation when the recording is in hand.
- **Playwright in CI:** several tests mock Playwright. A smoke test that
  hits the real site from CI would make the release more trustworthy but
  adds flake. Decision: skip live-network tests in CI for now, run locally
  before tagging.

## Branch strategy

Current branch `feat/rules-scrape` was created for rules work but P1 is now
priority. Options:

- Rename `feat/rules-scrape` → `chore/0.3.0-release`: loses the pending
  rules-sync work context
- Create new branch `chore/0.3.0-release` off `main`, leave
  `feat/rules-scrape` dormant for P4: preserves rules context

Decision: create `chore/0.3.0-release` off `main`. Rules-sync work resumes
later on `feat/rules-scrape` for P4.
