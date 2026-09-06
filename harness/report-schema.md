# Report schema (every lane, no matter how it exits)

```yaml
lane: <name>
run_id: <run-id>    # the launcher's $LANE_RUN_ID — binds this report to ONE run
status: built | parked | blocked | refused | failed
branch: <branch>
head_sha: <sha>
files_touched: [...]
gates:
  - command: <exact command>
    result: <pass|fail + concise diagnostic>
pregate_clean: true|false
choices:            # MANDATORY self-report for the choices audit
  - <each decision made beyond the brief — one line each; "none" only for trivial lanes>
proof: <exact command + fresh output — never a hedge phrase>
report: <root cause / what was built / what remains>
park:               # only when parked
  reason: ...
  resume_checklist: ...
```
The terse handback fields (measurements, revision table, proof owner, choice
verdicts) are defined by `planning/execution-contract.md` (introduced by
PR1); this file owns only the run binding and the two liveness surfaces.

**Run binding.** A report is a deliverable only for the run whose id it
carries, and only when it was written after that run started; `status` is the
closed set above because the launcher parses it. The report lands at
`$LANE_RESULT_PATH` (exported by the launcher, run-scoped — never a retyped
literal path). A read-only run prints the same report on stdout between the
documented markers and the wrapper writes it (`harness/run-lifecycle.md` §8).
Validity and the verdict table: `harness/run-lifecycle.md` §5.

Sentinel (`<lane>.sentinel.json`, in `$LANE_SENTINEL_DIR`) is updated at every
leg boundary so a slow-but-alive lane is never read as stalled; watchers must
prove liveness AND deliverable (a sentinel's presence is not production).
Stale exit-files from earlier rounds were a known trap; `run-lifecycle.md`
§2/§5 closes it — every receipt is named and stamped by run id, so an earlier
round's exit 0 cannot be read as this round's.
