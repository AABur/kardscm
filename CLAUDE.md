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
