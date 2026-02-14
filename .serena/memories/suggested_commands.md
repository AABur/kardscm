# Suggested Commands

## Setup / Dependencies
- `uv sync` or `make sync` — install runtime deps + Playwright Chromium.
- `uv sync --all-extras` or `make sync-dev` — install dev deps.

## Run
- `uv run python kards_final_scraper.py` — run scraper with defaults.
- `make run`, `make run-en`, `make run-json` — convenience targets.

## Quality / Tests
- `make format` — ruff format.
- `make lint` — ruff lint.
- `make typecheck` — mypy.
- `make test` — pytest + coverage.
- `make check` — format + lint + typecheck + test.
- `uv run pytest tests/ -v --cov=. --cov-report=term-missing` — direct pytest.

## Cleanup
- `make clean` — remove caches (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`).

## Common shell / git (macOS/Darwin)
- `ls`, `cd`, `rg`, `find`, `cat`, `pwd`.
- `git status`, `git diff`, `git add -p`, `git commit -m "type: message"`, `git checkout -b <branch>`.