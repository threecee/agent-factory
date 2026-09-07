# INSTALL — agent runbook

You are an LLM agent installing the factory into the repo you are standing in.
Follow the steps in order. Everything deterministic ships in this package;
YOUR job is parameterization against the target repo's language, build chain
and domain. Where a step says TRANSLATE, produce the target repo's own
document from the package's doctrine — keep section numbering stable (lane
briefs cite §-numbers).

This runbook was last tried end to end on 2026-09-06 against a Node
hello-world with one test and no Python project
(`verification/examples/install-trial-node.md`). Every "the trial found"
note below comes from that run; the trial's Node gate, boundary test,
Makefile and scripted CLI are in `verification/examples/node/`.

## Step 0 — Survey the target repo
Language/build chain, test command, lint/format, existing CI, whether a
frontend exists, whether GitHub Projects is in use. Identify the **verify
portfolio**: the set of commands that together constitute full local
verification. The factory REQUIRES one — build it if missing (a `make verify`
that runs everything and stops at the first red gate). Decide now which
`python3` will run the repo-agnostic decision gates (Step 2.1) if the repo
has no Python of its own, and pin it in the verify entry (`PY ?= python3`).

## Step 1 — Planning pillar
1. Copy the package's doc tree under ONE root that keeps its directory
   layout — `docs/factory/{planning,verification,interpretation,harness,user-level}/`
   — and resolve every {{PLACEHOLDER}} in `planning/`. The trial found that
   flattening `planning/*.md` into `docs/` leaves about thirty `../harness/…`,
   `../interpretation/…`, `../verification/…` and `../user-level/…` links
   dangling; the pillars cite each other by relative path. Do NOT copy
   `verification/gates/`, `verification/ci/` or `harness/tests/` under
   `docs/` (gates go to `scripts/` in Step 2; the CI examples are templates,
   Step 2.7; and anything under `docs/**` is scanned by `check_backlog.py`
   for `ADR-NNNN` references — the source factory's review prompt cites
   four ADRs your repo does not have, and the trial's first train went red
   on exactly that). `planning/CLAUDE.md.example` is not matched by `*.md`;
   copy it by name.
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
   ceiling, and the `Model/effort:` line filled from the operator's dated
   policy — `harness/model-policy.md` §4) are filled at dispatch, never in
   the template. No template, skill or doc carries a model name as a
   default.
4. Copy `planning/investigation-brief-template.md` →
   `.claude/templates/investigation-brief.md`. It is the read-only lane a
   bug goes through BEFORE it gets a fix brief when the cause is uncertain:
   pinned SHA, frozen evidence package (harness/artifact-bank.md), competing
   hypotheses, verdicts with sources, no code change. Its §8 is the boundary
   to the fix brief; do not add a mandatory investigation phase for trivial
   reproduced defects (its §0 says when).
5. Create `docs/decisions/` with `planning/NUMBERS-template.md` as
   `docs/decisions/NUMBERS.md`. ADR discipline: frontmatter `id: ADR-NNNN`
   + `status:` + `code:` (`planning/adr-and-numbers.md`; the trial found
   the `id:` field is required by the traceability gate and was
   undocumented). Numbers are allocated ONLY by the orchestrator, claimed in
   NUMBERS, flipped to `landed` at landing. Wire
   `python3 -m scripts.build_adr_index --check` into verify.
6. Run `harness/bootstrap_board.sh <owner> "<name>"` and write the project ID,
   Status field ID and option IDs into the repo's CLAUDE.md anchor
   (`planning/CLAUDE.md.example`). It needs `gh` with the project scope and
   a GitHub owner. A scratch trial without a GitHub remote can stand in a
   file for the smoke test (mark it "NOT an installed board"), but a repo
   whose board is a file has not completed this step.

## Step 2 — Verification pillar
1. Read `verification/gates/README.md` §"Which gates port" BEFORE copying
   anything. Of the 24 scripts, seven are repo-agnostic decision gates
   (ADR index, traceability, backlog, number registry, gitleaks, number
   provenance, sentinel); the rest are Python-stack tooling, frontend/
   migration/vendoring specifics, or domain choices of the source factory,
   and one (`check_contract_touch.py`) imports a module the package does
   not ship. Copy the seven to `scripts/` and `gitleaks.toml.example` →
   repo root as `.gitleaks.toml`; copy others only when the repo has the
   thing they check. The decision gates need a `python3` with **PyYAML** and
   the `gitleaks` binary, nothing else (the trial measured this in a clean
   venv). Invoke them as `python3 -m scripts.<gate>` from the repo root —
   their own documented form; `python3 scripts/<gate>.py` fails with
   `No module named 'scripts'` for every gate that imports a sibling. Each
   script's docstring is its contract. Some carry localized (Norwegian)
   output strings — translating those strings is part of your adaptation;
   never change a gate's LOGIC while translating.
2. Language fit: the ruff/mypy/bandit/semgrep/sca gates are Python-specific.
   For other stacks, WRITE equivalent ratchet gates with the same contract:
   a committed per-rule baseline, zero-regression enforcement, `--update`
   as the only path to a new baseline, `--report` exit 0, and a MISSING
   baseline as a hard failure — never lowering to pass.
   `verification/examples/node/check_lint_ratchet.mjs` is the contract in
   JavaScript; the trial falsified it (missing baseline → exit 1; planted
   finding → exit 1 naming the rule and line; restored → exit 0).
3. `check_backlog.py` enforces planning discipline (specs cited-or-stamped;
   DONE rows require closing commit SHAs that are ancestors of main — the
   trial planted a non-ancestor SHA and watched it refuse).
   `check_module_coverage.py` enforces ADR↔code pairing under a one-way cap
   (Python repos). Calibrate against the repo's starting point via their
   `--update` mechanisms — never by deleting assertions.
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
   verify leg). A skipped required check rejects. A repo with no served
   surface and no AI role writes "not applicable" for the last two and
   says so in the operations doc; it does not skip the smoke.
6. Add the import-root probe for your stack to the verify entry (before the
   full suite) and a runtime import-boundary test for your production entry
   points (`verification/verify-portfolio.md`, "Runtime import boundary";
   probes per stack in `harness/worktree-ritual.md`). Falsify both: point the
   root at the primary checkout and watch the probe refuse; add one excluded
   import and watch the boundary test go red. The trial's first boundary
   test stayed green with the violation planted (it matched a module name
   Node does not use) — the falsification is what caught it; the corrected
   test is `verification/examples/node/import_boundary.test.js`.
7. Copy and adapt `verification/ci/*.example` → `.github/workflows/`. They
   are the source factory's files: Python `make verify` arguments, a
   deployment target, a review prompt in Norwegian that names that
   product's ADRs and modules. TRANSLATE every one; the REGIME is what
   ports: full commit-SHA pinning of every action (never tags),
   secret-gated green-skip (a missing secret is a green skip with a
   ::notice, never a red), minimal `permissions:`, single-flight concurrency
   where it matters. Local verify is the gate; CI verifies additionally and
   DEPLOYS from main. `verification/ci/review-prompt.md` is the SHAPE of a
   review prompt — point the review lane at your translation of it, never
   at the file itself, and never store it under `docs/`.
8. Bind everything into `make verify`. Build every product the suite reads
   BEFORE running it (`verification/verify-portfolio.md`, "Build inputs
   exist before verify"), then run it. Green before the next step.
   `verification/examples/node/Makefile` is the trial's: import-root probe,
   the four decision gates, the ratchet, the test runner.

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
1. Copy `skills/` → `.agents/skills/` (including `skills-lock.json` and
   `verify_skills_lock.py`; leave `skills/tests/` behind) and symlink
   `.claude/skills` to it.
2. Verify the copy is what shipped:
   `python3 .agents/skills/verify_skills_lock.py --check --root .agents/skills`
   must print `verified: 38 skill(s)`. The lock is a content digest per
   skill directory (sha256 over sorted `<path>\t<sha256>` lines;
   recomputable with coreutils — the script's docstring has the recipe, for
   a machine without Python). It is NOT an upstream pin: upstream commit
   refs were not recorded at vendoring (`skills/ATTRIBUTION.md`). A
   deliberate local adaptation is recorded with `--update` on the copy plus
   a line in the repo's attribution note; editing the JSON by hand is not a
   path. Wire the check into verify.
3. TRANSLATE `skills/ROUTING.md` (the routing table by factory step, its one
   home) into the repo's operations doc with the repo's paths and dispatch
   forms; do not copy skill procedures into the lane brief. Panel and
   second-opinion models come from the operator's model policy (Step 6),
   never from the table or a skill's built-in default.

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
   paths, no key reading; log the CLI in before dispatch; the model and
   effort tokens are argv, filled from the operator's policy), the run-bound
   exit verdict (§5), process identity by executable name + exact argv token
   (§6), rate-limit classification by named field (§7), read-only runs whose
   report the wrapper extracts from stdout (§8), and banking receipts as they
   are produced (§9). Set `LANE_ARTIFACT_BANK` to the durable root chosen in
   Step 6. The launcher banks ITS receipts (start, log, exit, report); the
   wrapper banks the rest of the handback — the choices sidecar and the
   pregate log — next to them (the trial found the bank held four files
   until the wrapper copied the other two).
3. Follow `harness/worktree-ritual.md` (worktree from a pinned SHA, symlinked
   env dirs gitignored, one lane one writer under the launcher's writer lock,
   the wrapper commits — coding CLIs often cannot commit in linked worktrees,
   the import-root proof for your stack, and the teardown checks: bank
   gitignored valuables before removal) and `harness/report-schema.md`
   (sentinel + structured report carrying `run_id:`, `task:`/`round:`,
   `measurements:`, `revision_table:` with a named proof owner, the mandatory
   `choices:` self-report and its `<lane>-choices.md` sidecar). When the
   wrapper commits, the report's `head_sha` is the pin; the handback SHA is
   the wrapper's commit and is written into the choices protocol. Circuit
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
   nothing else (§4.1: `EXIT=0`, `HEAD=` equal to the tree you push, and
   `BASE=` an ancestor of it). Run its §7 falsification list once on a
   throwaway train. No assembler script ships; land from the plan by hand
   first (`verification/lander-duties.md` §6).
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
recommended user-level skills, choose the bank root, and write the
operator's **model policy** from `user-level/model-policy.example.md` to
`~/.claude/model-policy.md` — roles bound to models with `valid_from`,
`review_by`, a dated probe per row, and every temporary authorization
carrying an end (`harness/model-policy.md` §3, §5, §6). The factory ships
no model names; a copy with the placeholders still in it binds nothing.
Do NOT activate `user-level/landing-policy.example.md` — it ships INACTIVE
and only the owner activates it, in person. Until then every finished
train is held with a decision brief (`verification/lander-duties.md` §7).

## Step 7 — Smoke test
1. Create one trivial board item, write a mini-spec, dispatch one lane from
   the standing brief through `harness/launch_lane.sh` (read its `verdict`
   before touching the handback — `harness/run-lifecycle.md` §5), run the
   choices audit on the handback, assemble a single-lane train from
   `docs/train-plan.md` (the install exception — independent ready lanes
   otherwise share a train, `verification/lander-duties.md` §2), run full
   verify through the receipt launcher, land, sweep the FULL board
   (`planning/board-protocol.md`, "Authority, pagination and derived
   views"). Order matters and the trial got it wrong once: read the receipt
   (`EXIT=0`, `HEAD=` matches, `BASE=` is an ancestor), THEN push, THEN
   sweep — a sweep that runs after a red receipt marks work done that never
   landed. If `origin/main` moved while you verified, the push is rejected
   and the train is re-assembled and re-verified under a new run id
   (`verification/lander-duties.md` §3); the failed attempt's receipt stays.
   Fill the execution-contract fields for real even on the trivial task:
   `task:` is the item ID, `round: 1`, the apparatus is named, and if the
   lane cannot run it the proof owner is a role plus an exact command. Then
   run the rewrite check in `harness/report-schema.md` on the handback.
   Expect the assembled train to catch what the lane's pregate cannot — the
   trial's lane was green and its train red on a docs-wide gate.
2. Falsify at least one gate along the way (plant a violation, watch it go
   red, remove it). For the secret gate: random-shaped secrets on a throwaway
   branch (see verification/gates/README.md — documentation keys are
   allowlisted; the working-tree leg is advisory, history is HARD; deleting
   the branch clears it).
   If the repo has any evaluation or demo that runs against an instance:
   build one source from the seed, make two copies, plant an external path
   in one recorded reference and confirm the isolation check refuses it
   (`harness/artifact-bank.md` §3); confirm the source's hash is unchanged
   after a run on a copy (§6).
3. Run the installed gates THE WAY THEIR RUNBOOK DOCUMENTS THEM
   (`python3 -m scripts.<gate>`, then `make verify`) and read each gate's own
   verdict line; an import-only test does not count
   (`verification/evaluation-readiness.md` §6). If the repo serves a
   surface, run one offline functional trial against a small start state
   with fake AI roles and bank its receipt (§4 shape) as the installation's
   first evaluation artifact. Falsify the admission gate by planting the
   three rejections of `verification/falsification.md` rule 13.
4. Land with the receipt read and `git push` — never an unconditional push
   after a verify you did not read — and only on the owner's live ruling for
   the smoke train (the owner is present for the smoke test; that ruling IS
   the authority, recorded on the smoke item). Do not treat the smoke landing
   as a grant of standing authority. A scratch trial with no owner present
   lands nowhere shared; it says so in its protocol.
5. Falsify the round counter: re-dispatch the same item under a new lane
   name with `Round: 2 of 2` in the brief and confirm the report carries
   `round: 2`; write a brief with `Round: 3 of 2` and confirm the WRAPPER
   refuses it and logs restart-from-document. The launcher does not read
   the brief's round (it accepted the round-3 brief in the trial); the
   refusal is the wrapper's check on the template's `Round:` field.
A factory whose smoke test has not run is not installed — it is copied.
