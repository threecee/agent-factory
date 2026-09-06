---
name: log-triage
description: Extract failing tests, assertion messages, tracebacks, and red gate results from a large run or verify log without reading its full text. Use when a bounded-read hook blocks a read of a log matching the repository's log globs over the configured line threshold, or when the orchestrator must triage a long verify or lane-run log. Names failures, never causes.
---

# Log Triage

The log-triage command is the bulk reader specialised for factory logs: it
asks the worker chain to list only actionable failures with exact source
line numbers, discarding passing-test noise. The rules live in
`harness/bulk-read-contract.md`; this skill is the invocation.

## Invocation

```sh
{{LOG_TRIAGE_CMD}} <path-to-log>
```

- Only files matching the repository's log globs (`{{LOG_GLOBS}}`, for
  example `*-lane.log` and `verify-*.log`) route here from the hook; other
  large files route to `bulk-reader`. Invoking this skill by hand on any
  large log is fine.
- Output is structured bullets: exact line number, exact test/gate name,
  assertion text or traceback line — never a fix or an architecture opinion.
- Same input boundary and exit codes as `bulk-reader` (2 refused, 3 every
  worker failed, nothing echoed); `{{ALLOW_EXTERNAL_FLAG}}` under the same
  condition.
- Duplicated test names, retries and re-runs inside one log are where line
  numbers drift: confirm each listed line with a bounded read before you cite
  it in a handback or a ledger entry (contract §3 rule 4, §6).

## When NOT to use this

Don't use it to decide the fix — it names failures, not causes. Root-cause
the listed failures yourself with `skills/systematic-debugging` once you have
the list. A worker bullet that proposes a cause is out of contract; narrow
the question.

## Escape hatch

A targeted read or `sed -n` slice under the threshold always passes without
invoking this skill; `{{SHUNT_ALLOW}}` exempts named paths;
`{{SHUNT_DISABLE}}` disables the hooks for the session when every configured
worker is unavailable (contract §3 rule 5, §5).

## Parameters

`{{LOG_TRIAGE_CMD}}`, `{{LOG_GLOBS}}`, `{{ALLOW_EXTERNAL_FLAG}}`,
`{{SHUNT_ALLOW}}` and `{{SHUNT_DISABLE}}` are bound in the repository's
operations doc from `harness/bulk-read-contract.md` §4.
