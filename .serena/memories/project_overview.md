# Project Overview

- Purpose: Scrape the KARDS card collection website and export card data in multiple languages and formats (XLSX/CSV/JSON).
- Tech stack: Python 3.12+, uv for dependency management, Playwright for browser automation, openpyxl for Excel output, pytest/pytest-cov/pytest-asyncio for testing, ruff for lint/format, mypy for type checking.
- Entrypoint: `kards_final_scraper.py` (CLI script + core export logic).
- Structure:
  - `kards_final_scraper.py` main scraper and export functions.
  - `tests/` pytest suites (`test_cli.py`, `test_exporters.py`, `test_language_extraction.py`).
  - `pyproject.toml` tool config (ruff, mypy, pytest) and dependencies.
  - `Makefile` standard dev commands.
  - Output examples at repo root (e.g., `kards_cards_*.xlsx/csv/json`, `kards_collection_example.xlsx`).
- Platform: Darwin (macOS).