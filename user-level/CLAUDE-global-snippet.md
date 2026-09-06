## Factory conventions (all projects)

- If the repo has a CLAUDE.md factory anchor, its authorities govern: dispatch
  from the standing lane brief, board transactions at every dispatch/landing,
  choices audit at every handback, full local verify before any push to main.
- Numbers (ADR/migration) are allocated only by the orchestrator; claim first.
- Never weaken a criterion to pass. Falsify red/green after committing.
- New test literals via secrets.token_urlsafe. Never print API keys.
- Memory: one file per durable lesson (why + how-to-apply), indexed in
  MEMORY.md; verify a memory still holds before recommending it.
- Models: the role → model → effort binding is `~/.claude/model-policy.md`
  (dated, signed, with a review date); a lane brief carries the line, the
  launcher carries the tokens as argv. Never assert a model exists or does
  not from memory or a cached catalog — check the live source; probe before
  a wave; a retired row or a revoked authorization is history, not a
  fallback; a model name is not evidence, approved deliveries are.
