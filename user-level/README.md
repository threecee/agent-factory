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
   to `~/.claude/skills/`. Repo-level installs cover the rest. The copies
   are verifiable against the package lock from any directory:
   `python3 ../skills/verify_skills_lock.py --check --root ~/.claude/skills
   --lock ../skills/skills-lock.json` reports the skills you copied as
   verified and the ones you did not as missing — read only the first kind.
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
5. **Bulk-read worker and threshold (optional pilot):** if the repo has
   bound `../harness/bulk-read-contract.md`, the worker chain, line threshold,
   path exemptions and the session disable variable are YOUR settings, set
   in your shell environment (default names `SHUNT_WORKERS`,
   `SHUNT_MIN_LINES`, `SHUNT_ALLOW`, `SHUNT_DISABLED`), never committed.
   Record the reason for each value and the date of the live probe that
   showed the worker answering (contract §3 rule 1). Registering the hook is
   a separate decision taken after the off/on pilot has numbers (§7); a
   fresh checkout registers nothing.
6. **Landing authority (optional, INACTIVE by default):** the factory grants
   no push authority by installing it. A finished train with no live ruling
   from the owner is HELD with a decision brief
   (`../planning/decision-brief-template.md`). If — and only if — the owner
   wants the lander to land verified P1 trains without a live ruling, the
   owner copies `landing-policy.example.md` to `~/.claude/landing-policy.md`,
   fills every field, sets `status: ACTIVE` and signs it. Nothing to install
   otherwise; the example stays inactive. The package hold floor
   (`landing-policy.example.md` §2 `holds:`, its one home) stops a train
   regardless of the policy.
7. **Model policy (required before the first dispatch):** copy
   `model-policy.example.md` to `~/.claude/model-policy.md` and fill every
   row you will dispatch into: the exact model id from the provider's live
   list, the invocation form, the effort token, a probe date and result,
   `valid_from` (today, never a future date), `review_by`, and your
   signature. It is a user-level file because it describes YOUR accounts and
   machine; the repo's operations doc points at it by path and never copies
   the table (`../harness/model-policy.md` §3 rule 1). The package ships no
   model names — a copy with placeholders binds nothing. Temporary
   exceptions (a quota wall, a retired provider) are `authorizations:` rows
   with an end and, when lifted early, a `revoked_at`; they never become the
   default by expiring (§6 there). Revisit the names on `review_by`; a
   policy past that date is stale, and the reading rules for a stale or
   inherited policy are §3 rule 3 and the worked example in §9.
