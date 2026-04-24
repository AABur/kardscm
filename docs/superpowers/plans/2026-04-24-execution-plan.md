# kardscm Execution Plan

**Status:** in progress
**Started:** 2026-04-23
**Last updated:** 2026-04-24

This is the authoritative, cross-session execution plan. Structure:

- **Phase** = released version (tagged on GitHub). Each phase ships.
- **Task** = one feature branch, one PR. Tasks inside a phase run in
  sequence unless explicitly marked parallel.
- **Subtask** = one commit. Use conventional commit format
  (`type: description`).

Update this file as work progresses. Check off completed items. When a
phase ships, tag the release and move on.

Design specs live in `docs/superpowers/specs/`. Read the spec before
starting a task.

Legend: `[ ]` pending, `[~]` in progress, `[x]` done.

---

## Phase 1 — v0.3.0 (public MVP release)

**Design spec:** [`specs/2026-04-23-mvp-release-polish-design.md`](../specs/2026-04-23-mvp-release-polish-design.md)

**Branch strategy:** each task on its own feature branch from `main`.
Merge via PR with squash only after CI passes. Tag `v0.3.0` from `main`
after the last task is merged.

### Task 1.1 — Release prep (version + CHANGELOG + README install)

- [x] Branch: `chore/0.3.0-release-prep`
- [x] Subtask: `chore: bump version to 0.3.0`
  - edit `pyproject.toml` `version = "0.3.0"`
- [x] Subtask: `docs: add CHANGELOG.md with initial 0.3.0 entry`
  - create `CHANGELOG.md` in Keep a Changelog format
  - `[Unreleased]` header (empty)
  - `[0.3.0] - 2026-04-??` with sections Added / Changed / Fixed
  - content per roadmap: deck add `--replace`/`--update`, deck delete,
    sanitize_text whitespace normalization, AGENTS.md adoption, README
    expansion
  - bottom: compare-URL links to GitHub
- [x] Subtask: `docs: document github-only install in README`
  - rewrite Installation section per spec
  - explicit "no PyPI, ever" language
  - show `git clone` + `pipx install git+...`
- [x] PR: merge into `main`

### Task 1.2 — CI workflow

- [x] Branch: `chore/ci-workflow`
- [x] Subtask: `ci: add GitHub Actions workflow for lint and test`
  - create `.github/workflows/ci.yml`
  - triggers: `pull_request`, `push` to `main`
  - steps: checkout → setup-uv → `uv sync --all-extras --frozen` →
    `ruff check` → `ruff format --check` → `uv run mypy kardscm/` →
    `uv run pytest`
  - Python 3.12, Ubuntu runner
  - skip or mock any live-network tests
- [x] Subtask (if needed): not needed — all tests already mock network calls
- [x] PR: merge into `main`. CI green on first run.

### Task 1.3 — README badges

- [x] Branch: `docs/readme-badges`
- [x] Subtask: `docs: add license, python, CI badges to README`
  - MIT badge (shields.io)
  - Python 3.12+ badge
  - CI status badge (from workflow in Task 1.2)
- [x] PR: merge into `main`

### Task 1.4 — Tag and release (admin, no PR)

- [x] Precheck: `make check` green on `main`
- [x] `gh repo edit AABur/kardscm --description "..." --add-topic kards,kards-ccg,card-game,wwii,python,cli,sqlite,playwright,collection-manager,deck-manager`
  - description: one sentence, <120 chars
- [x] `git tag v0.3.0`
- [x] `git push origin v0.3.0`
- [x] `gh release create v0.3.0` with notes from CHANGELOG entry
- [x] Verify: `gh release view v0.3.0`, repo page shows topics

### Phase 1 exit criterion

- [x] Tag `v0.3.0` on GitHub
- [x] CI green on `main`
- [x] `gh repo view AABur/kardscm` shows description + topics
- [x] README has badges
- [x] CHANGELOG.md up to date

---

## Phase 2 — v0.4.0 (nerf/buff handling)

**Design spec:** to be written as part of Task 2.0

**Prerequisite:** Phase 1 shipped.

### Task 2.0 — Design spec

- [ ] Branch: `design/2.0-nerf-buff`
- [ ] Subtask: `docs: write design spec for nerf/buff handling`
  - new file `docs/superpowers/specs/YYYY-MM-DD-nerf-buff-design.md`
  - resolve open questions from roadmap:
    - card history table vs one-shot diff?
    - export integration?
    - deck warning on nerf?
  - single chosen approach
- [ ] PR: merge spec into `main` before implementation starts

### Task 2.1 — `card_history` table and diff computation

- [ ] Branch: `feat/card-history`
- [ ] Subtask: `feat: add card_history table to schema`
- [ ] Subtask: `feat: archive card state before upsert on sync`
- [ ] Subtask: `test: cover card_history append on changed stats`
- [ ] PR

### Task 2.2 — Diff report after sync

- [ ] Branch: `feat/sync-diff-report`
- [ ] Subtask: `feat: compute diff from card_history after sync`
- [ ] Subtask: `feat: print diff summary on sync command`
- [ ] Subtask: `feat: write full diff to docs/sync-diff-<ts>.md`
- [ ] Subtask: `test: diff with buffs, nerfs, text-only changes`
- [ ] Subtask: `docs: document diff output in README`
- [ ] PR

### Task 2.3 — `--diff-only` dry-run flag

- [ ] Branch: `feat/sync-diff-only`
- [ ] Subtask: `feat: add --diff-only flag to sync command`
- [ ] Subtask: `test: --diff-only does not touch DB`
- [ ] PR

### Task 2.4 — Release

- [ ] CHANGELOG entry `[0.4.0]`
- [ ] Version bump to 0.4.0
- [ ] Tag, release, topics update if needed

---

## Phase 3 — v0.5.0 (subtypes / implicit abilities)

**Design spec:** to be written as part of Task 3.0

**Prerequisite:** Phase 2 shipped.

### Task 3.0 — API probe + design spec

- [ ] Branch: `research/3.0-subtypes`
- [ ] Subtask: probe one sync response, document where subtype data
  lives (field in API JSON? parsed from title? separate attribute?)
- [ ] Subtask: `docs: write design spec for subtype support`
  - single chosen approach
  - DB schema change
  - CLI surface (`--subtype` flag on `export`)
  - translation strategy (if any)
- [ ] PR: merge spec into `main`

### Task 3.1 — DB schema + parser

- [ ] Branch: `feat/subtypes-schema`
- [ ] Subtask: `feat: add subtype column/field to cards schema`
- [ ] Subtask: `feat: parse subtype from API response in normalizer`
- [ ] Subtask: `test: normalizer emits correct subtype for known cards`
- [ ] PR

### Task 3.2 — Export filter and display

- [ ] Branch: `feat/subtypes-export`
- [ ] Subtask: `feat: add subtype column to XLSX/CSV/JSON export`
- [ ] Subtask: `feat: add --subtype filter to export command`
- [ ] Subtask: `test: export --subtype naval returns only naval cards`
- [ ] Subtask: `docs: document --subtype in README`
- [ ] PR

### Task 3.3 — Release

- [ ] CHANGELOG `[0.5.0]`
- [ ] Version bump
- [ ] Tag, release

---

## Phase 4 — v0.6.0 (rules sync skill)

**Design spec:** [`specs/2026-04-23-rules-sync-skill-design.md`](../specs/2026-04-23-rules-sync-skill-design.md)

**Prerequisite:** Phase 3 shipped.

### Task 4.1 — Skill scaffolding

- [ ] Branch: `feat/rules-skill-scaffold`
- [ ] Subtask: `feat: scaffold .claude/skills/rules-sync/ structure`
- [ ] Subtask: `feat: author SKILL.md frontmatter + instructions (English)`
- [ ] Subtask: `feat: populate patterns.yaml from roadmap classification`
- [ ] Subtask: `feat: author synthesis.md per-file rules`
- [ ] PR

### Task 4.2 — First dry-run and iteration

- [ ] Branch: `feat/rules-first-sync`
- [ ] Subtask: invoke skill in dev session, inspect `docs/rules/`
- [ ] Subtask: iterate on synthesis prompts until output is clean
- [ ] Subtask: `feat: commit initial docs/rules/ snapshot`
- [ ] PR

### Task 4.3 — Documentation and release

- [ ] Branch: `docs/rules-skill-readme`
- [ ] Subtask: `docs: document rules-sync skill in README`
- [ ] Subtask: `docs: add docs/rules/README.md for end users`
- [ ] Subtask: CHANGELOG `[0.6.0]`
- [ ] Subtask: version bump
- [ ] PR, tag, release

---

## Promotion (after Phase 1 ships)

**Not part of any version.** One-time activity after v0.3.0 is live.

### Task P.1 — Draft posts

- [ ] Branch: `docs/promotion`
- [ ] Subtask: `docs: draft reddit post for r/kards`
- [ ] Subtask: `docs: draft discord post`
- [ ] Subtask: `docs: draft VK post (Russian)`
- [ ] Subtask: (optional) `docs: draft steam community post`
- [ ] PR (merge drafts into main for archival)

### Task P.2 — Post

- [ ] r/kards — post within 24-48h of v0.3.0 release
- [ ] discord.gg/kards — post same or next day
- [ ] vk.com/kards_ru — post on day 2 or later
- [ ] steam (optional) — if there is a community-projects thread

### Task P.3 — Monitor

- [ ] Reply to first wave of comments within a few hours
- [ ] File any bug reports as GitHub issues
- [ ] Roll hotfixes (patch releases 0.3.1, 0.3.2 etc.) if needed

---

## Track A — Local Web UI (public, future)

**Starts:** after Phase 4 ships, and only if demand signals it.
**Scope:** see roadmap. This track requires its own brainstorm and
design cycle; no execution steps are committed here yet. Placeholder to
keep the slot reserved.

---

## Track B — LLM deck helper (private, future)

**Starts:** after Phase 4 ships.
**Scope:** see roadmap. Private repo. Does not touch `kardscm` source.
Uses `kardscm` outputs as inputs.

Placeholder. Will get its own execution plan in the private repo.

---

## Session hygiene

- Do not start a task without its design spec merged on `main`.
- Each subtask = one commit. Multiple commits per PR OK, but each must
  be independently sensible.
- Conventional commit format. Short body explaining why, not what.
- `make check` green before every PR.
- Update this file as you go: check off items, add discovered subtasks,
  note blockers.
- On rate-limit or session interrupt: commit what's done, leave a TODO
  comment, update this file with the resume point.
