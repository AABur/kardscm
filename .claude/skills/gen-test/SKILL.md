---
name: gen-test
description: Generate pytest tests following project patterns (pytest-cov, pytest-asyncio)
---

# Generate Tests

Generate pytest tests for the specified module or function, following existing project patterns.

## Instructions

1. **Read the target module** specified by the user argument (e.g., `/gen-test kardscm.storage`)
2. **Read 1-2 existing test files** from `tests/` to understand patterns:
   - Import style: `from kardscm.<module> import <functions>`
   - Docstrings: first line describes test purpose
   - Fixtures: use `tmp_path` for file/DB operations
   - Type hints on all test functions (`-> None`)
   - Naming: `test_<function_name>_<scenario>`
3. **Generate tests** in `tests/test_<module_name>.py`:
   - One test per public function/method minimum
   - Cover happy path + edge cases
   - Use `tmp_path` fixture for any file/DB operations
   - Mock external dependencies (Playwright, network) with `unittest.mock`
   - Add type hints to all test functions
4. **Run tests** with `uv run pytest tests/test_<module_name>.py -v` to verify they pass
5. **Fix any failures** before presenting the result

## Patterns to Follow

```python
"""Tests for <module description>."""

from pathlib import Path

import pytest

from kardscm.<module> import <functions>


def test_<function>_<scenario>(tmp_path: Path) -> None:
    """<What this test verifies>."""
    # Arrange
    ...
    # Act
    result = <function>(...)
    # Assert
    assert result == expected
```

## Do NOT

- Add unnecessary dependencies
- Test private functions (underscore-prefixed)
- Skip running the tests
