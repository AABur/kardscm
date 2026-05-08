.PHONY: help sync sync-dev run sync-diff web web-admin test lint format typecheck check clean release

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

run: ## Show kardscm CLI help
	@$(UV) run kardscm --help

sync-diff: ## Preview catalog sync without modifying the database
	@$(UV) run kardscm sync --diff-only

web: ## Start the local web UI
	@$(UV) run kardscm web

web-admin: ## Start the local admin web UI with DB backup
	@$(UV) run kardscm web --admin

test: ## Run tests with pytest
	@$(UV) run pytest tests/ -v --cov=kardscm --cov-report=term-missing

lint: ## Run ruff linter
	@$(UV) run ruff check .

format: ## Format code with ruff
	@$(UV) run ruff format .

typecheck: ## Run mypy type checker
	@$(UV) run mypy kardscm/

check: format lint typecheck test ## Run all checks (requires sync first!)

release: check ## Checklist for tagging a release (runs check first)
	@echo ""
	@echo "  1. Bump version in pyproject.toml and kardscm/__init__.py"
	@echo "  2. Add a dated entry to CHANGELOG.md"
	@echo "  3. Commit: git add pyproject.toml kardscm/__init__.py CHANGELOG.md"
	@echo "             git commit -m 'chore: X.Y.Z release prep'"
	@echo "  4. Tag:    git tag vX.Y.Z"
	@echo "  5. Push:   git push origin main vX.Y.Z"
	@echo ""

clean: ## Clean cache and temporary files
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/ 2>/dev/null || true
	@echo "Cache cleaned"
