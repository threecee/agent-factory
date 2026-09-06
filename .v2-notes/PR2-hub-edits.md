# PR2 — hub-file edits (to be integrated; NOT applied in this branch)

Hub files (`INSTALL.md`, `README.md`, `user-level/README.md`) are shared by
every v2 PR and are integrated later. The edits PR2 needs are written here
verbatim. Every rule stays at its home (`harness/run-lifecycle.md`,
`harness/worktree-ritual.md`, `verification/verify-portfolio.md`); the hubs
only point.

## INSTALL.md — Step 5 (replace the whole section)

Anchor: the heading `## Step 5 — Harness` through the end of its paragraph
(currently: "Copy `harness/launch_lane.sh` to your orchestration scratchpad. …
circuit breakers)."). Replace with:

```markdown
## Step 5 — Harness
1. Keep `harness/launch_lane.sh` where it is (it is repo-agnostic and takes
   everything as a parameter — worktree, run id, receipt directory, brief,
   the CLI argv, detachment, artifact bank). Run its test on the machine that
   will dispatch: `bash harness/tests/test_launch_lane.sh`. Read the printed
   `detach method exercised:` line — detachment is proven per host, not
   assumed (`harness/run-lifecycle.md` §4, §10).
2. Read `harness/run-lifecycle.md`. It owns dispatch and monitoring: run
   identity and receipts (§2), the environment contract (§3 — no built-in
   paths, no key reading; log the CLI in before dispatch), the run-bound exit
   verdict (§5), process identity by executable name + exact argv token (§6),
   rate-limit classification by named field (§7), read-only runs whose
   report the wrapper extracts from stdout (§8), and banking receipts as they
   are produced (§9). Set `LANE_ARTIFACT_BANK` to the durable root chosen in
   Step 6.
3. Follow `harness/worktree-ritual.md` (worktree from a pinned SHA, symlinked
   env dirs gitignored, one lane one writer under the launcher's writer lock,
   the wrapper commits — coding CLIs often cannot commit in linked worktrees,
   and the import-root proof for your stack) and `harness/report-schema.md`
   (report carrying `run_id`, sentinel, mandatory `choices:` self-report).
4. Parameterize the standing brief's paths as the launcher's environment
   names (`$LANE_RESULT_PATH`, `$LANE_SENTINEL_DIR`, `$LANE_RUN_ID`), never as
   literal scratch paths.
```

## INSTALL.md — Step 2 (append one item after item 4, "Read
`verification/falsification.md` …")

Insert as new item 5 (renumber the following items 5→6, 6→7):

```markdown
5. Add the import-root probe for your stack to the verify entry (before the
   full suite) and a runtime import-boundary test for your production entry
   points (`verification/verify-portfolio.md`, "Runtime import boundary";
   probes per stack in `harness/worktree-ritual.md`). Falsify both: point the
   root at the primary checkout and watch the probe refuse; add one excluded
   import and watch the boundary test go red.
```

## INSTALL.md — Step 7 item 1 (extend one sentence)

Anchor: "dispatch one lane from the standing brief, run the choices audit on
the handback,". Replace with:

```markdown
dispatch one lane from the standing brief through `harness/launch_lane.sh`
(read its `verdict` before touching the handback — `harness/run-lifecycle.md`
§5), run the choices audit on the handback,
```

## README.md — "Shared infrastructure" paragraph

Anchor: "**`harness/`** (lane launcher, worktree ritual, board bootstrap,
report schema)". Replace with:

```markdown
**`harness/`** (parameterized lane launcher with run-bound receipts and its
test, the run lifecycle, worktree ritual, board bootstrap, report schema)
```

## user-level/README.md — append item 4

```markdown
4. **Artifact bank root:** choose one durable, out-of-repo directory on the
   machine (not the scratchpad, not the worktree) and export it as
   `LANE_ARTIFACT_BANK` in every shell that dispatches lanes, so run
   receipts are banked as they are produced (`../harness/run-lifecycle.md`
   §9). The root is operator policy; what is banked is decided by
   regeneration cost, never by size.
```
