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
   An import test alone (`python -c "import gate"`) is not the invocation.
7. **A skip is a verdict too — plant it.** An admission gate
   (`evaluation-readiness.md`) is proven by three planted receipts, each of
   which must REJECT with a message naming the cause: (a) a product AI role
   configured real and observed dead while the judge is alive; (b) a
   required data precondition unmet on the small bed; (c) a required check
   marked `skip`. A wrapper that admits on "no check failed" passes (c) and
   is vacuous. Then restore and prove the honest partial receipt (fake roles,
   omitted actions with cause) is ADMITTED as a functional trial and
   REJECTED as an AI evaluation — both directions, per evaluation-readiness §2.2 rule 8.
8. **Fabricated probes falsify nothing.** A check tested only against inputs
   the test invented (a selector list the test wrote, a log line the test
   composed) has never met the real inventory it guards. Run the check once
   against the actual served DOM, the actual log, the actual source
   inventory before counting it as protection; the source factory's first
   live smoke found a helper import that had never existed on main because
   every unit test had supplied its own probes.
