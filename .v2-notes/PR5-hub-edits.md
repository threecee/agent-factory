# PR5 — hub-file edits (to be integrated by the hub owner)

PR5 does not edit `INSTALL.md`, `README.md` or `user-level/README.md`. The
exact edits it wants in them are below, verbatim. Each points at the rule's
single home (`harness/artifact-bank.md`); none duplicates it.

## INSTALL.md

### Step 3 — Interpretation pillar, item 2

Replace:

```
2. Establish the memory conventions (`interpretation/memory-conventions.md`)
   and the evaluation practice (`interpretation/evaluation-practice.md`).
```

with:

```
2. Establish the memory conventions (`interpretation/memory-conventions.md`)
   and the evaluation practice (`interpretation/evaluation-practice.md`).
   Evaluation practice presumes an artifact bank: every full evaluation runs
   on an isolated copy of a banked pristine source, never on the source and
   never on leftover state (`harness/artifact-bank.md` §3, §6).
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
1. Copy `harness/launch_lane.sh` to your orchestration scratchpad. Follow
   `harness/worktree-ritual.md` (worktree from a pinned SHA, symlinked
   venv/env/node_modules, one lane one writer, the wrapper commits — coding
   CLIs often cannot commit in linked worktrees; bank gitignored valuables
   before teardown) and `harness/report-schema.md` (sentinel + structured
   report + mandatory `choices:` self-report + circuit breakers).
2. Establish the artifact bank (`harness/artifact-bank.md`). Write the §10
   table into the repo's operations doc: bank root (chosen at user level),
   what counts as durable, the inventory of every config key / manifest
   field / database column that stores a path, the seed and its hash, the
   renewal cadence, the role names the receipt reports, retention. Then run
   `sh harness/examples/copy-isolation.sh` and read its output: it is the
   red→green shape your own isolation check must reproduce against the
   product's real path inventory. A factory whose pristine acceptance is
   "the manifest hashes match" is not installed.
```

### Step 7 — Smoke test, item 2

Append after the existing sentence ending "history is HARD).":

```
   If the repo has any evaluation or demo that runs against an instance:
   build one source from the seed, make two copies, plant an external path
   in one recorded reference and confirm the isolation check refuses it
   (`harness/artifact-bank.md` §3); confirm the source's hash is unchanged
   after a run on a copy (§6).
```

## README.md

### "Shared infrastructure" paragraph

Replace:

```
Shared infrastructure: **`skills/`** (35 vendored, hash-locked agent skills),
**`harness/`** (lane launcher, worktree ritual, board bootstrap, report
schema), **`user-level/`** (what goes into `~/.claude` so the factory works
from any checkout).
```

with:

```
Shared infrastructure: **`skills/`** (35 vendored, hash-locked agent skills),
**`harness/`** (lane launcher, worktree ritual, board bootstrap, report
schema, the artifact-bank contract — pristine acceptance, isolated copies,
receipts that tell a deliberate fake from a promised-but-failed role),
**`user-level/`** (what goes into `~/.claude` so the factory works from any
checkout, including the local bank root).
```

### Core-loop diagram, line `→ board sweep (Done + archive) → evaluation → findings → new board items`

Replace with:

```
  → board sweep (Done + archive) → evaluation on an isolated bank copy
    → findings → new board items
```

## user-level/README.md

Append as item 4:

```
4. **Artifact bank root:** choose one durable directory outside every
   repository and outside every scratchpad (e.g. `~/<project>-bank/`) and
   record it in the repo's operations doc per `../harness/artifact-bank.md`
   §10. The bank is where evaluation sources, run output, receipts and
   evidence bundles live; a scratchpad or a worktree is never storage. The
   root is a user-level choice because it is a property of the machine, not
   of the repository.
```
