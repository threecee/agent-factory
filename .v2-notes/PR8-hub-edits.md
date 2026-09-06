# PR8 — edits to the shared hub files (apply at integration)

The hub files are not edited on this branch. Apply these verbatim.

## INSTALL.md

**Anchor:** end of `## Step 4 — Skills`, after the sentence "Write the
skill-routing table into the repo's operations doc (the template carries
it)."

**Insert:**

```
Three of the skills (`bulk-reader`, `log-triage`, `handback-digest`) are the
bounded bulk-read pilot. They are inert until you bind the commands and
variables in `harness/bulk-read-contract.md` §4 in the operations doc; they
register NO hook. Do not add a PreToolUse registration in this step.
```

**Anchor:** end of `## Step 5 — Harness`, after "(sentinel + structured
report + mandatory `choices:` self-report + circuit breakers)."

**Insert:**

```
Optional, measurement-gated: `harness/bulk-read-contract.md` — route large
reads through a cheaper worker. Bind its parameters (§4), run the worker-down
trial (§5) and the off/on pilot (§7) before registering the adapter (§8).
Installing the contract activates nothing.
```

## README.md

**Anchor:** the paragraph beginning "Shared infrastructure: **`skills/`**
(35 vendored, hash-locked agent skills), **`harness/`** (lane launcher,
worktree ritual, board bootstrap, report schema), ..."

**Replace** `**`harness/`** (lane launcher, worktree ritual, board
bootstrap, report schema)` **with**
`**`harness/`** (lane launcher, worktree ritual, board bootstrap, report
schema, and the measurement-gated bounded bulk-read contract)`.

(Leave the "35 vendored" count to whichever PR renumbers it; this PR adds
three skills.)

## user-level/README.md

**Anchor:** after item 3 ("**User-level skills:** ...").

**Insert as item 4:**

```
4. **Bulk-read worker and threshold (optional pilot):** if the repo has
   bound `harness/bulk-read-contract.md`, the worker chain, line threshold,
   path exemptions and the session disable variable are YOUR settings, set
   in your shell environment (default names `SHUNT_WORKERS`,
   `SHUNT_MIN_LINES`, `SHUNT_ALLOW`, `SHUNT_DISABLED`), never committed.
   Record the reason for each value and the date of the live probe that
   showed the worker answering (contract §3 rule 1). Registering the hook is
   a separate decision taken after the off/on pilot has numbers (§7); a
   fresh checkout registers nothing.
```
