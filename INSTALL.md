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
   `planning/execution-contract.md` is the one home of the measurement
   baseline and the two-round limit; the lane brief only parameterizes it
   (§8 of that file lists the parameters). Keep its section numbers —
   briefs cite them.
2. `planning/core-model.md` + `planning/board-protocol.md` are law, not
   inspiration: the board is the planning source of truth; every dispatch and
   landing has a board transaction (see the table in board-protocol). A
   ruling the owner must give is filed as a decision brief
   (`planning/decision-brief-template.md`, copied with the rest) — the owner
   reads the brief, never the conversation.
3. Copy `planning/lane-brief-template.md` → `.claude/templates/lane-brief.md`
   and parameterize: the gate block with the repo's pregate commands,
   `{{FIRST_CONTACT_STOPS}}` with the repo's guarded boundaries and number
   rules, `{{PARK_DESTINATION}}` with where parked remainders are tracked
   (a board item, or the backlog row your planning gate governs). The
   per-lane fields (task ID, round, apparatus, proof owner, attachments,
   ceiling) are filled at dispatch, never in the template.
4. Copy `planning/investigation-brief-template.md` →
   `.claude/templates/investigation-brief.md`. It is the read-only lane a
   bug goes through BEFORE it gets a fix brief when the cause is uncertain:
   pinned SHA, frozen evidence package (harness/artifact-bank.md), competing
   hypotheses, verdicts with sources, no code change. Its §8 is the boundary
   to the fix brief; do not add a mandatory investigation phase for trivial
   reproduced defects (its §0 says when).
5. Create `docs/decisions/` with `planning/NUMBERS-template.md` as the empty
   registry. ADR discipline: frontmatter `status:` + `code:` pairing; numbers
   are allocated ONLY by the orchestrator, claimed in NUMBERS, flipped to
   `landed` at landing. Wire `verification/gates/build_adr_index.py --check`
   into verify.
6. Run `harness/bootstrap_board.sh <owner> "<name>"` and write the project ID,
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
4. Read `verification/falsification.md` and apply it from day one. Rules
   §7–§9 govern root-cause reports: falsify the causal model before the fix
   (or as the fix's first red test), refute only with a source, and keep an
   unknown cause unknown. Before writing any gate over stored evidence
   (rows, snapshots, receipts) or any progress meter that survives a retry,
   read `verification/examples/identity-and-history.md` and run its script
   once (`python3 verification/examples/identity_and_history.py`, then with
   `--plant count-all`): a gate must read what the consumer reads, and is
   falsified in both directions (rules §10–§12).
5. Read `verification/evaluation-readiness.md`. TRANSLATE its §2.1 check
   families into the repo's own pre-flight smoke (stable check ids, a
   time budget, a receipt in the §4 shape) and write, into the repo's
   operations doc, which checks each evaluation type REQUIRES. Keep the
   three types apart from day one: pre-flight smoke, offline functional
   trial (fakes allowed, a verify leg), AI evaluation (real roles, never a
   verify leg). A skipped required check rejects.
6. Add the import-root probe for your stack to the verify entry (before the
   full suite) and a runtime import-boundary test for your production entry
   points (`verification/verify-portfolio.md`, "Runtime import boundary";
   probes per stack in `harness/worktree-ritual.md`). Falsify both: point the
   root at the primary checkout and watch the probe refuse; add one excluded
   import and watch the boundary test go red.
7. Copy and adapt `verification/ci/*.example` → `.github/workflows/`. The
   regime is non-negotiable: full commit-SHA pinning of every action (never
   tags), secret-gated green-skip (a missing secret is a green skip with a
   ::notice, never a red), minimal `permissions:`, single-flight concurrency
   where it matters. Local verify is the gate; CI verifies additionally and
   DEPLOYS from main. `verification/ci/review-prompt.md` is the canonical
   review prompt — point the review lane at it.
8. Bind everything into `make verify`. Build every product the suite reads
   BEFORE running it (`verification/verify-portfolio.md`, "Build inputs
   exist before verify"), then run it. Green before the next step.

## Step 3 — Interpretation pillar
1. Create `docs/choices/` with `interpretation/choices-ledger-README.md`. The
   choices audit is a TRANSACTION POINT: every lane handback is audited with
   the `audit-choices` skill and recorded in `docs/choices/<train>.md` BEFORE
   assembly; unsound choices are resolved before the train is built. Every
   choice carries one stable ID (`<train>/<lane>-<n>`) from self-report to
   fix commit, and its walked scenario is stored in the protocol or in a
   sidecar committed under `docs/choices/<train>/` — never in a scratchpad
   (README §2–§3). `interpretation/examples/simplification-review.md` shows
   one train done this way end to end.
2. Establish the memory conventions (`interpretation/memory-conventions.md`)
   and the evaluation practice (`interpretation/evaluation-practice.md` —
   how a result is READ: a working judge over a dead product role, a fake
   prefix over a full journey, a small bed over scale; the admission gate
   itself is in `verification/evaluation-readiness.md`).
   Evaluation practice presumes an artifact bank: every full evaluation runs
   on an isolated copy of a banked pristine source, never on the source and
   never on leftover state (`harness/artifact-bank.md` §3, §6).
3. Read `interpretation/investigation-practice.md` — instrument-first is the
   default for every debugging lane; "investigate before the fix lane gets
   its mandate" is the default whenever the cause is uncertain (the brief is
   `planning/investigation-brief-template.md`; the trust rules are
   `verification/falsification.md` §7–§9); its "Consumer inventory"
   section is the mandatory pre-step for every lane that deletes, moves,
   splits or renames: one row per protected element, readers in every
   language and path-keyed tool baselines included, live-versus-historical
   decided per file by executing readers; and its "Identity and history"
   section is the default for any gate, count or plan that reads stored
   evidence.

## Step 4 — Skills
Copy `skills/` → `.agents/skills/` and symlink `.claude/skills` to it. Verify
the hash lock (`skills-lock.json`). Write the skill-routing table into the
repo's operations doc (the template carries it).

Three of the skills (`bulk-reader`, `log-triage`, `handback-digest`) are the
bounded bulk-read pilot. They are inert until you bind the commands and
variables in `harness/bulk-read-contract.md` §4 in the operations doc; they
register NO hook. Do not add a PreToolUse registration in this step.

## Step 5 — Harness
1. Keep `harness/launch_lane.sh` where it is (it is repo-agnostic and takes
   everything as a parameter — worktree, run id, receipt directory, brief,
   the CLI argv, detachment, artifact bank). Run its test on the machine that
   will dispatch: `bash harness/tests/test_launch_lane.sh`. Read the printed
   `detach method exercised:` line — detachment is proven per host, not
   assumed (`harness/run-lifecycle.md` §4, §10).
2. Read `harness/run-lifecycle.md`. It owns dispatch and monitoring: run
   identity and receipts (§2), the environment contract (§3 — no built-in
   paths, no key reading; log the CLI in before dispatch), the run-bound exit
   verdict (§5), process identity by executable name + exact argv token (§6),
   rate-limit classification by named field (§7), read-only runs whose
   report the wrapper extracts from stdout (§8), and banking receipts as they
   are produced (§9). Set `LANE_ARTIFACT_BANK` to the durable root chosen in
   Step 6.
3. Follow `harness/worktree-ritual.md` (worktree from a pinned SHA, symlinked
   env dirs gitignored, one lane one writer under the launcher's writer lock,
   the wrapper commits — coding CLIs often cannot commit in linked worktrees,
   the import-root proof for your stack, and the teardown checks: bank
   gitignored valuables before removal) and `harness/report-schema.md`
   (sentinel + structured report carrying `run_id:`, `task:`/`round:`,
   `measurements:`, `revision_table:` with a named proof owner, the mandatory
   `choices:` self-report and its `<lane>-choices.md` sidecar). Circuit
   breakers are not in the schema: they live in
   `planning/execution-contract.md` §3–§6.
4. Parameterize the standing brief's paths as the launcher's environment
   names (`$LANE_RESULT_PATH`, `$LANE_SENTINEL_DIR`, `$LANE_RUN_ID`), never as
   literal scratch paths.
5. Fill in `harness/train-plan.md` and commit it as `docs/train-plan.md`: the
   exact command per landing step (§2) and the resource contract (§3 — port
   range, agent-CLI binary and subcommand token, load threshold and wait
   window, hard stops). Save its §4.2 receipt launcher into the project's
   scripts directory — the full-verify verdict is read from that receipt and
   nothing else (§4.1). Run its §7 falsification list once on a throwaway
   train. No assembler script ships; land from the plan by hand first
   (`verification/lander-duties.md` §6).
6. Establish the artifact bank (`harness/artifact-bank.md`). Write its §10
   table into the repo's operations doc: bank root (the `LANE_ARTIFACT_BANK`
   directory chosen in Step 6), what counts as durable, the inventory of
   every config key / manifest field / database column that stores a path,
   the seed and its hash, the renewal cadence, the role names the receipt
   reports, retention. Then run `sh harness/examples/copy-isolation.sh` and
   read its output: it is the red→red→red→green shape your own isolation
   check must reproduce against the product's real path inventory. A
   factory whose pristine acceptance is "the manifest hashes match" is not
   installed.
7. Optional, measurement-gated: `harness/bulk-read-contract.md` — route large
   reads through a cheaper worker. Bind its parameters (§4), run the
   worker-down trial (§5) and the off/on pilot (§7) before registering the
   adapter (§8). Installing the contract activates nothing.

## Step 6 — User level
Follow `user-level/README.md`: add the global CLAUDE snippet to the user's
`~/.claude/CLAUDE.md`, establish the memory conventions, install the
recommended user-level skills. Do NOT activate
`user-level/landing-policy.example.md` — it ships INACTIVE and only the
owner activates it, in person. Until then every finished train is held with
a decision brief (`verification/lander-duties.md` §7).

## Step 7 — Smoke test
1. Create one trivial board item, write a mini-spec, dispatch one lane from
   the standing brief through `harness/launch_lane.sh` (read its `verdict`
   before touching the handback — `harness/run-lifecycle.md` §5), run the
   choices audit on the handback, assemble a single-lane train from
   `docs/train-plan.md` (the install exception — independent ready lanes
   otherwise share a train, `verification/lander-duties.md` §2), run full
   verify, land, sweep the FULL board (`planning/board-protocol.md`,
   "Authority, pagination and derived views"). Fill the
   execution-contract fields for real even on the trivial task: `task:` is
   the item ID, `round: 1`, the apparatus is named, and if the lane cannot
   run it the proof owner is a role plus an exact command. Then run the
   rewrite check in `harness/report-schema.md` on the handback.
2. Falsify at least one gate along the way (plant a violation, watch it go
   red, remove it). For the secret gate: random-shaped secrets on a throwaway
   branch (see verification/gates/README.md — documentation keys are
   allowlisted; the working-tree leg is advisory, history is HARD).
   If the repo has any evaluation or demo that runs against an instance:
   build one source from the seed, make two copies, plant an external path
   in one recorded reference and confirm the isolation check refuses it
   (`harness/artifact-bank.md` §3); confirm the source's hash is unchanged
   after a run on a copy (§6).
3. Run the installed gates THE WAY THEIR RUNBOOK DOCUMENTS THEM (`python
   scripts/<gate>.py --check`, then `make verify`) and read each gate's own
   verdict line; an import-only test does not count
   (`verification/evaluation-readiness.md` §6). If the repo serves a
   surface, run one offline functional trial against a small start state
   with fake AI roles and bank its receipt (§4 shape) as the installation's
   first evaluation artifact. Falsify the admission gate by planting the
   three rejections of `verification/falsification.md` rule 13.
4. Land with `make verify && git push` — never an unconditional push after a
   verify you did not read — and only on the owner's live ruling for the
   smoke train (the owner is present for the smoke test; that ruling IS the
   authority, recorded on the smoke item). Do not treat the smoke landing
   as a grant of standing authority.
5. Falsify the round counter: re-dispatch the same item under a new lane
   name and confirm the wrapper writes `round: 2`; attempt a third and
   confirm it is refused without a logged restart-from-document.
A factory whose smoke test has not run is not installed — it is copied.
