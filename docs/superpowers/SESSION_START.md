# Session Start — kardscm

Read this first when resuming work on the project.

## What this project is

`kardscm` — KARDS Collection Manager. Python 3.12 CLI that syncs the
official KARDS card catalog into SQLite, exports to XLSX/CSV/JSON,
updates quantities from edited XLSX, and saves/adds/deletes/exports
decks from the KARDS client TXT format.

Installed from GitHub only. No PyPI, ever. Public open-source tool;
private LLM-adjacent tooling lives in a separate future track.

## Where we are right now

- **Branch:** should be `main` at session start
- **Version:** `0.3.0` in `pyproject.toml`
- **Release status:** v0.3.0 not yet tagged. Phase 1 in progress
  (Task 1.1 shipped; Tasks 1.2–1.4 pending).
- **Current priority (Phase 1):** polish repo for public release

## Key files to read (in order)

1. **[`docs/superpowers/plans/2026-04-24-execution-plan.md`](plans/2026-04-24-execution-plan.md)**
   — THE plan. Check what's checked off, pick the next `[ ]` task,
   read its subtasks, start work.
2. **[`docs/superpowers/specs/2026-04-23-kardscm-roadmap.md`](specs/2026-04-23-kardscm-roadmap.md)**
   — high-level roadmap with all phases, tracks, promotion plan.
3. **[`docs/superpowers/specs/2026-04-23-mvp-release-polish-design.md`](specs/2026-04-23-mvp-release-polish-design.md)**
   — Phase 1 design spec.
4. **[`docs/superpowers/specs/2026-04-23-rules-sync-skill-design.md`](specs/2026-04-23-rules-sync-skill-design.md)**
   — Phase 4 design spec (read when Phase 4 starts).
5. **[`AGENTS.md`](../../AGENTS.md)** — project-wide agent operating
   rules. Absolute language rules, commit conventions, YAGNI, surgical
   changes. Read if unsure how to approach a task.
6. **[`CLAUDE.md`](../../CLAUDE.md)** — thin wrapper pointing to
   AGENTS.md plus project-specific structure notes.

## Non-negotiables

- **All files in English.** Code, comments, docstrings, commits, docs,
  README. No Russian anywhere in project files. Chat with the user is
  in Russian; that is the only exception.
- **No PyPI.** Ever. If asked, explain the policy and decline.
- **No `Co-Authored-By: Claude` in commits.** No `Generated with Claude
  Code` tag.
- **Conventional commits:** `type: description`, imperative, <50 chars
  subject.
- **One subtask = one commit.** One task = one PR.
- **`make check` green before every PR.**

## Quick state check

Run these to know where you are:

```bash
git branch --show-current          # expect: main
git status --short                  # expect: clean, maybe .claude/ untracked
grep '^version' pyproject.toml      # expect: version = "0.3.0" after Phase 1.1
ls docs/superpowers/plans/          # plan files
gh release list --limit 5           # expect: v0.3.0 after Phase 1.4
```

## Typical session flow

1. `git pull` on `main`
2. Read the plan file, find first unchecked task
3. Read that task's design spec (linked from plan)
4. Create the task's feature branch from `main`
5. Work subtask by subtask, one commit each
6. Check off subtasks in the plan file as you go (commit plan updates
   alongside the work)
7. `make check` before opening PR
8. Open PR, wait for CI green, merge
9. Return to `main`, pull, loop

## On rate-limit or interrupt

- Commit anything in-progress with a `WIP:` prefix
- Note the resume point in the plan file (TODO comment)
- Leave a short chat summary for the next session

## Non-goals (rejected ideas)

- PyPI publishing
- Russian-language rules output (rules content is English only)
- Auto-scheduled rules sync (user-invoked only)
- Web UI in `kardscm` itself (that is Track A, separate)
- Heavy staging/accept/discard workflow for rules (previous attempt in
  closed PR #7 — explicit lesson learned)
