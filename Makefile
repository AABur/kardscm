.PHONY: help sync test lint format check run-sync run-update run-export-json run-export-csv run-export-xlsx run-import-deck run-export-deck-xlsx run-export-deck-json clean

.DEFAULT_GOAL := help

UV := uv

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

sync: ## Sync basic dependencies only
	@echo "Syncing dependencies..."
	@$(UV) sync
	@echo "Installing Chromium for Playwright..."
	@$(UV) run python -m playwright install chromium
	@echo "Dependencies synced successfully!"

sync-dev: ## Sync all dependencies including dev tools
	@echo "Syncing all dependencies (including dev tools)..."
	@$(UV) sync --all-extras
	@echo "Installing Chromium for Playwright..."
	@$(UV) run python -m playwright install chromium
	@echo "All dependencies synced successfully!"

test: ## Run tests with pytest
	@$(UV) run pytest tests/ -v --cov=kards --cov-report=term-missing

lint: ## Run ruff linter
	@$(UV) run ruff check .

format: ## Format code with ruff
	@$(UV) run ruff format .

typecheck: ## Run mypy type checker
	@$(UV) run mypy kards/

check: format lint typecheck test ## Run all checks (requires sync first!)

run-sync: ## Sync cards into SQLite
	@$(UV) run python -m kards sync

run-update: ## Update card quantities from XLSX file
	@$(UV) run python -m kards update --file kards_cards_ru.xlsx

run-export-xlsx: ## Export cards to XLSX
	@$(UV) run python -m kards export --format xlsx --file kards_cards_ru.xlsx

run-export-csv: ## Export cards to CSV
	@$(UV) run python -m kards export --format csv --file kards_cards_ru.csv

run-export-json: ## Export cards to JSON
	@$(UV) run python -m kards export --format json --file kards_cards_ru.json

run-import-deck: ## Import deck from TXT file
	@$(UV) run python -m kards deck import --file $(FILE)

run-export-deck-xlsx: ## Export deck as sheet in existing XLSX
	@$(UV) run python -m kards deck export --format xlsx --file kards_cards_ru.xlsx

run-export-deck-json: ## Export deck to JSON file
	@$(UV) run python -m kards deck export --format json --file deck.json

clean: ## Clean cache and temporary files
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/ 2>/dev/null || true
	@echo "Cache cleaned"
