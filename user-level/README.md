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
4. **Artifact bank root:** choose one durable directory outside every
   repository and outside every scratchpad (e.g. `~/<project>-bank/`),
   export it as `LANE_ARTIFACT_BANK` in every shell that dispatches lanes,
   so run receipts are banked as they are produced
   (`../harness/run-lifecycle.md` §9), and record it in the repo's
   operations doc per `../harness/artifact-bank.md` §10. The bank is where
   evaluation sources, run output, receipts and evidence bundles live; a
   scratchpad or a worktree is never storage. The root is a user-level
   choice because it is a property of the machine, not of the repository;
   what is banked is decided by regeneration cost, never by size.
