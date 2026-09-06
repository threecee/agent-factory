# Skill attribution

The vendored skills derive from two MIT-licensed open-source sets, plus
factory-specific additions:

- **dzhng/skills** (MIT) — the factory-loop set (audit-choices, write-spec,
  implement-spec, explore-unknowns, code-review/review/refactor-clean,
  write-docs, write-tests, audit-performance, eli5, screenshot skills,
  write-skills/eval-skills, and more). Pinned refs in `skills-lock.json`.
- **obra/superpowers** (MIT) — the process-discipline set (brainstorming,
  systematic-debugging, test-driven-development,
  verification-before-completion, writing-plans, worktree/parallel-agent
  skills, and more).
- Factory additions (this repo's license): independent-lane-review and
  adaptations recorded in the lock file.
- **threecee/varde** (same author; contributed under this repo's license) —
  the bounded bulk-read pilot skills `bulk-reader`, `log-triage` and
  `handback-digest`, adapted from that factory's `.claude/skills/` set. The
  adaptation replaces every repository-specific command, path, threshold,
  worker alias and model name with the parameters in
  `../harness/bulk-read-contract.md` §4; the worker runtime and the
  PreToolUse hooks were not copied — the contract describes them.

Both upstream licenses permit redistribution with attribution; retain this
file and the lock file when copying the skill set onward.
