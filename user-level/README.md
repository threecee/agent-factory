# User-level installation (~/.claude)

So the factory works from ANY checkout on the machine:

1. **Global CLAUDE snippet:** append `CLAUDE-global-snippet.md` to
   `~/.claude/CLAUDE.md`.
2. **Memory conventions:** the agent's per-project memory directory follows
   `../interpretation/memory-conventions.md` (MEMORY.md index + one file per
   fact). Nothing to install — it is a convention the snippet establishes.
3. **User-level skills:** copy the skills your user should have everywhere
   (recommended minimum: `audit-choices`, `eli5`, `write-spec`,
   `systematic-debugging`, `verification-before-completion`) from `../skills/`
   to `~/.claude/skills/`. Repo-level installs cover the rest.
