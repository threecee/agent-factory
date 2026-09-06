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
7. **A gate over stored evidence is falsified in BOTH directions.** Plant a
   false red and a false green, and require the gate to survive each:
   - *False red:* a historical unavailable row whose scope has a valid
     successor the consumer selects. The gate must stay green and report it
     as history (`superseded_in_practice`), not as a violation.
   - *False green:* a live unavailable row — the row the consumer selects —
     under a role that was configured to deliver. The gate must fail with a
     message naming the live count, not the total.
   Both counts appear in the receipt. Message check (rule 2) applies: a
   gate that fails with `unavailable=666` when the consumer sees 1 has
   mis-described the failure. The principle lives in
   `interpretation/investigation-practice.md` (Identity and history); the
   planted rows and expected verdicts are in
   `verification/examples/identity-and-history.md` §1.
8. **Identity gates are planted with a wrong-but-newer candidate.** Where
   the consumer resolves an artifact by a content key, plant a decoy with a
   NEWER mtime (or later insertion) and the wrong key. A gate that selects
   the decoy is red; a gate that resolves by the consumer's key and rejects
   a missing key is green. Copy operations reorder mtimes — the planted
   decoy is the realistic case, not a corner. Example §2.
9. **Incremental work is falsified on three axes.** For any plan that
   reuses partial results when its inputs move: (a) an unchanged identity
   is NOT recomputed (assert the exact set sent to the expensive step);
   (b) a changed identity IS recomputed and the old result is retired only
   by exact precedence — a weaker result never replaces a stronger current
   one of the same identity; (c) progress after a retry starts from the
   stored receipt and never regresses. The falsification for (c) is the old
   `restart at 0` initialization: with it reverted in, the store's own
   regression guard must turn red. Example §3.
