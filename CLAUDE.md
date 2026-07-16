@AGENTS.md

# Claude Notes

Use `AGENTS.md` as the source of truth for project rules.

Tracked Claude assets in this repository:

- `.claude/settings.json`: shared hooks and plugin settings
- `.claude/skills/check/SKILL.md`: project check helper
- `.claude/skills/gen-test/SKILL.md`: pytest generation helper

Local Claude files are ignored:

- `.claude/settings.local.json`
- `.claude/worktrees/`

Do not duplicate architecture or command references here. If project behavior,
developer workflow, or documentation policy changes, update `README.md`,
`CONTRIBUTING.md`, and `AGENTS.md` as appropriate.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (`AABur/kardscm`), accessed via the
`gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, each label string equal to its role name. See
`docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See
`docs/agents/domain.md`.
