# Experiments

Local-only workspace for research experiments with the KARDS collection data.

## Rules

- This folder exists only on the `experiments` branch
- Never push this branch to remote (blocked by pre-push hook)
- Import from `kardscm` package freely: `from kardscm.config import ...`
- Keep experiments self-contained in subfolders
- No production code changes on this branch

## Structure

```
experiments/
├── README.md
└── <experiment_name>/
    ├── notebook.ipynb   # or script.py
    └── ...
```
