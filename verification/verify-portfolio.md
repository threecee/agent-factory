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

## Known vacuity classes (test for these in review)
Inherited-field assertions (matching a copied row passes broken code) ·
write/read parity ungated (written-by-N, read-by-none passes) · helpers
tested but call sites untested (test the documented invocation — `python
scripts/X.py` has a different sys.path than pytest) · self-comparison guards
(compare against something the change cannot move) · waitFor-style
falsification that passes with the fix reverted.
