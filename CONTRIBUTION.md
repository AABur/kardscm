# Contributing to KARDS Scraper

## Development Rules

### Python Code Style
- Use Python 3.12+ features
- Follow PEP 8 style guide with `ruff` formatter
- Line length: 100 characters maximum
- Use type hints on all function definitions

### Code Organization
- Avoid OOP overkill - use functional approach where possible
- Keep functions small and focused (single responsibility)
- Prefer simple functions over abstract base classes
- Don't create unnecessary abstractions for one-time operations

### Imports
- Use `from typing import ...` for type hints
- Order imports: standard library → third-party → local
- Avoid wildcard imports (`from module import *`)

### Testing with pytest
- Test file naming: `tests/test_<module_name>.py`
- Test function naming: `test_<function_name>_<scenario>()`
- Use fixtures for setup/teardown
- Aim for 80%+ code coverage

Example test structure:
```python
# tests/test_exporters.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_data():
    """Fixture providing test data."""
    return {"test": "value"}

def test_export_creates_file(sample_data, tmp_path):
    """Test that export creates output file."""
    output = tmp_path / "output.xlsx"
    export_function(sample_data, str(output))
    assert output.exists()
```

### Type Checking with mypy
- All functions must have type hints
- Run `make typecheck` before committing
- Use `dict[str, str]` instead of `Dict[str, str]` (Python 3.9+)
- Use `list[dict]` instead of `List[Dict]`

Example:
```python
def extract_field(data: dict[str, str], key: str) -> str:
    """Extract field value with type hints."""
    return data.get(key, "")
```

### Logging
- Use `logging` module, not print statements
- Get logger: `logger = logging.getLogger(__name__)`
- Log levels: `debug` (detailed), `info` (progress), `warning` (issues), `error` (failures)

### Error Handling
- Catch specific exceptions, not bare `except:`
- Log exceptions with `logger.error(f"...", exc_info=True)`
- Validate input at system boundaries (user input, external APIs)
- Trust framework and internal code guarantees

### Git Commit Messages
Format: `type: description`

**Commit types:**
- `feat:` - New feature or functionality
- `fix:` - Bug fixes
- `docs:` - Documentation updates
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring without feature changes
- `config:` - Configuration changes (linting, build tools)
- `chore:` - Maintenance tasks, dependency updates

**Rules:**
- NEVER include "Generated with Claude Code"
- Use present tense, imperative mood
- Keep first line under 50 characters when possible
- Focus on WHAT and WHY, not HOW

Examples:
- `feat: add multi-language support with 12 languages`
- `feat: add export functions for csv and json formats`
- `fix: handle missing translations with fallback logic`
- `test: add unit tests for language extraction`
- `docs: update README with CLI usage examples`

### Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/language-support
   ```

2. **Make changes**
   - Write tests first (TDD approach when possible)
   - Keep commits atomic and focused
   - Format and lint frequently

3. **Quality checks**
   ```bash
   make format    # Format code
   make lint      # Check style
   make typecheck # Run type checker
   make test      # Run tests
   make check     # Run all checks
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: add language support"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/language-support
   ```

### Code Review Checklist

- [ ] Code follows style guide (run `make check`)
- [ ] All functions have type hints
- [ ] Tests added for new functionality
- [ ] Test coverage maintained or improved
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No hardcoded values or magic numbers
- [ ] Error handling for edge cases

### Architecture Principles

1. **Simplicity over complexity**
   - Three similar lines of code is better than premature abstraction
   - Don't create helpers for one-time operations
   - Avoid feature flags unless necessary

2. **No backwards-compatibility hacks**
   - Delete unused code completely
   - Don't rename with `_` prefix for "removal"
   - Don't add `// removed` comments

3. **Input validation**
   - Validate at system boundaries (user input, APIs)
   - Trust internal code and framework guarantees
   - Don't add fallbacks for impossible scenarios

4. **Functional approach**
   - Prefer functions to classes when possible
   - Keep state immutable or clearly managed
   - Use dataclasses for simple data structures

## Setup Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install development dependencies
make install

# Run checks
make check
```

## Resources

- [ruff documentation](https://docs.astral.sh/ruff/)
- [mypy documentation](https://mypy.readthedocs.io/)
- [pytest documentation](https://docs.pytest.org/)
- [PEP 8 style guide](https://pep8.org/)
