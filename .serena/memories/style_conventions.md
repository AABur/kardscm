# Style and Conventions

- Python 3.12+; follow PEP 8 with ruff formatting; line length 100.
- Type hints required on all functions; mypy enforces `disallow_untyped_defs`.
- Imports ordered: standard library → third-party → local; no wildcard imports.
- Prefer small, focused functions; avoid unnecessary abstractions or heavy OOP.
- Functional approach where possible; use dataclasses for simple data structures.
- Logging: use `logging` module (no print), with appropriate log levels.
- Error handling: catch specific exceptions, validate at system boundaries, avoid impossible fallbacks.
- Testing conventions: `tests/test_<module_name>.py`, `test_<function>_<scenario>()`; aim for 80%+ coverage.
- Commit messages: `type: description` (feat/fix/docs/test/refactor/config/chore), imperative tense, keep short, never include "Generated with Claude Code".