# Report schema (every lane, no matter how it exits)

```yaml
lane: <name>
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
Sentinel (`<lane>.sentinel.json`) is updated at every leg boundary so a
slow-but-alive lane is never read as stalled; watchers must prove liveness
AND deliverable (a sentinel's presence is not production). Stale exit-files
from earlier rounds are a known trap — check mtimes against the current
round's start before reading verdicts.
