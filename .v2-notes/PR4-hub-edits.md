# PR4 — hub-file edits (to be integrated by the hub owner)

PR4 does not touch `INSTALL.md`, `README.md` or `user-level/README.md`
directly. The exact edits it needs are below, verbatim. Every rule they
mention has its home in `verification/evaluation-readiness.md`,
`verification/verify-portfolio.md` or `interpretation/evaluation-practice.md`;
the hub text only points there.

## INSTALL.md

### Edit 1 — Step 2, after item 4 (`Read verification/falsification.md …`)

Insert a new item 5 (renumber the current items 5 and 6 to 6 and 7):

```
5. Read `verification/evaluation-readiness.md`. TRANSLATE its §2.1 check
   families into the repo's own pre-flight smoke (stable check ids, a
   time budget, a receipt in the §4 shape) and write, into the repo's
   operations doc, which checks each evaluation type REQUIRES. Keep the
   three types apart from day one: pre-flight smoke, offline functional
   trial (fakes allowed, a verify leg), AI evaluation (real roles, never a
   verify leg). A skipped required check rejects.
```

### Edit 2 — Step 3, item 2

Replace:

```
2. Establish the memory conventions (`interpretation/memory-conventions.md`)
   and the evaluation practice (`interpretation/evaluation-practice.md`).
```

with:

```
2. Establish the memory conventions (`interpretation/memory-conventions.md`)
   and the evaluation practice (`interpretation/evaluation-practice.md` —
   how a result is READ: a working judge over a dead product role, a fake
   prefix over a full journey, a small bed over scale; the admission gate
   itself is in `verification/evaluation-readiness.md`).
```

### Edit 3 — Step 7 (Smoke test), after item 2

Insert a new item 3 (renumber the current item 3 to 4):

```
3. Run the installed gates THE WAY THEIR RUNBOOK DOCUMENTS THEM (`python
   scripts/<gate>.py --check`, then `make verify`) and read each gate's own
   verdict line; an import-only test does not count
   (`verification/evaluation-readiness.md` §6). If the repo serves a
   surface, run one offline functional trial against a small start state
   with fake AI roles and bank its receipt (§4 shape) as the installation's
   first evaluation artifact. Falsify the admission gate by planting the
   three rejections of `verification/falsification.md` rule 7.
```

## README.md

### Edit 4 — pillar table, `verification/` row

Replace the row's Contents cell:

```
24 deterministic gate scripts (one-way ratchets, secret scanning with a working-tree leg, traceability, planning-doc teeth), the verify portfolio, falsification norms, CI in the pinned/secret-gated regime, lander duties for landing trains
```

with:

```
24 deterministic gate scripts (one-way ratchets, secret scanning with a working-tree leg, traceability, planning-doc teeth), the verify portfolio, falsification norms, evaluation readiness (pre-flight smoke, offline functional trial and AI evaluation kept apart, one receipt schema), CI in the pinned/secret-gated regime, lander duties for landing trains
```

### Edit 5 — pillar table, `interpretation/` row

Replace `evaluation practice (persona loops, state parity, honest metrics)`
with `evaluation practice (what each evaluation type proves, intended
product mode, state parity, honest metrics)`.

## user-level/README.md

No edit needed from PR4.
