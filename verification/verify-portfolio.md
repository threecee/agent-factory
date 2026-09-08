# The verify portfolio — prove that it works

## Structure
`make verify` runs the full portfolio and stops at the first failing gate:
format check → lint ratchet → type ratchet → complexity ratchet → security
scans (secret scan with BOTH a committed-history leg and a working-tree leg;
SAST; dependency audit) → traceability → backlog teeth → ADR index →
module-coverage cap → full test suite(s). A frontend adds its own suite —
note that if the make target lacks a frontend-test leg, trains touching the
frontend must run it explicitly at assembly.

## Build inputs exist before verify

1. Every product the suite or a gate READS — a bundled frontend, generated
   docs, a compiled schema, a fixture index — is built on the tree under test
   BEFORE the portfolio starts, on every train, whether or not a file under
   that product's source changed. A build product is a gitignored local
   artifact; a stale one from an earlier checkout renders as a product bug
   that no source diff explains.
2. The build writes a stamp (input digest or SHA) the tests can compare
   against; "the build exists" is not "the build is current". A gate that
   checks the stamp belongs in the cheap gates.
3. The check for "did a frontend file change?" is not a substitute: a
   served-instance test reads the bundle regardless of what changed. The
   source factory's lander once skipped the build because no frontend file
   had changed on a train that did change backend code; the train worktree
   had no bundle, a login page answered 503 in a browser test, and the
   first verify round was red for an apparatus reason, not a product one.
4. The commands are the project's (harness/train-plan.md §2, step 5). The
   order — cross-checks, build, cheap gates, full verify — is the lander's
   (lander-duties.md §1).

## Laws
- **One verify at a time, on an idle machine.** Full verify never shares the
  machine with a build lane, a served instance or an evaluation wave; the
  resource contract in harness/train-plan.md §3 is the check, run
  immediately before the suite (a snapshot, not a lock — train-plan §3.6).
  A red suite from a contended machine is adjudicated (below), never
  trusted.
- **Watchers never run the chain.** A verification chain that may outlive one
  tool call runs under one detached driver. The driver sequences the phases
  and writes each phase's log and atomic `<run-id>-<phase>.exit` file. A
  watcher only reads those receipts and reports state; its timeout ends the
  watch, never signals or kills the driver or its children. The next phase is
  started by the driver from the preceding phase receipt, never by the watcher
  (`harness/train-plan.md` §4.2). Provenance: source factory Varde w137,
  2026-09-08.
- **Local verify gates landing — in both landing modes** (landing-modes.md).
  The host's branch policy requires the lander's `local-verify` status on
  the exact commit; CI re-verifies on the train pull request (pr) or on main
  after the push (direct-push) and is read and adjudicated, never the gate,
  until a project promotes it by a reviewed diff (ci/README.md §4). Lanes
  never run full verify and never open pull requests; the lander does both,
  on the ASSEMBLED train — verify the batch, not just its parts.
- **Ratchets move one way.** Every baseline gate exposes `--update` as the
  only path to a new baseline; regeneration is audited by diffing the
  semantic delta, and NEW findings of a secret-like nature are never
  baselined — rewrite the commit instead.
- **Read the log, not the wrapper.** Background exit codes lie; the gate's own
  log line is the verdict, and a train's verdict is its run-bound exit
  receipt (harness/train-plan.md §4.1 owns the rule and §4.2 the launcher;
  lander-duties.md §3 — a resumed attempt gets a new run id and never
  overwrites the failed attempt's receipt). A red verify has three
  different causes that look
  alike (product bug, harness/starvation, stale state) — adjudicate before
  acting: rerun the failing file at idle; load-starved timing tests that go
  green at idle are a known class (then harden the test to assert contracts,
  not clock margins).
- **A red X is evidence, not an emergency.** A rescue is a verdict too — test
  the rescue's limit case.
- **Prove the import root before the expensive run.** Immediately before the
  full verify on the assembled tree — and before a lane's proof run — print
  where the package resolved from with the tree's own import root set, and
  refuse any origin outside that tree (Python:
  `PYTHONPATH=<train>/src python -c 'import <pkg>; print(<pkg>.__file__)'`;
  the per-stack probes are in `harness/worktree-ritual.md`). A green verify
  that imported the primary checkout verified the wrong code; the printed
  origin goes into the train receipt, as the source factory's assembler does.
- **Fresh evidence only.** A verdict about a lane run is read from the
  receipts of THAT run — start receipt, exit receipt with `LANE_EXIT`, report
  carrying the run id, all named `<lane>.<run-id>.*` — never from an exit
  file whose run id or timestamp belongs to an earlier round, and never from
  a captured pipe status (`harness/run-lifecycle.md` §5). The launcher's
  `verdict` subcommand is the mechanical form; a hedge phrase in a report
  ("should pass now") is no proof at all.

## Evaluation legs inside verify
The admission rules and the receipt are owned by
`verification/evaluation-readiness.md`; this section says which legs the
portfolio carries.
- **The offline functional trial is a verify leg.** A scripted user journey
  in a real browser against a banked small start state with fake AI roles,
  writing a partial receipt (actions performed / omitted / cause). It is
  the cheapest true proof that the product's plumbing survived the train.
- **The AI-on trial is never a verify leg.** It runs in a provider window
  against a separately built AI-on copy of the same small seed. The two beds
  are never one symlink that a verify run could flip.
- **Absent bed ⇒ loud skip, never a fail, never a silent pass.** The leg
  skips with a reason naming the missing bank. What a skip may and may not
  satisfy — and the lander's duty to see the leg's own PASSED line whenever
  the bank exists — is evaluation-readiness §3 rule 13; this file only
  carries the leg.
- **Data preconditions are checked before the driver starts.** Each critical
  action names the data situation it needs; an unmet precondition fails the
  leg on data, with the beat id in the message, not on a selector timeout
  minutes later.
- **Installation smoke runs the documented entry point** — the rule is
  evaluation-readiness §6. Which tree that invocation actually imported is
  the provenance leg above ("Prove the import root before the expensive
  run"; per-stack probes in `harness/worktree-ritual.md`, "Prove which code
  the test imported").

## Known vacuity classes (test for these in review)
Inherited-field assertions (matching a copied row passes broken code) ·
write/read parity ungated (written-by-N, read-by-none passes) · helpers
tested but call sites untested (test the documented invocation — `python
scripts/X.py` has a different sys.path than pytest) · self-comparison guards
(compare against something the change cannot move) · waitFor-style
falsification that passes with the fix reverted · **import-root vacuity** (a
subprocess in a test that inherits the shared environment and imports the
primary tree; pin the root from the test file's own location) · **runtime
import boundary untested** (a production entry point silently loading the
evaluation/dev-only package family — see below) · **admission by exit code**
(a smoke whose `skip` rows do not reject lets "12/14 ok" admit an AI wave;
evaluation-readiness §2.3) · **fabricated probes** (a classifier unit-tested
against invented inputs, never the real inventory — the first live run
imported a helper that did not exist; falsification.md rule 14) · **green
suite with a skipped journey leg reported as a green journey**
(evaluation-readiness §3).

## Runtime import boundary — the method, not the list
Production entry points must not load packages that exist only for offline
evaluation, benchmarking or development, or the deployed artifact carries a
dependency it never declared. The proof is a subprocess test, run with the
tree's own import root:

```
import <every production entry point>
loaded = [m for m in sys.modules if m == "<excluded>" or m.startswith("<excluded>.")]
assert not loaded, loaded
```

The target repo defines its own entry points and its own excluded families;
what ports is the shape (a subprocess, the worktree's import root pinned from
the test's own path, an assertion over what was actually loaded) and the
falsification (add one import of the excluded family to an entry point and
watch the test go red before trusting it).

## Legs that bring lane-green closer to train-green

Cheap legs that catch on the lane or in the first minute of the train what
the full suite would find after seventeen. None has a switch: the fix is
the fix (`protections.md` §7 owns the three shipped ones).

- (a) Duplicate row ids and the canonical id form are HARD in the backlog
  check (`gates/check_backlog.py`, `duplicate_row_id_problems`).
- (b) The registry check — including the drift leg that finds a `claimed`
  row whose file is already on main — runs among the cheap gates, in
  seconds, before the suite.
- (c) The lane pregate is the brief's cheap block plus diff-triggered legs
  (a migration file ⇒ the migration test; a UI string ⇒ the help-copy test;
  the registry ⇒ the pin tests). The table is the repo's, kept in its
  operations doc and copied byte-equal into the brief at
  its `DIFF_TRIGGERED_LEGS` placeholder (`../planning/lane-brief-template.md`
  §4); the import root is pinned to the lane tree; it is never the full
  suite. Its column contract (every cell in angle brackets is the repo's;
  the two `translated from` pointers name the package chapter the repo's
  own document is written from, never a path to copy into a brief):

  | touches (globs) | run (exact command from `<wt>`) | proves | reads first |
  |---|---|---|---|
  | `migrations/**` | `<migration head test>` | one head; the count literal bumped | `<the repo's migration doc>` |
  | `<ui glob>` | `<copy-contract test>`, `<a11y name test>` | strings and roles unchanged or documented | `<the repo's pattern doc>` |
  | `docs/decisions/NUMBERS.md` | `<registry pin tests>` | registry consistent | `<the repo's number doc>`, translated from `../planning/adr-and-numbers.md` |
  | `openspec/**` | `python3 -m scripts.check_openspec` (or the project's equivalent adapter) | runs strict OpenSpec validation with the four non-interactive environment controls; reports advisory until every sidecar is accepted, then gates | `<the repo's capability-spec doc>`, translated from `../planning/capability-specs.md` §5 |
  | `<gate/guard/hook source>` | `check_gate_weakening --hard` — hard from the first lane: the train's WARN-first rule (`protections.md` §7) is for the whole tree, and a lane touching gate source has no first-train excuse; the gate's default `--base`, the merge-base with `origin/<default>`, is the right base in a lane worktree; then the rule's `falsify` | criteria not weakened | `<the repo's guard doc>`, translated from `../harness/guards.md` §11 |

  On the lane a row runs when one of its globs matches the working tree
  against the pin — the lane's command is
  `{ git diff --name-only <pin>; git ls-files --others --exclude-standard; } | sort -u`
  — because the wrapper commits after the pregate (HEAD is still `<pin>`
  when the block runs, so `<pin>..HEAD` is empty) and the canonical
  trigger, a new migration file, is untracked and invisible to every `git
  diff` form. On the train the lander re-runs the matching rows among the
  cheap gates against the committed range, `git diff --name-only
  <BASE>..HEAD` (`lander-duties.md` §1 step 6). Each row runs in seconds
  and names ONE proof, judged by exit code like any gate. The package ships
  no pregate runner: selecting the rows is the lane's reading of the table
  and the brief's §4 is the home of that duty. A row whose command is
  skip-guarded (a test that skips on an absent build product) names the
  build step in `proves` as its precondition, and the lane reports such a
  row as not run when that product is absent — a skipped row is not a
  green row. `reads first` is where domain checklists live: a
  pointer to the repo's own architecture or pattern document for that
  surface, which the brief's §2 already requires read; a harness may
  deliver that pointer as a directory-local instruction file
  (`../harness/guards.md` §9, "Domain guidance delivery"), never as a
  second statement of the rule. A first-round assembly red that no row
  caught becomes a row in the same train — the assembly finding is an
  orchestrator ledger entry (`../interpretation/choices-ledger-README.md`
  §1), and the row is its fix. The change kind of
  `../planning/execution-contract.md` §9 selects rows by what the diff
  contains; it adds no row of its own.
- (d) The never-weaken check (`gates/check_gate_weakening.py`): a baseline
  that grew without an `--update` commit, a gate changed without a test
  naming it, a net loss of `assert` lines — WARN on the first train,
  `--hard` after, a `Gate-change: ADR-NNNN` trailer as the documented
  exception.
- (e) The brief template's pregate block AND its diff-triggered legs table
  are byte-equal to the operations doc's, every section the brief cites
  exists, and every path-scoped instruction file mirrors one legs-table row
  — a test the installer writes. The package's own instance over its hub
  files is `tests/test_hub_pointers.sh`: every `pillar/file.md §N` pointer
  in the README and INSTALL resolves to a file and a numbered heading — a
  `§N` continuation binds to the last path in its paragraph, a pointer
  wrapped across a line is read whole, a quoted heading must open a heading
  or a bold lead — the counts INSTALL states equal the tree, the pointer
  count is printed and held above a floor, and the test is self-falsified
  with a planted dead path, a planted wrong §-number, a planted
  continuation (`, §99` after a valid pointer), a planted wrapped pointer
  and a planted wrong heading (all red, naming the path). Its `--tree` mode
  scans every document under a root except the locked `skills/` set and is
  asserted green on the package; its `--installed` flag refuses `{{…}}`
  residue under `planning/` — the directory the installer resolves — and is
  asserted green over the package's chapter tree with `planning/` resolved
  and `--skills` pointing at the skill set kept elsewhere, the installer's
  own form over the copied doc tree.
- (f) The skills lock is the existing `skills/verify_skills_lock.py`; no
  second checker.
- (g) Only for repos whose tests set process-wide environment: every
  process-wide key the product sets is scrubbed in both halves of the test
  fixture.
- (h) Only for repos with a migration graph: seed literals never live in a
  migration (derivation SELECTs pass).
