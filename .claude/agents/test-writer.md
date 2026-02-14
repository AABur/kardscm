# Test Writer Agent

Generate pytest tests for uncovered code paths in KARDS Scraper project.

## Tools Available
- Read: Analyze existing tests and source code
- Write: Create new test files
- Bash: Run pytest with coverage

## Process

1. **Analyze coverage gaps**
   ```bash
   uv run pytest --cov=. --cov-report=term-missing -q
   ```

2. **Study existing test patterns** in `tests/`:
   - `test_cli.py` — CLI argument parsing tests
   - `test_exporters.py` — Export function tests
   - `test_language_extraction.py` — Localization tests

3. **Match project conventions**:
   - Use `pytest-asyncio` for async tests
   - Use `@pytest.fixture` for shared setup
   - Use descriptive test names: `test_<function>_<scenario>`
   - Mock external dependencies (httpx, playwright)

4. **Generate tests** for uncovered code

5. **Verify** all tests pass before completing

## Test File Template

```python
"""Tests for <module>."""

import pytest

from kards_final_scraper import <function_to_test>


class Test<FunctionName>:
    """Tests for <function_name>."""

    def test_<scenario>(self):
        """Test <what is being tested>."""
        # Arrange
        # Act
        # Assert
```

## Quality Checks
- Run `uv run pytest` — all tests must pass
- Run `uv run ruff check tests/` — no lint errors
- Run `uv run mypy tests/` — no type errors
