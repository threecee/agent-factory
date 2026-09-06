# The verify portfolio — prove that it works

## Structure
`make verify` runs the full portfolio and stops at the first failing gate:
format check → lint ratchet → type ratchet → complexity ratchet → security
scans (secret scan with BOTH a committed-history leg and a working-tree leg;
SAST; dependency audit) → traceability → backlog teeth → ADR index →
module-coverage cap → full test suite(s). A frontend adds its own suite —
note that if the make target lacks a frontend-test leg, trains touching the
frontend must run it explicitly at assembly.

## Laws
- **Local verify gates landing.** CI re-verifies and deploys; it is never the
  gate that lets code onto main. Lanes never run full verify (the lander does,
  on the ASSEMBLED train — verify the batch, not just its parts).
- **Ratchets move one way.** Every baseline gate exposes `--update` as the
  only path to a new baseline; regeneration is audited by diffing the
  semantic delta, and NEW findings of a secret-like nature are never
  baselined — rewrite the commit instead.
- **Read the log, not the wrapper.** Background exit codes lie; the gate's own
  log line is the verdict. A red verify has three different causes that look
  alike (product bug, harness/starvation, stale state) — adjudicate before
  acting: rerun the failing file at idle; load-starved timing tests that go
  green at idle are a known class (then harden the test to assert contracts,
  not clock margins).
- **A red X is evidence, not an emergency.** A rescue is a verdict too — test
  the rescue's limit case.

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
  skips with a reason naming the missing bank; the lander requires an actual
  PASSED line for the leg on every train that touches the journey and
  whenever the bank exists (a landing duty; `lander-duties.md` is extended by PR3). A skip cannot satisfy a mandatory
  acceptance.
- **Data preconditions are checked before the driver starts.** Each critical
  action names the data situation it needs; an unmet precondition fails the
  leg on data, with the beat id in the message, not on a selector timeout
  minutes later.
- **Installation smoke runs the documented entry point.** Each gate is run
  as its runbook documents (`python scripts/<gate>.py --check`, `make
  verify`), verdict read from the gate's own line. An import-only test does
  not count (evaluation-readiness §6). Which tree a subprocess actually
  imported is the provenance leg (worktree-ritual; extended by PR2).

## Known vacuity classes (test for these in review)
Inherited-field assertions (matching a copied row passes broken code) ·
write/read parity ungated (written-by-N, read-by-none passes) · helpers
tested but call sites untested (test the documented invocation — `python
scripts/X.py` has a different sys.path than pytest) · self-comparison guards
(compare against something the change cannot move) · waitFor-style
falsification that passes with the fix reverted · admission by exit code
(a smoke whose `skip` rows do not reject lets "12/14 ok" admit an AI wave) ·
fabricated probes (a classifier unit-tested against invented inputs, never
the real inventory — the first live run imported a helper that did not
exist) · green suite with a skipped journey leg reported as a green journey.
