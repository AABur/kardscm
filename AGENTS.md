# AGENTS.md

Operating instructions for coding agents working on `kardscm`.

## Non-Negotiables

- Start by reading this file, `README.md`, and `CONTRIBUTING.md`.
- Do not fabricate paths, commands, API names, versions, test results, or commit
  hashes. Read the file or run the command.
- Touch only files required by the task.
- Do not revert user changes. If the working tree is dirty, identify the dirty
  files and work around unrelated changes.
- Keep all project files in English. Chat with the user may be Russian.
- Do not publish to PyPI or add PyPI release instructions.
- Do not add generated-agent attribution such as `Co-Authored-By: Claude`.
- Do not commit local data, databases, sync reports, Playwright logs, caches, or
  personal fixtures.

## Project Identity

`kardscm` is a local-first KARDS collection and deck manager.

The product is not a generic scraper and not an LLM assistant. Scraping,
baseline drift checks, and manually curated extra abilities exist to support
the local collection/deck workflow.

## Stack

- Python 3.12
- Package manager: `uv`
- CLI: Typer
- Web UI: FastAPI, Jinja2, HTMX
- Storage: SQLite
- API access: httpx + static GraphQL shape
- Export: openpyxl, JSON

## Main Commands

```bash
make sync-dev
make test
make lint
make typecheck
make check
uv run kardscm --help
uv run kardscm web --no-browser
```

Prefer narrow tests during iteration. Run the relevant final verification before
claiming completion.

## Source Map

```text
kardscm/cli.py              Typer declarations only
kardscm/commands/           user workflow orchestration (package)
kardscm/scraping/           GraphQL fetch, normalize, API baseline drift
kardscm/storage/            SQLite schema, migrations, persistence, backups
kardscm/export/             XLSX/JSON collection and deck export
kardscm/importing/          KARDS TXT deck parser
kardscm/locales/            TOML locale loader and locale data
kardscm/web/                local FastAPI/Jinja/HTMX web UI
kardscm/data/               committed API baseline and extra-ability seed
scripts/                    maintainer helpers
tests/                      pytest suite
```

## Documentation Rules

Documentation must stay current with behavior.

When a change affects user-visible behavior, update `README.md` in the same
branch. Examples: commands, flags, install/run flow, output files, sync behavior,
web UI behavior, deck workflows, language behavior.

When a change affects development or maintenance, update `CONTRIBUTING.md` in
the same branch. Examples: architecture, module ownership, release process, API
baseline workflow, extra-ability workflow, locale workflow, Make targets.

When a change affects agent behavior, update `AGENTS.md` or `CLAUDE.md`.

When a change is released or release-worthy, update `CHANGELOG.md`.

Do not create a new `docs/` tree for ordinary project documentation. The active
project docs are `README.md` and `CONTRIBUTING.md`; agent-specific docs are
`AGENTS.md` and `CLAUDE.md`.

Two exceptions, both agent configuration rather than project documentation:
`docs/agents/` holds the per-repo settings the engineering skills read (issue
tracker, triage labels, domain-doc layout), and `docs/adr/` holds architecture
decision records written by `/domain-modeling`. Neither replaces `README.md` or
`CONTRIBUTING.md`, and ordinary project docs still must not move under `docs/`.

## Coding Rules

- Match existing style and module boundaries.
- Keep `cli.py` thin; put workflow logic in `commands/`.
- Keep DB behavior in `storage/`.
- Keep web query/filter logic in `web/queries.py`; view conversion in
  `web/translate.py`.
- Keep locale strings in `kardscm/locales/*.toml`, not in Python code, unless
  the string is not user-facing.
- Keep ability key changes synchronized across constants, locale files, seed
  data, web filters, storage tests, and docs.
- Preserve user-managed `quantity` across syncs.
- Admin mode must stay localhost-only and must keep the pre-start DB backup.

## Verification

Use the smallest meaningful verification first, then broader checks when the
change is ready.

Typical commands:

```bash
uv run pytest tests/test_<area>.py -v
uv run ruff check .
uv run mypy kardscm/
make check
```

For documentation-only changes, at minimum inspect the changed Markdown for
broken project facts and run a status/diff review. Full tests are optional
unless code, commands, or config changed.

For UI changes, verify the rendered page in a browser.

## Release Rules

Before tagging a release:

- bump `version` in `pyproject.toml`
- bump `__version__` in `kardscm/__init__.py`
- add a dated `CHANGELOG.md` entry
- run `make check`

The two version files must match the tag.
