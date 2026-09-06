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

Factory adaptations to upstream skill text (recorded here so a re-vendoring
from upstream does not silently drop them):

- `audit-choices/SKILL.md`: a stable choice **ID** as the first ledger field;
  a handback digest ranked as input, not boundary; the rule that the
  scenario is stored beside the ledger (never a scratchpad path) and that an
  amended verdict keeps its ID. Home of the protocol:
  `interpretation/choices-ledger-README.md`.
- `refactor-clean/SKILL.md`: consumers include text readers in other
  languages, path-keyed tool baselines and name-patching tests; the
  consumer inventory and live-versus-historical rule live in
  `interpretation/investigation-practice.md`; a moved line is a new finding
  to a path-keyed baseline (fix code, never the baseline); the line count is
  a signal, the consumer surfaces are the verdict.

Both upstream licenses permit redistribution with attribution; retain this
file and the lock file when copying the skill set onward.
