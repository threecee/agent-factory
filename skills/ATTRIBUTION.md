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
  - The guard dispatcher, its shared primitives and the three example
    rules under `harness/guards/` are adapted from that factory's guard
    dispatcher and rule set (wave 1 and 2, 2026-09); the adaptation makes
    imports package-relative, replaces every gate name, CLI name, port
    range, path, identity and Norwegian string with the parameters in
    `../harness/guards.md` §8, drops the fixture library and pytest suite
    in favour of `guard_dispatch.py falsify` and the shell test, and keeps
    the semantics verbatim: fail-open on a crashing rule, four logged
    switch sources, denial reserved for hard forms.
  - `verification/protections/` (the git-hook driver and shims, the status
    poster, the ruleset bootstrap, the CI signal), the rule modules
    `landing`, `pre_push`, `commit_msg`, `pre_commit` and `closeout` under
    `harness/guards/rules/`, and the gates `check_landing_closeout`,
    `check_choices_protocol` and `check_gate_weakening` are adapted from
    that factory's wave-2 guards; the adaptation moves the ruleset payload
    into `verification/ci/ruleset-main.json.example`, sets the strict
    up-to-date policy and admits a pull-request merge beside the direct
    push, replaces the per-SHA state file with a status read-back, lints the
    package's ledger schema instead of the reference's section shape, reads
    every check as contains-not-equals, and removes every repository name,
    port, identity, issue reference and non-English string.

- **Harness Kit** (`development-harness`, version 3.0.0 per its package
  manifest, MIT per that manifest; the copy read on 2026-09-06 carried no
  LICENSE file or copyright line) — read, not vendored. The change-kind
  line with its escalate-automatically / never-demote-silently rule
  (`../planning/execution-contract.md` §9) and the diff-triggered-legs
  placeholder (`../planning/lane-brief-template.md` §4) were prompted by
  reading it. No text was borrowed; every sentence here is a restatement.
  The kit deliberately does not adopt its path-tier table, merge-policy
  columns, phase write guard, tier-gated review agent, type-lens gate,
  skills registry or custom-workflow triggers — the README's provenance
  section lists them so a later change does not re-import them. Should a
  sentence ever be borrowed, this entry must first carry the upstream
  notice, reconstructed from the upstream source.

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
