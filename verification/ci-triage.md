# CI triage — self-healing CI as a managed lane class

## 1. Managed lane class

A CI-red lane reads the latest failed workflow run on the repository's
default branch, classifies every failed job, and prepares exactly the next
local action. It is diagnosis and fix-lane preparation, not landing
authority. The lane never reruns CI, never pushes, and never treats a rerun
button as a fix. It prints any host rerun command for an operator to review.

The generic entry point is:

```
python3 verification/gates/ci_triage.py \
  --workflow <workflow-name> --branch <default-branch> \
  --idle-check <idle-check-executable> --test-command <test-executable> \
  --delta-dir <output-directory> [--known-flakes <regex-file>] [--json]
```

`--gh <executable>` injects the host CLI boundary. Tests always bind a fake
executable or call the Python API with an injected runner, so they never touch
the network.

## 2. Inputs and run comparison

The script asks `gh run list` for the two newest red runs of the named
workflow on the named branch. It reads the jobs of the latest run and, when
present, the previous run. The result includes three sorted job-name sets:
`added` (failed now only), `persisting` (failed in both), and `resolved`
(failed previously only). This is a diff of failed sets, not a comparison of
log text or total job counts.

The workflow and branch are parameters. The script does not infer a branch
from a repository-specific name, and a missing red run is a refusal rather
than an empty report.

## 3. Classification table

Classification is ordered; the first matching row owns the job.

| Class | Evidence | Action |
|---|---|---|
| `cancelled` | host conclusion is cancelled | print `gh run rerun <run-id> --failed`; do not execute it |
| `null-job` | no start/completion timestamps or no steps | escalate to the workflow owner |
| `known-flake` | job name or failed log matches a regex in the supplied flake file | cite the matching regex |
| `environment` | failed log carries a runner, network, disk, rate-limit, timeout, service, or infrastructure signature | escalate to the environment owner |
| `real` | none of the rows above matches | reproduce its extracted test IDs locally, then write a fix-lane delta |

One non-comment regex per line makes the known-flake file reviewable. A bad
regex is a refusal. Classification never quarantines or creates a flake; it
can only cite an existing entry.

## 4. Local reproduction and action boundary

Only `real` test IDs are passed to the local test executable. Before the
first local test, the configured idle-check executable must exit zero; a red
idle check stops all reproduction and delta writes. Cancelled, null, flake,
and environment jobs are never smuggled into a broad local suite.

Each reproduced real job gets one Markdown delta in `--delta-dir`, with
numbered `Lane header`, `Measurement baseline`, and `Task` sections following
`../planning/lane-brief-template.md §3`'s task shape. It records the workflow
run, head, job, exact test IDs, and reproduction exit, and asks the next lane
to preserve the criterion and attach red-to-green proof. Writing the delta is
the only repository-independent mutation.

## 5. Safety and output contract

Text output shows the failed-set diff, each class and action, the printed-only
rerun command, and the explicit statement that CI was not rerun and no push
was performed. `--json` exposes `run`, `previous_run`, `failed_set_diff`,
`jobs`, `rerun_command`, `deltas`, and `safety` with the same meaning.

The script invokes only `gh run list`, `gh run view ... --json jobs`, and
`gh run view ... --job ... --log`. There is no `gh run rerun`, `git push`, or
host mutation path in the implementation.

## 6. Provenance and what is still provisional

This managed class generalizes the source factory's watch-and-report CI mode
using the self-healing loop in issue 23: classify before spending, reproduce
the smallest real failure, and create a bounded lane rather than repeatedly
rerunning a climbing failure. `test_ci_triage.sh` uses one fixture per class,
checks the failed-set diff, proves idle refusal prevents local work, and
checks the delta shape. Environment signatures and test-ID grammars are
generic defaults and remain provisional for stacks with different logs.
