# PR10 — hub-file edits (to be integrated by the hub owner)

PR10 does not edit `INSTALL.md`, `README.md` or `user-level/README.md`
directly (shared hub files). The exact edits it needs are below; every rule
stays homed in `interpretation/investigation-practice.md`,
`verification/falsification.md` and
`verification/examples/identity-and-history.md` — the hubs only point.

## INSTALL.md

**Anchor:** Step 2 — Verification pillar, item 4, currently:

```
4. Read `verification/falsification.md` and apply it from day one.
```

**Replace with:**

```
4. Read `verification/falsification.md` and apply it from day one. Before
   writing any gate over stored evidence (rows, snapshots, receipts) or any
   progress meter that survives a retry, read
   `verification/examples/identity-and-history.md` and run its script once
   (`python3 verification/examples/identity_and_history.py`, then with
   `--plant count-all`): a gate must read what the consumer reads, and is
   falsified in both directions.
```

**Anchor:** Step 3 — Interpretation pillar, item 3, currently:

```
3. Read `interpretation/investigation-practice.md` — instrument-first is the
   default for every debugging lane.
```

**Replace with:**

```
3. Read `interpretation/investigation-practice.md` — instrument-first is the
   default for every debugging lane, and its "Identity and history" section
   is the default for any gate, count or plan that reads stored evidence.
```

## README.md

**Anchor:** the three-pillars table, `verification/` row. Insert after
"falsification norms," (verbatim cell text is long; insert the phrase, do
not re-author the row):

```
falsification norms (with a runnable identity-and-history example: gates
follow the consumer's identity, falsified in both directions),
```

## user-level/README.md

No edit required by PR10.
