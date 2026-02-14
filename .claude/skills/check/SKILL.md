---
name: check
description: Run full project check (ruff format, ruff check, mypy, pytest) and analyze results
---

# Full Project Check

Run all project quality checks and analyze results.

## Instructions

Run the following commands sequentially and analyze output:

1. **Format**: `uv run ruff format .`
2. **Lint**: `uv run ruff check .`
3. **Type check**: `uv run mypy kardscm/`
4. **Tests**: `uv run pytest tests/ -v --cov=kardscm --cov-report=term-missing`

## Output Format

After running all checks, provide a summary:

```
## Check Results

| Check      | Status | Issues |
|------------|--------|--------|
| Format     | ...    | ...    |
| Lint       | ...    | ...    |
| Type check | ...    | ...    |
| Tests      | ...    | ...    |
```

If there are failures, list specific issues with file:line references.

## Important

- Run ALL checks even if earlier ones fail
- Do NOT auto-fix issues unless the user explicitly asks
- Report coverage percentage from pytest output
