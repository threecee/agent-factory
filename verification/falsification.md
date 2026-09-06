# Falsification norms

1. **Red before green.** Every fix lands with a test that FAILS with the fix
   reverted. The wrapper verifies this mechanically after committing:
   checkout the parent's version of the changed source, run the new test
   (expect red), restore (expect green). Falsify AFTER committing — the
   restore step wipes uncommitted edits.
2. **Falsification checks the message, not just the verdict.** An exit code 1
   that mis-describes the failure is a failed falsification.
3. **Instrument before product.** For any non-trivial bug: reproduce with
   attribution (who held the resource, which layer enforced, which hash
   bucket) BEFORE writing the fix. Roughly three of four "obvious" fixes
   written before instrumentation address the wrong layer.
4. **Surgical mutation isolates the enforcing layer.** When multiple layers
   could enforce an invariant, mutate ONE and observe — never conclude from
   reading alone.
5. **Gate teeth are proven by planting.** A new or lifted gate must be shown
   to catch a planted violation before it counts as protection.
6. **The container/CI invocation is a separate truth.** A test suite green
   under the dev environment proves nothing about the documented production
   invocation (CMD paths, missing PYTHONPATH, files not COPY'd into the
   image). Test the invocation your Dockerfile/runbook actually documents.
   An import test alone (`python -c "import gate"`) is not the invocation
   (`evaluation-readiness.md` §6).
7. **A root-cause report is falsified before the fix, or at the latest as
   the red acceptance criterion.** A read-only investigation
   (`../planning/investigation-brief-template.md`) returns a proposed causal
   model, not a verdict. Before a fix brief is written from it, the
   orchestrator re-runs at least one of its decisive checks on the same
   frozen evidence — the query that refuted the leading hypothesis, the
   cited lines that carry the mechanism — and the result must match. Where
   no direct check is possible before dispatch, the mechanism becomes the
   fix lane's first red test: a test that encodes the claimed mechanism and
   fails on the unfixed code. If that test is green on the unfixed code, the
   model is wrong and the lane STOPs before building on it. The worked
   example: the claim "the retry writes progress `444 -> 0` and the monotonic
   guard rejects it" was pinned as "checkpoint 2, provoke stale, the retry
   must not attempt `2 -> 0`" — red on the old initialization, green on the
   rebase, red again with the rebase reverted.
8. **Refutation is source-backed; a reading is not a refutation.** A
   hypothesis is refuted by a query or probe against pinned evidence that
   shows the mechanism did not occur (the suspected jobs never wrote to the
   identity; no identity-feeding write exists in the failure window), or by
   cited code that cannot produce the observed rows (the stale path throws
   before it publishes). "I read the code and it looks fine" supports
   nothing either way (rule 4 applies: mutate one layer and observe when
   reading cannot decide). A refutation is reported with the check that
   produced it, so a reviewer can re-run it.
9. **Unknown stays unknown.** When the evidence cannot decide a cause (an
   exception that was not persisted, a state the package does not contain),
   the report says "unknown" and names the gap, the fix brief carries the
   gap as an observability criterion (persist the cause class; the next
   run's log must show it), and the choices protocol records it as an open
   observation. Rewriting an unknown into the nearest plausible mechanism —
   "attempt 2 was self-induced drift" when no write in the window supports
   it — is a false green on the causal model, and the fix built on it is
   tested against a mechanism that may not exist. The fix mandate is
   falsifiable only for the mechanisms the evidence supports; for the rest
   it is a promise to observe, and is labeled as one.
10. **A gate over stored evidence is falsified in BOTH directions.** Plant a
    false red and a false green, and require the gate to survive each:
    - *False red:* a historical unavailable row whose scope has a valid
      successor the consumer selects. The gate must stay green and report it
      as history (`unavailable_superseded`), not as a violation.
    - *False green:* a live unavailable row — the row the consumer selects —
      under a role that was configured to deliver. The gate must fail with a
      message naming the live count (`unavailable_live`), not the total.
    Both counts appear in the receipt (`../harness/artifact-bank.md` §5).
    Message check (rule 2) applies: a gate that fails with `unavailable=666`
    when the consumer sees 1 has mis-described the failure. The principle
    lives in `../interpretation/investigation-practice.md` (Identity and
    history); the planted rows and expected verdicts are in
    `examples/identity-and-history.md` §1.
11. **Identity gates are planted with a wrong-but-newer candidate.** Where
    the consumer resolves an artifact by a content key, plant a decoy with a
    NEWER mtime (or later insertion) and the wrong key. A gate that selects
    the decoy is red; a gate that resolves by the consumer's key and rejects
    a missing key is green. Copy operations reorder mtimes — the planted
    decoy is the realistic case, not a corner. Example §2.
12. **Incremental work is falsified on three axes.** For any plan that
    reuses partial results when its inputs move: (a) an unchanged identity
    is NOT recomputed (assert the exact set sent to the expensive step);
    (b) a changed identity IS recomputed and the old result is retired only
    by exact precedence — a weaker result never replaces a stronger current
    one of the same identity; (c) progress after a retry starts from the
    stored receipt and never regresses. The falsification for (c) is the old
    `restart at 0` initialization: with it reverted in, the store's own
    regression guard must turn red. Example §3.
13. **A skip is a verdict too — plant it.** An admission gate
    (`evaluation-readiness.md`) is proven by three planted receipts, each of
    which must REJECT with a message naming the cause: (a) a product AI role
    configured real and observed dead while the judge is alive; (b) a
    required data precondition unmet on the small bed; (c) a required check
    marked `skip`. A wrapper that admits on "no check failed" passes (c) and
    is vacuous. Then restore and prove the honest partial receipt (fake
    roles, omitted actions with cause) is ADMITTED as a functional trial and
    REJECTED as an AI evaluation — both directions, per evaluation-readiness
    §2.2 rule 8. The worked receipts are evaluation-readiness §5.1–§5.4.
14. **Fabricated probes falsify nothing.** A check tested only against inputs
    the test invented (a selector list the test wrote, a log line the test
    composed) has never met the real inventory it guards. Run the check once
    against the actual served DOM, the actual log, the actual source
    inventory before counting it as protection; the source factory's first
    live smoke found a helper import that had never existed on main because
    every unit test had supplied its own probes.
