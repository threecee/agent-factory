# INSTALL — agent runbook

The kit ships its own capabilities under `openspec/specs/` as the worked
example of the four-document model. Read those current promises beside the
numbered records in `decisions/`, `ARCHITECTURE.md`, `PATTERNS.md`, and the
choices protocol before adapting their shapes to the target repository.

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
   — and resolve every installation placeholder in every copied Markdown
   file. The trial found that
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
   (a board item, or the backlog row your planning gate governs),
   `{{DIFF_TRIGGERED_LEGS}}` with the repo's diff-triggered legs table
   (`verification/verify-portfolio.md`, leg (c): touches | run | proves |
   reads first) — seed it from the gates README's domain rows and from the
   repo's own first-round assembly reds (grep the train ledgers' `O-`
   entries), and keep the table in the operations doc as its one home —
   and `{{KIND_CLASSIFIER}}` with the change-kind classifier command
   (`planning/execution-contract.md` §9), built from the docs-only
   classifier and the guarded-boundary list the repo binds in Step 5;
   until it binds one the line reads `none — classifier unbound`. The
   per-lane fields (task ID, round, apparatus, proof owner, attachments,
   ceiling, the `Kind:` line from that classifier over the planned file
   set, and the `Model/effort:` line filled from the operator's dated
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
7. Pin the capability-spec CLI with
   `npm install --save-dev --save-exact @fission-ai/openspec@1.12.0`. Verify
   that both the manifest and lock file record 1.12.0 exactly. Create
   `openspec/specs/` and `openspec/changes/archive/.gitkeep`. Set `CI=1`,
   `OPENSPEC_TELEMETRY=0`, `DO_NOT_TRACK=1`, and
   `OPENSPEC_NO_UPDATE_CHECK=1` for every validation and archive invocation.
   Write the project's `check_openspec` adapter with the advisory-to-HARD
   exit contract in `planning/capability-specs.md §5`, then use that adapter
   in verification instead of invoking raw validation as a gate.
   Resolve `{{SPEC_DELTA}}` in the lane template to the project's dispatch
   field for either the lane delta path or its no-delta trailer
   (`planning/capability-specs.md §3`). If the project ports a pairing gate,
   add the pattern-capable `spec:` leg and advisory-to-HARD transition from
   `verification/gates/README.md`.
   With the pinned binary on `PATH`, run
   `bash harness/tests/test_capability_spec_flow.sh`; an absent binary is a
   loud skip, never proof. That package test first runs strict validation over
   the kit's own `openspec/specs/`, then proves delta archival in a throwaway
   project. Also run `bash verification/tests/test_adr_anchors.sh` and
   `bash verification/tests/test_architecture_anchors.sh`; they keep the
   worked example's decision, architecture, pattern, and shell-case anchors
   resolvable.

## Step 2 — Verification pillar
1. Read `verification/gates/README.md` §"Which gates port" BEFORE copying
   anything. Of the 28 scripts, eleven are repo-agnostic decision gates
   (ADR index, traceability, backlog, number registry, gitleaks, number
   provenance, sentinel, and the three protections gates: close-out, ledger
   lint, never-weaken — stdlib + git); the rest are Python-stack tooling, frontend/
   migration/vendoring specifics, or domain choices of the source factory,
   and one (`check_contract_touch.py`) imports a module the package does
   not ship. Copy the ten to `scripts/` and `gitleaks.toml.example` →
   repo root as `.gitleaks.toml`; copy others only when the repo has the
   thing they check. The decision gates need a `python3` with **PyYAML** and
   the `gitleaks` binary, nothing else (the trial measured this in a clean
   venv). Invoke them as `python3 -m scripts.<gate>` from the repo root —
   their own documented form; `python3 scripts/<gate>.py` fails with
   `No module named 'scripts'` for every gate that imports a sibling. Each
   script's docstring is its contract. Some carry localized (Norwegian)
   output strings — translating those strings is part of your adaptation;
   never change a gate's LOGIC while translating.
   Copy `verification/select_diff_triggered_legs.sh` to the same path in the
   target repository; it is the repo-neutral selector invoked by the lane
   brief and reads the repository's parameterised table.
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
   7–9 govern root-cause reports: falsify the causal model before the fix
   (or as the fix's first red test), refute only with a source, and keep an
   unknown cause unknown. Before writing any gate over stored evidence
   (rows, snapshots, receipts) or any progress meter that survives a retry,
   read `verification/examples/identity-and-history.md` and run its script
   once (`python3 verification/examples/identity_and_history.py`, then with
   `--plant count-all`): a gate must read what the consumer reads, and is
   falsified in both directions (rules 10–12).
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
7. Copy and adapt `verification/ci/*.example` → `.github/workflows/` per
   `verification/ci/README.md` (the regime that ports, the mode table per
   file, the branch policy). They are the source factory's files below an
   English mode header: Python `make verify` arguments, a deployment
   target, a review prompt in Norwegian that names that product's ADRs and
   modules. TRANSLATE every one; the REGIME is what ports: full commit-SHA
   pinning of every action (never tags), secret-gated green-skip (a
   missing secret is a green skip with a ::notice, never a red), minimal
   `permissions:`, single-flight concurrency where it matters. Then apply
   the branch policy once: `python3 verification/protections/bootstrap_ruleset.py`
   (dry run), then `--apply`; run the repository-settings command it
   prints; on a 403 use the classic fallback in `verification/ci/README.md`
   §3; record the date in train-plan §5. Local verify is the gate in both
   landing modes; CI re-verifies and deploys (`verification/landing-modes.md`
   §4.3). `verification/ci/review-prompt.md` is the SHAPE of a review
   prompt — point the review lane at your translation of it, never at the
   file itself, and never store it under `docs/`.
8. Bind everything into `make verify`. Build every product the suite reads
   BEFORE running it (`verification/verify-portfolio.md`, "Build inputs
   exist before verify"), then run it. Green before the next step.
   `verification/examples/node/Makefile` is the trial's: import-root probe,
   the four decision gates, the ratchet, the test runner.
9. Wire the three protections gates: `python3 -m scripts.check_choices_protocol
   --warn` among the cheap gates of the train (WARN on the first train, HARD
   after — `verification/protections.md` §5), `python3 -m
   scripts.check_gate_weakening` over the train range (WARN first, `--hard`
   after), and `python3 -m scripts.check_landing_closeout --state …` as the
   close-out reading (`verification/lander-duties.md` §8). The drift leg and
   the duplicate-id leg run inside the registry and backlog gates you
   already wired.
10. Write the consistency test of `verification/verify-portfolio.md` leg
    (e): the brief's pregate block AND its diff-triggered legs table are
    byte-equal to the operations doc's, every section the brief cites
    exists, and every path-scoped instruction file (Step 5 item 8) mirrors
    one legs-table row. `verification/tests/test_hub_pointers.sh` is the
    package's own instance and the shape to copy; its `--tree --installed`
    form over the copied doc tree (`--skills .agents/skills`, Step 4's
    location) also refuses installation-placeholder residue in every
    Markdown file in that tree.

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
   `verification/falsification.md` rules 7–9); its "Consumer inventory"
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
   must print `verified: 32 skill(s)`. The lock is a content digest per
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
4. If the upstream `superpowers` plugin is installed at user level, disable it
   where this kit's vendored copies are used: the plugin injects its own
   session-start mandate and creates a second routing authority.

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
   Choose the landing mode in train-plan §5 — `pr` is the default; a
   project that declares `direct-push` writes its standing reason there
   (`verification/landing-modes.md` §1, §5).
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
8. Optional, measurement-gated: `harness/guards.md`. Run
   `bash harness/tests/test_guards.sh`. Keep `harness/guards/` and
   `harness/adapters/` where they are (the settings example already points
   there) or move BOTH together — imports are package-relative and the
   package directory must keep the name `guards`. Add `.factory-guard/` and
   `__pycache__/` to the target repo's `.gitignore` before the first hooked
   lane (the wrapper's `git add -A` must never commit them — the same rule
   as the env symlinks in item 1). Bind the §8 parameters in the operations
   doc and put the same values where the hook process reads them (§8 names
   the path per harness; the session-start reminder prints what is bound).
   Run `python3 harness/guards/guard_dispatch.py falsify --lane install
   --out <dir>` and bank the log — the receipt proves the shipped tables
   under a scrubbed environment, your binding is proved on the first hooked
   train (§11). Then register the adapter block from
   `harness/adapters/claude-code-settings.json.example` as a deliberate
   step — the package registers nothing. Coding CLIs get the
   `AGENTS.md.example` paragraph. Every rule that applies is written into
   the operations doc as a reviewed diff naming the guard, the switch and
   the falsification. A rules directory (a Claude Code `.claude/rules/`
   file with `paths:` frontmatter, a Cursor glob-scoped rule, a nested
   `CLAUDE.md` or `AGENTS.md`) is optional; if used, every file carries the
   path scope of ONE legs-table row and its whole body is the pointer that
   row's `reads first` column names — never a second statement of a rule,
   never claimed as a check (`harness/guards.md` §2 is the home of that
   rule; the channel is `harness/guards.md` §9, "Domain guidance delivery").
9. Install the tracked git hooks once in the primary —
   `python3 verification/protections/git_hooks.py install` (`core.hooksPath`,
   shared by every worktree; `status` exits 1 until done, and the
   session-start reminder prints `GIT HOOKS:` until then) — and bind the
   protections parameters where the hook process reads them, beside the
   guards' (`harness/guards.md` §8): the commit identity and the trailer
   form (`FACTORY_GUARD_GIT_EMAIL`, `FACTORY_GUARD_SOURCE_PREFIX`,
   `FACTORY_GUARD_TRAILER_RE`, `FACTORY_GUARD_DECISIONS_DIR`), the default
   branch and the declared landing mode (`FACTORY_GUARD_DEFAULT_BRANCH`,
   `FACTORY_GUARD_LANDING_MODE_DEFAULT`); `verification/protections.md` §1.
   Run `bash verification/tests/test_git_hooks.sh` and
   `bash verification/tests/test_landing_protections.sh` on the machine that
   will land.

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
   verify through the receipt launcher, land in pr mode — push the train
   branch, post the `local-verify` status from the receipt, open the pull
   request with the ledger as its body, take the owner's live ruling as the
   authority, merge with `gh pr merge <n> --merge --match-head-commit
   <HEAD=>`, close out per `verification/lander-duties.md` §8 — then sweep
   the FULL board (`planning/board-protocol.md`, "Authority, pagination and
   derived views"). Order matters and the trial got it wrong once: read the
   receipt (`EXIT=0`, `HEAD=` matches, `BASE=` is an ancestor), THEN merge
   or push, THEN sweep — a sweep that runs after a red receipt marks work
   done that never landed. If `origin/main` moved while you verified, the
   landing is rejected and the train is re-assembled and re-verified under
   a new run id (`verification/lander-duties.md` §3); the failed attempt's
   receipt stays. A scratch trial with a bare local origin has no
   pull-request host and lands by direct push, saying so in its ledger
   (`landing mode: direct-push`, `override reason:`).
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
   the branch clears it). Then the branch-policy falsification of
   `verification/falsification.md` rule 16, in a THROWAWAY repository with
   the same payload applied (`verification/ci/README.md` §5) — never on the
   real main; record the five outcomes in the smoke protocol.
   If the repo has any evaluation or demo that runs against an instance:
   build one source from the seed, make two copies, plant an external path
   in one recorded reference and confirm the isolation check refuses it
   (`harness/artifact-bank.md` §3); confirm the source's hash is unchanged
   after a run on a copy (§6).
3. Run the installed gates THE WAY THEIR RUNBOOK DOCUMENTS THEM
   (`python3 -m scripts.<gate>`, then `make verify`) and read each gate's own
   verdict line; an import-only test does not count
   (`verification/evaluation-readiness.md` §6). Run
   `sh verification/tests/test_hub_pointers.sh` once on the package (the
   hub pointers and INSTALL's counts hold) and its `--check --tree
   --installed <docs root> --skills .agents/skills` form on the copied doc
   tree (`--skills` names where Step 4 put the skill set; the doc root
   carries none): no dead pointer and no installation-placeholder residue
   in any Markdown file. The test's case 8 runs this exact form on the
   package's own chapter tree with every placeholder resolved and the skills
   kept elsewhere, so a faithful copy is green. If the repo
   serves a
   surface, run one offline functional trial against a small start state
   with fake AI roles and bank its receipt (§4 shape) as the installation's
   first evaluation artifact. Falsify the admission gate by planting the
   three rejections of `verification/falsification.md` rule 13.
4. Land with the receipt read and the merge or push — never an unconditional push
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
6. Mount the guards for the smoke train from assembly start; record every
   refusal and switch in the ledger; a false positive without a named
   alternative goes to WARN.
7. Falsify the diff trigger like any gate: plant one legs-table row (a glob
   and a one-second command) in a scratch lane and run the brief's §4 with
   the lane-side command — `{ git diff --name-only <pin>; git ls-files
   --others --exclude-standard; } | sort -u` — three times: with one
   matching file EDITED, the lane's pregate output (its result file) must
   show the row ran; with a matching file CREATED and left uncommitted (a
   new migration file — the canonical trigger, invisible to every `git
   diff` form), the row must run again; with a file no row matches —
   nothing runs. Then declare the scratch lane `source` and plant a file
   of the `record` kind (a migration, a baseline): the lander's
   re-derivation over `<BASE>..HEAD` on the committed train must print
   `record` and the ledger line must read `kind: source→source, record`
   (`planning/execution-contract.md` §9.3 — this is the falsification of
   the design constraint that the kind and the landing legs never disagree
   about a path); with no classifier bound the line reads `none —
   classifier unbound` and the step is recorded as not exercised.
A factory whose smoke test has not run is not installed — it is copied.

## Step 8 — Record installation identity

After Step 7 is green, write `.factory-kit.yml` at the target repository root.
The file is an append-only installation stamp with this shape, using actual
values rather than the metavariables shown here:

```yaml
schema: 1
installs:
  - kit_version: "<exact release identifier or source commit>"
    installed_at: "<UTC ISO-8601 date and time>"
    parameters:
      "<parameter name>": "<resolved value>"
```

The `parameters` mapping records every named placeholder resolved in the
copied Markdown tree and every target-specific path or command selected by
this runbook. Record the name or location of a secret-bearing binding, never
the secret value itself.

**Update note.** Before updating an installed kit, read the last `installs`
entry and retain every existing entry. Apply the newer runbook, rerun Step
7.3 and the target's full verify, then append one entry for the new kit
version, update date, and complete resolved-parameter mapping; a failed update
leaves the stamp unchanged.
