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
