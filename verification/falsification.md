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
