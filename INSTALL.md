# INSTALL — agent runbook

You are an LLM agent installing the factory into the repo you are standing in.
Follow the steps in order. Everything deterministic ships in this package;
YOUR job is parameterization against the target repo's language, build chain
and domain. Where a step says TRANSLATE, produce the target repo's own
document from the package's doctrine — keep section numbering stable (lane
briefs cite §-numbers).

## Step 0 — Survey the target repo
Language/build chain, test command, lint/format, existing CI, whether a
frontend exists, whether GitHub Projects is in use. Identify the **verify
portfolio**: the set of commands that together constitute full local
verification. The factory REQUIRES one — build it if missing (a `make verify`
that runs everything and stops at the first red gate).

## Step 1 — Planning pillar
1. Copy `planning/*.md` → `docs/` and resolve every {{PLACEHOLDER}}.
2. `planning/core-model.md` + `planning/board-protocol.md` are law, not
   inspiration: the board is the planning source of truth; every dispatch and
   landing has a board transaction (see the table in board-protocol).
3. Copy `planning/lane-brief-template.md` → `.claude/templates/lane-brief.md`
   and parameterize the gate block with the repo's pregate commands.
4. Create `docs/decisions/` with `planning/NUMBERS-template.md` as the empty
   registry. ADR discipline: frontmatter `status:` + `code:` pairing; numbers
   are allocated ONLY by the orchestrator, claimed in NUMBERS, flipped to
   `landed` at landing. Wire `verification/gates/build_adr_index.py --check`
   into verify.
5. Run `harness/bootstrap_board.sh <owner> "<name>"` and write the project ID,
   Status field ID and option IDs into the repo's CLAUDE.md anchor
   (`planning/CLAUDE.md.example`).

## Step 2 — Verification pillar
1. Copy `verification/gates/*.py` → `scripts/` (note the dependency clusters
   in gates/README.md) and `gitleaks.toml.example` → repo root as
   `.gitleaks.toml`. Each script's docstring is its
   contract. Most read repo-root/`docs/` paths and port as-is. Some carry
   localized (Norwegian) output strings from the source factory — translating
   those strings is part of your adaptation; never change a gate's LOGIC while
   translating.
2. Language fit: the ruff/mypy/bandit gates are Python-specific. For other
   stacks, WRITE equivalent ratchet gates with the same contract: a baseline
   file, zero-regression enforcement, `--update` as the only path to a new
   baseline, and never lowering to pass.
3. `check_backlog.py` enforces planning discipline (specs cited-or-stamped;
   DONE rows require closing commit SHAs). `check_module_coverage.py` enforces
   ADR↔code pairing under a one-way cap. Calibrate both against the repo's
   starting point via their `--update` mechanisms — never by deleting
   assertions.
4. Read `verification/falsification.md` and apply it from day one.
5. Copy and adapt `verification/ci/*.example` → `.github/workflows/`. The
   regime is non-negotiable: full commit-SHA pinning of every action (never
   tags), secret-gated green-skip (a missing secret is a green skip with a
   ::notice, never a red), minimal `permissions:`, single-flight concurrency
   where it matters. Local verify is the gate; CI verifies additionally and
   DEPLOYS from main. `verification/ci/review-prompt.md` is the canonical
   review prompt — point the review lane at it.
6. Bind everything into `make verify`. Run it. Green before the next step.

## Step 3 — Interpretation pillar
1. Create `docs/choices/` with `interpretation/choices-ledger-README.md`. The
   choices audit is a TRANSACTION POINT: every lane handback is audited with
   the `audit-choices` skill and recorded in `docs/choices/<train>.md` BEFORE
   assembly; unsound choices are resolved before the train is built.
2. Establish the memory conventions (`interpretation/memory-conventions.md`)
   and the evaluation practice (`interpretation/evaluation-practice.md`).
3. Read `interpretation/investigation-practice.md` — instrument-first is the
   default for every debugging lane.

## Step 4 — Skills
Copy `skills/` → `.agents/skills/` and symlink `.claude/skills` to it. Verify
the hash lock (`skills-lock.json`). Write the skill-routing table into the
repo's operations doc (the template carries it).

## Step 5 — Harness
Copy `harness/launch_lane.sh` to your orchestration scratchpad. Follow
`harness/worktree-ritual.md` (worktree from a pinned SHA, symlinked
venv/env/node_modules, one lane one writer, the wrapper commits — coding CLIs
often cannot commit in linked worktrees) and `harness/report-schema.md`
(sentinel + structured report + mandatory `choices:` self-report + circuit
breakers).

## Step 6 — User level
Follow `user-level/README.md`: add the global CLAUDE snippet to the user's
`~/.claude/CLAUDE.md`, establish the memory conventions, install the
recommended user-level skills.

## Step 7 — Smoke test
1. Create one trivial board item, write a mini-spec, dispatch one lane from
   the standing brief, run the choices audit on the handback, assemble a
   single-lane train, run full verify, land, sweep the board.
2. Falsify at least one gate along the way (plant a violation, watch it go
   red, remove it). For the secret gate: random-shaped secrets on a throwaway
   branch (see verification/gates/README.md — documentation keys are
   allowlisted; the working-tree leg is advisory, history is HARD).
3. Land with `make verify && git push` — never an unconditional push after a
   verify you did not read.
A factory whose smoke test has not run is not installed — it is copied.
