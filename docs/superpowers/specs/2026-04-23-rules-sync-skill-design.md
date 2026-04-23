# P4: Rules Sync Skill — Design (Deferred)

**Status:** designed, deferred until P1–P3 are complete
**Date:** 2026-04-23

## Context

KARDS game rules, mechanics, balance changes, and expansion details are
scattered across news articles on `https://www.kards.com/news`. Content
evolves: rotation policies, draft pools, and card balance are revised over
time; some news supersedes earlier news entirely (e.g. the new 2026 annual
rotation system replaces two prior rotation announcements).

A useful knowledge base for LLM-driven deck building needs (a) the current
authoritative state of each rule domain and (b) traceability to the source
article that established it, so a human can verify or an LLM can cite.

This is not a code feature: it is a maintained Markdown corpus produced by
an AI agent (Claude Code or equivalent) on demand via a skill. No Python
module is added to `kardscm`. The skill lives outside the package proper.

## Non-goals

- Python code inside `kardscm/` for rules scraping
- Automatic scheduled runs — the user invokes the skill manually
- Russian-language rules output — source content is English-only
- Coverage of non-rules content (tournaments, events, holidays, lore)

## Architecture

### Output tree

```
docs/rules/
├── README.md                 # user-facing: when to run, what's inside
├── manifest.yaml             # state: sources, hashes, classification
├── current/                  # synthesized authoritative rules
│   ├── mechanics.md
│   ├── subtypes.md
│   ├── rotation.md
│   ├── draft.md
│   ├── balance.md
│   ├── archetypes.md
│   ├── expansions.md
│   └── nations.md
├── sources/                  # archived raw Markdown of originals
│   └── YYYY-MM-DD__<slug>.md
└── superseded/               # articles that no longer apply
    └── <slug>.md
```

### Skill location

```
.claude/skills/rules-sync/
├── SKILL.md                  # frontmatter + instruction content (English)
├── patterns.yaml             # include/exclude slug patterns
└── synthesis.md              # detailed synthesis rules for each current/*.md
```

### Source files (`docs/rules/sources/*.md`)

```yaml
---
url: https://www.kards.com/news/<slug>
slug: <slug>
published: YYYY-MM-DD
fetched: YYYY-MM-DD
classification: patch-notes | balance | mechanic | subtype | rotation | draft | archetype | expansion | card-spotlight | roadmap
supersedence_type: additive | replacing | incremental
hash: sha256:<hex>
---

# <article title>
<body converted from HTML to Markdown>
```

### Superseded files

```yaml
---
superseded_by: <slug>
superseded_on: YYYY-MM-DD
reason: <one line>
---
```

### Manifest (`docs/rules/manifest.yaml`)

```yaml
version: 1
last_sync: <ISO8601>
sources:
  - slug: <slug>
    url: <url>
    published: YYYY-MM-DD
    fetched: YYYY-MM-DD
    classification: <type>
    supersedence_type: additive | replacing | incremental
    hash: sha256:<hex>
    status: active | superseded | review-needed | excluded | gone
    superseded_by: <slug>   # when status == superseded
```

Patterns live in `patterns.yaml`, separate from manifest, so humans can
edit them without touching state.

## Classification

Two-pass:

1. **Slug pattern match** against `patterns.yaml` include/exclude lists.
   Include patterns cover `*patch-notes*`, `*balance*`, `*dev-blog*`,
   `*-expansion-*`, `*-mini-set*`, `*-spoiler*`, `card-spotlight*`,
   `*-battle-ready-decks*`, `*rotation*`, `*draft*`, `*mechanic*`,
   `*subtype*`, `*-keywords*`, `*-neutral*`, `*-resistance*`,
   `*player-profile*`, `*roadmap*`, plus the static pages `how-to-play`,
   `expansions`, `kards-allegiance`. Exclude patterns cover tournaments,
   events, holidays, policy, history/lore.

2. **Review-needed gate.** Articles matching neither list are marked
   `status: review-needed` and the skill halts, showing the user the list
   and asking them to extend patterns before a re-run. Gate fires
   *before* body fetch to avoid wasted work on obvious junk.

## Supersedence

Three types, chosen from classification:

- **Additive** (mechanics, subtypes): articles accumulate. Skill scans
  the latest article body for `reworked` / `replaces` / `redesigned` and
  moves the older entry to `superseded/` when found.
- **Replacing** (rotation, draft pool): only the most recent article
  (highest `published`) is authoritative. Older ones go to `superseded/`.
- **Incremental** (balance patches): each patch is an edit diff.
  `current/balance.md` is a table `card → latest change → source`, built
  by walking patch notes in chronological order and keeping the last
  change per card. Old patches stay in `sources/`, not in `superseded/`.

## Workflow

1. Read `manifest.yaml` (or initialize empty).
2. Playwright MCP → `https://www.kards.com/news`, enumerate all articles.
3. For each article:
   a. Matched hash in manifest → skip.
   b. Matches exclude pattern → mark `excluded`, skip.
   c. Matches include pattern → fetch body, save to `sources/`, update
      manifest.
   d. Matches neither → mark `review-needed`, skip fetch.
4. Same treatment for static pages: `/how-to-play`, `/expansions`,
   `/kards-allegiance`.
5. If any `review-needed` exist, halt and report.
6. Rebuild `current/*.md` from the active `sources/` set using the
   synthesis rules in `synthesis.md`.
7. Update `last_sync` and per-source `status`/`hash` in manifest.
8. Print a summary: N new, M superseded, K review-needed.

## Error handling

- **Network or Playwright failure:** halt, leave manifest untouched.
  Re-run resumes from the same state.
- **Slug gone from live list:** mark `status: gone`, keep the source
  file. Human decides whether to delete.
- **Body hash mismatch on known slug:** overwrite the source, reclassify,
  rebuild affected `current/*.md`. Git shows the diff.
- **Conflicting balance entries:** write both with a
  `conflict: see sources <X>, <Y>` marker in `balance.md`, flag for
  human.
- **Static page rewritten:** hash mismatch → rebuild `nations.md` /
  `mechanics.md` from scratch (static pages are treated as first-class
  sources).

## Model cost

Skill runs on Claude Haiku 4.5 by default. The SKILL.md frontmatter
instructs the user that switching to Sonnet 4.6 (e.g. via `/model` in
Claude Code) produces higher-quality synthesis at higher token cost.

Rough estimate at Haiku 4.5 pricing:
- Crawl: 0 model tokens (Playwright MCP)
- Classification: ~2k input, ~500 output — negligible
- Synthesis of current/*.md from ~50 articles: ~60k input, ~10k output
- Full rebuild ≈ $0.10–0.30. Incremental (only new articles) ≈ cents.

## Dependencies

- Playwright MCP must be available in the Claude Code harness where the
  user invokes the skill.
- No Python dependency is added to `kardscm`.

## Open questions

None at design time. Implementation plan will decide concrete pattern
lists, exact `current/*.md` headings, and SKILL.md prose.
