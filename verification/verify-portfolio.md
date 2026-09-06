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
- **Local verify gates landing.** CI re-verifies and deploys; it is never the
  gate that lets code onto main. Lanes never run full verify (the lander does,
  on the ASSEMBLED train — verify the batch, not just its parts).
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

## Known vacuity classes (test for these in review)
Inherited-field assertions (matching a copied row passes broken code) ·
write/read parity ungated (written-by-N, read-by-none passes) · helpers
tested but call sites untested (test the documented invocation — `python
scripts/X.py` has a different sys.path than pytest) · self-comparison guards
(compare against something the change cannot move) · waitFor-style
falsification that passes with the fix reverted.
