# Skill attribution

The vendored skills derive from two MIT-licensed open-source sets, plus
factory-specific additions:

- **dzhng/skills** (MIT) — the factory-loop set (audit-choices, write-spec,
  implement-spec, explore-unknowns, code-review/review/refactor-clean,
  write-docs, write-tests, audit-performance, eli5, screenshot skills,
  write-skills/eval-skills, and more). Origin recorded per skill in
  `skills-lock.json`; upstream commit refs were NOT recorded at vendoring
  time, so the lock is a content digest (what shipped), not a fetchable pin.
  Verify with `python3 skills/verify_skills_lock.py --check`; falsified by
  `skills/tests/test_skills_lock.sh`.
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
- `independent-lane-review/SKILL.md` and `lane-reviewer.md` (factory
  addition): the panel's models come from the operator's dated policy
  (`harness/model-policy.md`), not from a source-factory roster table with
  pinned model names (removed 2026-09-06).
- `ROUTING.md` (this directory): the skill-routing table by factory step,
  the home INSTALL step 4 translates from.

Both upstream licenses permit redistribution with attribution; retain this
file and the lock file when copying the skill set onward.
