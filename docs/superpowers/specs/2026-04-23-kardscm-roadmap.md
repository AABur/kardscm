# kardscm Roadmap

**Status:** draft for discussion
**Date:** 2026-04-23

This document lays out the full plan for `kardscm`: the public MVP release
(P1–P4), the two development branches after MVP (A — WebUI, B — private
LLM deck helper), and the promotion plan. P1–P4 happen on this repository
sequentially. Tracks A and B are independent and can run in parallel once
MVP is out.

## Guiding principles

- **Public part must be usable as-is** without LLM knowledge. The tool
  does deterministic collection/deck work; it is not gated on AI.
- **LLM-adjacency is intentional but optional.** The data exported by the
  tool is shaped so that someone who wants to feed it to an LLM (deck
  building, advice) can do so without extra processing. That is all the
  public tool needs to promise.
- **Public vs private split is explicit.** Anything that depends on the
  user's personal taste, a paid API key, or a private prompt lives in
  track B and stays off GitHub.
- **No PyPI, ever.** Install path is `git clone` + `uv`, optionally
  `pipx install git+...`. Documented in README.

---

## P1 — MVP public release

**Goal:** ship `0.3.0` as a polished public repository that a player
landing on from Reddit would consider usable and trustworthy.

See [`2026-04-23-mvp-release-polish-design.md`](2026-04-23-mvp-release-polish-design.md)
for the detailed spec. Summary of work:

1. Bump `pyproject.toml` version 0.2.0 → 0.3.0.
2. Create `CHANGELOG.md` in Keep-a-Changelog format, first entry `[0.3.0]`.
3. Add README badges (license, Python, CI once workflow exists).
4. Rewrite README install section to state "GitHub only, no PyPI, ever"
   and show both `git clone` and `pipx install git+...`.
5. Record asciinema demo of `sync → export → deck add → deck export`,
   commit to `docs/demo.cast`, embed in README.
6. Add `.github/workflows/ci.yml` running ruff + mypy + pytest on
   `pull_request` and `push` to `main`. Python 3.12 only, Ubuntu.
7. Verify `make check` green locally.
8. Create branch `chore/0.3.0-release` from current `main`.
9. Commit all of the above. Open PR, merge.
10. On `main` after merge: tag `v0.3.0`, push tag, run `gh release create`
    with notes pulled from CHANGELOG.
11. `gh repo edit` to set description and topics.

**Exit criterion:** `gh release view v0.3.0` succeeds; repo shows
description + topics; CI is green; README has working badges and demo.

---

## P2 — Nerf/buff handling

**Goal:** when a card's stats change on the official site (balance patch),
the tool must help the user see what changed and keep their collection
data consistent.

Current behavior: `sync` upserts cards by `cardId`. If `kredits` or text
changed, the DB row is overwritten silently. The user has no audit trail.

### Questions to resolve before design

- Is the right artifact a **diff report** after sync (like `git status`
  for the card catalog)?
- Should old card states be archived in the DB, or is a single-run diff
  (comparing pre-sync and post-sync rows) enough?
- Does the diff touch any export? E.g. an additional XLSX sheet
  "changed-since-last-sync" useful for deck review?
- Should the user be warned if a card in their saved deck got nerfed
  (`deck add` / `deck export` shows a flag)?

### Sketch

- Add `card_history` table: on sync, before upsert, write a row with
  `cardId`, old stats, and `archived_at`. No automatic pruning — it is
  just a log.
- Extend `sync` command to print a compact diff at the end: "N cards
  changed: M buffs, K nerfs, L text updates". Full report written to
  `docs/sync-diff-<timestamp>.md`.
- Optional `--diff-only` flag on `sync` to run the report without
  touching the DB (dry-run style).

### Exit criterion

User runs `kardscm sync` after a patch day, sees exactly which cards
changed, and can grep deck files against the diff.

---

## P3 — Implicit abilities / subtypes

**Goal:** support filtering and grouping by subtypes like Naval, Alpine,
Infantry, Armor. These are not in `attributes` the same way Blitz/Fury
are; they are semantic card types that matter for deck archetypes
("Naval deck", "Alpine deck").

### Questions to resolve before design

- Where do subtypes live in the API response? Are they a dedicated field
  or implicit in the card's `type` / `tags` / `title`?
- Are subtypes language-agnostic? (Likely yes — they are structural
  tags, not translated names.)
- What does the user actually want to do with them:
  - Filter export by subtype? (`kardscm export --subtype naval`)
  - Group by subtype in XLSX sheets?
  - See them alongside abilities in the existing export?

### Sketch

- Investigate one sync response to locate subtype data.
- Add `subtype` column to the DB schema (or parse it from existing JSON).
- Extend exporters: show subtype in its own column; add `--subtype`
  filter.
- Extend `LanguageConfig` with `subtype_names` mapping if subtypes need
  display translation.

### Exit criterion

`kardscm export --subtype naval -f xlsx -o naval.xlsx` produces a file
containing only Naval cards.

---

## P4 — Rules sync skill

**Goal:** maintainable Markdown knowledge base of current KARDS rules,
mechanics, and card synergies, built by an AI agent from kards.com news.

Fully designed. See
[`2026-04-23-rules-sync-skill-design.md`](2026-04-23-rules-sync-skill-design.md).

Implementation steps at a high level:

1. Scaffold `.claude/skills/rules-sync/` with `SKILL.md`, `patterns.yaml`,
   `synthesis.md`.
2. Author the English-language SKILL.md with Haiku 4.5 default and a note
   advising Sonnet 4.6 for better synthesis.
3. Populate `patterns.yaml` with include/exclude lists from the April 2026
   news-list analysis (already classified in this session's research).
4. Author `synthesis.md` with per-file rules for `current/mechanics.md`
   etc.
5. First dry-run: invoke the skill, inspect generated `docs/rules/`,
   iterate on synthesis prompts until output is clean.
6. Commit skill + initial `docs/rules/` snapshot.
7. Document in README: "for LLM-adjacent users, run the `rules-sync`
   skill to materialize a rules knowledge base".

### Exit criterion

`docs/rules/current/*.md` is checked in, human-readable, and references
sources. `docs/rules/manifest.yaml` is stable across a no-change re-run.

---

## Promotion

After P1 is merged and tagged, announce on community channels. Keep it
short and factual.

### Reddit — r/kards

- Single post: "KARDS Collection Manager — an open source CLI for
  syncing your collection and decks"
- Body: what it does (3 bullets), install command, link to repo, link
  to README demo.
- Disclose: written by a fan, no affiliation with 1939 Games.
- Do not advertise LLM plans. The tool stands on its own.
- Title must not be clickbait. Something like: "I built a CLI to
  manage my KARDS collection and decks — open source, feedback
  welcome".
- Reply to first few comments promptly; ignore trolls.

### Discord — discord.gg/kards

- Post in a `#community-projects` or equivalent channel if one exists.
  If not, post in general with a one-liner and a link; do not repeat.
- Shorter message than Reddit — Discord audience scrolls faster.

### Steam Community group — KARDSccg

- Optional, low priority. If there is a community project thread,
  cross-post. Otherwise skip.

### VK (ru-audience) — vk.com/kards_ru

- Optional. Write a separate short Russian-language post. Content is
  the same: link + 3 bullets.

### Draft location

Once ready: `docs/promotion/reddit-post.md`,
`docs/promotion/discord-post.md`, `docs/promotion/vk-post.md`. Not part
of P1; write when the repo is live.

### Timing

Post within 24–48 hours of the `v0.3.0` release, while the repo is
visibly fresh.

---

## Track A — Local Web UI (public, future)

**Goal:** a browser-based UI for sorting, filtering, and composing decks
with direct export to KARDS client format. Covers functionality the
official deck builder is missing (e.g. filter by ability, filter by
subtype, filter by nation × subtype intersection).

This is a **significant** undertaking and its own discussion. Captured
here only to keep the roadmap honest.

### Shape (tentative)

- Local app — no server, no account. Runs against the same
  `collection.db`.
- Read-only for catalog, read/write for decks.
- Export deck directly as the KARDS `.txt` format that `kardscm deck
  import` accepts.
- Tech choice open: FastAPI + React? Flask + htmx? Tauri? Needs its
  own brainstorm.

### When to start

After P1–P4 are done on the CLI side, and only if demand from the
Reddit post or personal use indicates the CLI is limiting.

---

## Track B — LLM deck helper (private, self-use only)

**Goal:** LLM-driven deck building and advice tailored to the current
metagame. For personal use, not public.

### What "private" means

- Not committed to this repo. Lives in a sibling directory or a private
  repo.
- Uses this tool's outputs as inputs: collection XLSX/JSON,
  `docs/rules/current/*.md`, card catalog DB.
- May require an Anthropic / OpenAI API key and a paid plan. Cost is
  per user, not borne by the project.

### Shape (tentative)

- Prompt templates that take:
  - Current meta description (from `docs/rules/current/balance.md`,
    `archetypes.md`, `mechanics.md`).
  - User's collection (XLSX export).
  - User's preferences and play style (free-text input).
- Outputs a deck in KARDS TXT format that `kardscm deck add` can
  consume.
- Iteration loop: LLM proposes deck → user plays → reports results →
  LLM adjusts. Journal kept as Markdown.

### "Fine-tuning on current metagame"

Strictly speaking this will not be fine-tuning — it will be
context-augmented prompting (RAG-style), with `docs/rules/current/`
plus a curated set of tournament deck lists as the context pack. Real
fine-tuning is out of scope until the context-prompting approach hits
a ceiling.

### When to start

After P4 is complete — the rules knowledge base is the foundation.

---

## Dependency graph

```
P1 (MVP release)
   ↓
P2 (nerf/buff diff)
   ↓
P3 (subtypes)
   ↓
P4 (rules sync skill)
   ↓
┌──────────┴──────────┐
↓                     ↓
Track A (Web UI)      Track B (LLM helper)
(public, kardscm fork (private, separate repo
 or feature branch)    or sibling dir)
```

Tracks A and B can run in parallel after P4. P1–P4 must be sequential
because each leans on the prior: diff needs schema stability (P1),
subtypes need diff semantics clean (P2), rules skill uses full
collection context including subtypes (P3).

## Open questions / for discussion

- **P2 nerf/buff:** is the diff report valuable enough to justify the
  `card_history` table, or is a one-shot "what changed since last
  sync" comparison (without persistence) enough?
- **P3 subtypes:** before designing, need a probe of the actual API
  response to see where subtype info lives. Should that probe happen
  as part of this brainstorm, or as the first step of P3 work?
- **Promotion timing:** post to all four channels same day, or stagger
  (Reddit first, Discord next day, VK/Steam a week later to re-surface)?
- **Track B privacy:** is a private GitHub repo fine, or should the
  artifacts live purely locally with no remote at all?
