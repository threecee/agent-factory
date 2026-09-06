# PR3 — requested edits to the shared hub files

PR3 does not edit `INSTALL.md`, `README.md` or `user-level/README.md`. The
integrator applies the edits below verbatim.

## INSTALL.md

### Step 2 — Verification pillar, item 6

Replace:

```
6. Bind everything into `make verify`. Run it. Green before the next step.
```

with:

```
6. Bind everything into `make verify`. Build every product the suite reads
   BEFORE running it (`verification/verify-portfolio.md`, "Build inputs
   exist before verify"), then run it. Green before the next step.
```

### Step 5 — Harness

Replace the whole step body:

```
Copy `harness/launch_lane.sh` to your orchestration scratchpad. Follow
`harness/worktree-ritual.md` (worktree from a pinned SHA, symlinked
venv/env/node_modules, one lane one writer, the wrapper commits — coding CLIs
often cannot commit in linked worktrees) and `harness/report-schema.md`
(sentinel + structured report + mandatory `choices:` self-report + circuit
breakers).
```

with:

```
Copy `harness/launch_lane.sh` to your orchestration scratchpad. Follow
`harness/worktree-ritual.md` (worktree from a pinned SHA, symlinked
venv/env/node_modules, one lane one writer, the wrapper commits — coding CLIs
often cannot commit in linked worktrees) and `harness/report-schema.md`
(sentinel + structured report + mandatory `choices:` self-report + circuit
breakers).

Fill in `harness/train-plan.md` and commit it as `docs/train-plan.md`: the
exact command per landing step (§2) and the resource contract (§3 — port
range, agent-CLI binary and subcommand token, load threshold and wait
window, hard stops). Run its §7 falsification list once on a throwaway
train. No assembler script ships; land from the plan by hand first
(`verification/lander-duties.md` §6).
```

### Step 7 — Smoke test, item 1

Replace:

```
1. Create one trivial board item, write a mini-spec, dispatch one lane from
   the standing brief, run the choices audit on the handback, assemble a
   single-lane train, run full verify, land, sweep the board.
```

with:

```
1. Create one trivial board item, write a mini-spec, dispatch one lane from
   the standing brief, run the choices audit on the handback, assemble a
   single-lane train from `docs/train-plan.md` (the install exception —
   independent ready lanes otherwise share a train, `lander-duties.md` §2),
   run full verify, land, sweep the FULL board (`board-protocol.md`,
   "Authority, pagination and derived views").
```

## README.md

### "Shared infrastructure" paragraph

Replace:

```
**`harness/`** (lane launcher, worktree ritual, board bootstrap, report
schema)
```

with:

```
**`harness/`** (lane launcher, worktree ritual, board bootstrap, report
schema, the train plan with its resource contract)
```

### "The core loop" block, the landing-train lines

Replace:

```
  → landing train: --no-ff pinned SHAs → cross-checks → cheap gates
    → FULL local verify green → push main → CI deploys
```

with:

```
  → landing train (independent ready lanes share one): --no-ff pinned SHAs
    → cross-checks → build → cheap gates → resource check
    → FULL local verify green → push main → CI deploys
```

## user-level/README.md

No edit requested by PR3. (PR11 introduces the landing-authorization
example that `lander-duties.md` §1 step 10 and `train-plan.md` §5 point to.)
