# Run lifecycle — dispatch and monitoring as one auditable chain

This file is the home of every rule below (§1–§10); lane briefs and the other
harness docs cite these §-numbers. `harness/launch_lane.sh` is the mechanism
that implements them and `harness/tests/test_launch_lane.sh` is the proof that
it does. The launcher is repo-agnostic: it knows no path, port, project id,
provider, model or credential — every one of those is a parameter (§3).

## 1. Three questions, never one

A launcher that returns quickly proves nothing: the agent may never have
started. An exit code 0 proves nothing either: the agent may have written no
report. Every judgement about a run answers three separate questions from
three separate pieces of evidence:

| Question | Evidence | Never inferred from |
|---|---|---|
| Did the process start? | the **start receipt**: `cli_pid`, `started_at`, and the executable identity actually observed for that pid | the launcher's return code |
| Is it alive? | the **process identity check** (§6) on the pid in the start receipt | a sentinel's presence, a log's size |
| Is there a verified deliverable? | a **report bound to this run** (§5): right `run_id`, written after `started_at`, schema status | exit 0, "done" in the log |

A sentinel (`harness/report-schema.md`) answers "is it making progress";
it answers none of the three. Watchers read the three answers — the `verdict`
subcommand prints them — before considering a re-dispatch.

## 2. Run identity

One dispatch is one **run id**. The lane name is not an identity: the same
lane is dispatched again after a park, a rename, a second round or a new
session, and each of those is a new run with its own receipts. Every file a run
produces is named `<lane>.<run-id>.*` inside `LANE_RUN_DIR`:

| File | Written by | Content |
|---|---|---|
| `<lane>.<run-id>.start` | launcher, then runner | key=value lines, appended, last occurrence wins: `run_id`, `worktree`, `brief_sha256`, `cli_name`, `detach`, `state` (`dispatched → delayed → started`, or `refused` + `refused_reason`), `runner_pid`, `runner_pgid`, `cli_pid`, `cli_comm_observed`, `head_at_start`, `started_at`, `started_epoch` |
| `<lane>.<run-id>.log` | the CLI | stdout + stderr, stdin closed |
| `<lane>.<run-id>.result.md` | the CLI (write mode) or the runner (read-only, §8) | the report, per `harness/report-schema.md`, carrying `run_id:` |
| `<lane>.<run-id>.exit` | runner, atomically, **last** | `run_id`, `ended_at`, `deliverable`, `report_status`, `rate_limited`, `bank_path`, and as the final line `LANE_EXIT=<code>` |
| `<lane>.<run-id>.runner.log` | runner | the launcher's own diagnostics |

Rules:

1. A run id is single-use; `start` refuses an id whose start receipt exists.
2. The same id names the start, the stdout extraction, the report and the
   exit. It appears *inside* every receipt (`run_id=`) and inside the report
   (`run_id:`), so a file moved to the wrong name is still attributable.
3. A receipt without this run's id is not evidence for this run (§5).
4. Two runs of two lanes never share a file: two lanes once ran full suites
   whose launchers wrote the same `full_suite.log`/`.exit`, and one lane's
   gated push read the *other* lane's return code as its own. Naming by
   lane and run id is the fix; attributing by pid is the fallback when a
   collision is already live.

## 3. Environment contract — parameters, not literals

The launcher validates this contract **before** anything starts and refuses
with exit 2 naming the missing variable or file. Nothing is discovered at
handback. (A lane once derived its result path from another variable because
the dispatcher had exported one of the two — the whole contract is validated
at start now.)

Required for `start`:

| Variable | Meaning |
|---|---|
| `LANE` | lane name, `[A-Za-z0-9._-]+` |
| `LANE_WORKTREE` | the lane's own worktree (`harness/worktree-ritual.md`); the CLI's cwd |
| `LANE_RUN_DIR` | where receipts go (the orchestration scratchpad, or a per-run directory); created if missing |
| `LANE_BRIEF` | the brief file; its sha256 is recorded in the start receipt |
| argv after `--` | the CLI invocation, verbatim, with placeholders |

Optional, with defaults:

| Variable | Default | Meaning |
|---|---|---|
| `LANE_RUN_ID` | `<lane>-<UTC stamp>-<pid>` | §2; pass an explicit id when the orchestrator plans attempts (`w7-2`) |
| `LANE_DELAY_S` | `0` | staggered start; still a start (§4) |
| `LANE_DETACH` | `auto` | `setsid` \| `python` \| `perl` \| `none`; `auto` picks the first available and **refuses** when none is (§4) |
| `LANE_MODE` | `write` | `read-only` extracts the report from stdout (§8) |
| `LANE_PIN_SHA` | unset | when set, HEAD of the worktree must match at start (§4) |
| `LANE_ARTIFACT_BANK` | unset | bank root; receipts are copied to `<bank>/<lane>/<run-id>/` (§9) |
| `LANE_RATE_LIMIT_REGEX` | a named-field pattern (§7) | the ONLY way a log line can mark a run rate-limited |
| `LANE_RESULT_BEGIN` / `LANE_RESULT_END` | `LANE-RESULT-BEGIN` / `LANE-RESULT-END` | stdout markers for read-only runs |
| `LANE_SENTINEL_DIR` | `LANE_RUN_DIR` | exported to the CLI for its sentinel |
| `LANE_RESULT_PATH` | `<run-dir>/<lane>.<run-id>.result.md` | exported to the CLI; where the report must land |
| `LANE_START_TIMEOUT_S` / `LANE_LOCK_TIMEOUT_S` | `30` / `600` | check-in and writer-lock budgets |

Placeholders substituted in every argv element: `{brief}` (contents),
`{brief_path}`, `{worktree}`, `{lane}`, `{run_id}`, `{result_path}`. Paths
with spaces are preserved because argv is passed as an array, never re-split.

The CLI sees `LANE`, `LANE_RUN_ID`, `LANE_WORKTREE`, `LANE_RUN_DIR`,
`LANE_SENTINEL_DIR`, `LANE_RESULT_PATH` in its environment; the brief tells
it to use those names, never a retyped literal path (long scratch paths get
mis-transcribed by models — a phantom sibling directory once collected
several lanes' reports).

**Credentials are not the launcher's business.** Log the CLI in before
dispatch, or export the provider variable in the shell that runs `start`; the
launcher never reads a `.env`, never greps a key file, and its `env`
subcommand prints only its own variables. A provider override (an alternate
model tier, a proxy) is just more argv.

Worked example — one lane, one run, a generic coding CLI whose headless form
is `<cli> exec --cd <dir> "<prompt>"`:

```sh
export LANE=mech LANE_RUN_ID=w7-1 \
       LANE_WORKTREE="$WT_ROOT/mech" LANE_RUN_DIR="$SCRATCH" \
       LANE_BRIEF="$SCRATCH/mech-brief.md" LANE_PIN_SHA="$PIN" \
       LANE_ARTIFACT_BANK="$BANK"
harness/launch_lane.sh start -- <cli> exec --cd "{worktree}" "{brief}"
#   → run_id=w7-1 state=started cli_pid=… start_receipt=… log=… exit_receipt=…
harness/launch_lane.sh wait 3600 && harness/launch_lane.sh verdict
#   → verdict=built | died | no-deliverable | … (exit code per §5)
```

## 4. Start: delay, writer lock, pin, detachment, stdin

1. **A delayed start is still a start.** `LANE_DELAY_S` staggers the CLI (a
   free-tier 429 storm is a real reason) but the start receipt says
   `state=delayed` with `delayed_until_epoch` at once, and `verdict` answers
   `delayed` (exit 11) until the CLI is observed — a delayed run is never
   invisible.
2. **The writer lock closes the commit/start race.** One lane, one writer
   (`harness/worktree-ritual.md`). The runner holds a per-worktree lock from
   the moment the delay elapses until the CLI exits, and the wrapper's commit
   runs under the same lock: `launch_lane.sh with-writer-lock -- git -C "$WT"
   commit …`. So a delayed start cannot begin while a commit is in progress,
   and a commit cannot begin while a CLI is writing. The lock is an atomic
   `mkdir` in `LANE_RUN_DIR`, keyed by the canonical worktree path, with the
   holder's pid inside; a dead holder is reclaimed, a live one is waited for
   up to `LANE_LOCK_TIMEOUT_S`, then the start is **refused** (`state=refused`,
   `refused_reason=writer-lock-timeout`) rather than started late beside
   whoever holds it.
3. **The pin is checked after the lock is held.** With `LANE_PIN_SHA` set,
   HEAD of the worktree must match (prefix allowed) or the start is refused
   with `head-moved: pinned …, found …`. The wrapper's order is therefore:
   commit → pin HEAD → validate the start receipt of the next run **before**
   any other writer gets the tree.
4. **Detachment is a new session, tried, not assumed.** The runner is spawned
   in its own session (`setsid` binary, `python3 -c 'os.setsid()'`, or
   `perl POSIX::setsid`, whichever `LANE_DETACH=auto` finds first). What that
   buys: SIGTERM/SIGHUP to the dispatcher's process group — the parent
   harness being torn down — does not reach the run, and the exit receipt
   still appears (§10, case 13 exercises exactly this). What it does not buy:
   surviving a machine sleep, a container teardown, or a SIGKILL of the whole
   login session. Hence the exit receipt is the only completion signal; never
   judge from a process you happen to still be watching, and never from a
   captured pipe status (`$PIPESTATUS` of a backgrounded wrapper reads blank).
   Two traps written down because both happened: (a) `setsid <cli> … &`
   nested *inside* a wrapper that then returns backgrounds the CLI within the
   wrapper's group and it is torn down with it — the tell-tale is a log that
   is never created; the launcher spawns the runner as the detached process
   itself. (b) `auto` finding no method is a refusal, not a silent fallback;
   `LANE_DETACH=none` is the explicit way to run undetached.
5. **stdin is closed** (`< /dev/null`). An open stdin makes some CLIs wait
   forever, which presents as a hung lane.
6. **Identity is observed at start.** After the CLI is spawned, the runner
   reads the executable name the kernel reports for that pid and records it
   (`cli_comm_observed`). A wrapper that expected `<cli>` and observed `sh`
   has a broken invocation, not a slow lane.

## 5. The exit verdict is run-bound

`launch_lane.sh verdict` reads THIS run's receipts and re-validates the report
at judgement time — it does not trust the exit receipt's own summary, and no
other run's report can satisfy this run id.

| Verdict | Exit | Condition |
|---|---|---|
| `<status>` (`built`, `parked`, …) | 0 | `LANE_EXIT=0` and a **valid** report |
| `running` | 10 | no exit receipt; the CLI pid presents the expected executable, or the runner is alive |
| `delayed` | 11 | no exit receipt; `state=delayed`; runner alive |
| `not-started` | 12 | no start receipt for this run id |
| `vanished` | 13 | no exit receipt and no live process — a dead spawn |
| `refused-start` | 14 | the runner refused (head moved, lock timeout) |
| `died` | 20 | non-zero `LANE_EXIT`, or `LANE_EXIT=signal:<name>` |
| `no-deliverable` | 21 | `LANE_EXIT=0` and no report at `LANE_RESULT_PATH` |
| `unbound-report` / `stale-report` | 22 | a report exists but carries another run id, or is older than this run's `started_epoch` |
| `invalid-report` | 23 | right run id, but no `lane:` or no schema `status:` |

A report is **valid** when it is non-empty, carries `run_id: <this run>`,
was modified at or after `started_epoch`, carries `lane: <this lane>` and a
`status:` from the closed set in `harness/report-schema.md`.

Worked example — old receipts cannot approve a new run:

```
run r1 of lane a: built, exit 0, report valid          → verdict a r1 = built (0)
verdict a r2 before r2 is dispatched                    → not-started (12)
r2 dispatched; r1's report copied to r2's result path;
  CLI exits 0 without writing                           → unbound-report (22)
r3's report written 1 s BEFORE r3 starts, right run_id → stale-report (22)
verdict a r1 afterwards                                 → still built (0)
```

Consequences for the watcher:

- Read the verdict before any re-dispatch. A re-dispatch is a new run id;
  the old run keeps its receipts, because a failed attempt's receipt is
  evidence for the choices audit and for the two-round breaker
  (`planning/execution-contract.md` §3–§6).
- `vanished` and `died` are the "subagent run died" breaker: re-dispatch once
  after confirming quiescence (`git diff` hashed twice), a second death STOPs.
- `no-deliverable` is not a success with a missing file; it is a lane that
  did not do the job. Its log is read, not its exit code.

## 6. Process identity: executable name + exact argv token

A lane process is identified by two facts and nothing else: the executable
basename the kernel reports for the pid (`ps -o comm= -p <pid>`, queried per
pid — a multi-column `comm` is truncated on macOS, and the Linux kernel
truncates `comm` to 15 characters) **and** an exact token in its argv (the
CLI's headless verb, e.g. `exec`). `launch_lane.sh running <cli-name> <token>`
implements it.

Never `pgrep -f "<cli> exec"` or any text match over command lines: the shell
that is inspecting, a watcher, a `sleep` whose comment mentions the command,
and the process-table command itself all contain that text. The source
factory's idle guard once refused an assembly because it matched the
orchestrator's own shell, which was gone seconds later. The descendant rule
survives translation — a test runner that descends from a lane process is
still the lane — but the local mechanics around it (port ranges, load limits,
what counts as idle) are the target repo's policy, not this file's.

## 7. Rate-limit classification is parsing, not matching

A digit string is not a status: `42906` contains `429`. The launcher marks a
run `rate_limited=yes` only when (a) `LANE_EXIT` is non-zero and (b) a log line
matches `LANE_RATE_LIMIT_REGEX`, whose default requires a **named field** —
`status=429`, `code: 429`, `HTTP/1.1 429` — with the number delimited on both
sides. Set the variable to your provider's documented error form; do not
widen it to a bare number.

A log match is never an exit verdict. Exit 0 with a valid report and a `429`
field in the log (a retry that succeeded) is `built`, `rate_limited=no`. A
`died` with `rate_limited=yes` takes the quota back-off path (never a tight
retry); a `died` with `rate_limited=no` is a plain death (§5).

## 8. Read-only runs: the wrapper is the writer

An investigation run in a read-only sandbox cannot write its report. Contract:
the CLI prints the report on stdout between `LANE_RESULT_BEGIN` and
`LANE_RESULT_END` (first begin, first end after it; anything after the end
marker is chatter, not report). The runner — the authorized writer — extracts
it to `LANE_RESULT_PATH`, validates it exactly as in §5 and banks it (§9).
`LANE_MODE=read-only` selects this; exit 0 without an extracted report is
`no-deliverable`, not a shrug. The brief for a read-only run states the two
markers and the required fields (`lane:`, `run_id:`, `status:`).

## 9. Durable receipts survive the worktree and the conversation

The scratchpad is session-scoped and disposable; a worktree dies at reaping.
Anything a later train, a review, or the owner would want again — receipts,
the log, the report, a measurement whose re-derivation is expensive — is
banked **as it is produced**, not at the end: a run that banks at exit banks
nothing when it is force-collected. With `LANE_ARTIFACT_BANK` set, the runner
copies the start receipt, log, report and exit receipt to
`<bank>/<lane>/<run-id>/` and records `bank_path` in the exit receipt. The
bank root is operator policy (`user-level/README.md`), a durable out-of-repo
directory; what goes there is decided by regeneration cost and auditability,
never by size. Never bank virtualenvs, caches, served-instance directories or
worker temp trees — all rebuildable. Copy, do not move, while any lane may
still read the original path. A new operator must be able to reconstruct a
run from the bank alone: the start receipt names worktree, brief hash, pin and
observed executable; the exit receipt names log, report and verdict.

`harness/artifact-bank.md` (introduced by PR5) owns the bank's own lifecycle
— pristine copies, isolation, renewal, retention. This section owns only
which run receipts go there and when.

## 10. What the test proves — and what it does not

`bash harness/tests/test_launch_lane.sh` (or `zsh …`) runs in ~15 s against a
fake CLI (a symlink to `/bin/sh` named `fakecli`, so the kernel reports the
identity `fakecli`), every path containing a space:

| Case | Proves | Section |
|---|---|---|
| 1 | a missing variable, a missing brief file, or no argv is refused with exit 2 naming it, before any file is written | §3 |
| 2 | two lanes dispatched concurrently in paths with spaces both deliver; logs never cross; the CLI's cwd is its worktree; placeholders keep spaces | §2, §3 |
| 3 | start receipt, log name, report and exit receipt all carry the same run id; a run id is single-use | §2 |
| 4 | non-zero exit is `died` with the exact `LANE_EXIT`; a log containing `42906` is not rate-limited | §5, §7 |
| 5 | exit 0 without a report is `no-deliverable` | §5 |
| 6 | a named `status=429` field with non-zero exit is `died` + `rate_limited=yes` | §7 |
| 7 | the same field with exit 0 and a valid report is `built`, not rate-limited | §7 |
| 8 | a new run id with only old receipts is `not-started`; an old report at the new path is `unbound-report`; a right-id report older than the start is `stale-report`; the old run's verdict is unchanged | §5 |
| 9 | the real `fakecli` pid is listed by identity; a `sh -c '… fakecli exec'` whose text says the same is not; the start receipt observed `fakecli`; a live run is `running` | §6 |
| 10 | a start delayed into a held writer lock (a simulated commit) begins only after the lock is released, and still delivers | §4 |
| 11 | a HEAD that does not match `LANE_PIN_SHA` is refused (no CLI log ever produced); a matching pin runs | §4 |
| 12 | read-only: the report is extracted from stdout, trailing chatter excluded, validated, and banked with the receipts; no markers means `no-deliverable` | §8, §9 |
| 13 | the dispatcher runs in its own session, is killed with SIGTERM then SIGHUP to its whole process group, and the run still writes its exit receipt with verdict `built`; the detach method used is printed; SKIP (never pass) when no method exists | §4 |

Falsification of the test itself (authoring run): three one-line mutations of
a scratch copy of the launcher — dropping the `run_id` check, widening the
rate-limit regex to a bare `429`, removing the writer lock — turned exactly
cases 8b, 4b and 10c red and nothing else.

What the test does **not** prove:

- **Detachment on every platform.** Case 13 exercises the method the host
  offers (the authoring run used `python3` on macOS, where no `setsid` binary
  exists; a Linux host takes the `setsid` binary). Run the test on the machine
  that will dispatch; the printed `detach method exercised:` line is the
  evidence.
- **The three operational traps as reproduced incidents.** The `42906`
  false-429, the delayed-start/commit race and the unwritable read-only
  report are recorded in the source factory's v2 extraction analysis as an
  orchestrator's night observations with **medium confidence as event
  sequences** — no raw log is attached. Here they are contract cases with
  tests, not claims that a specific incident was reproduced.
- **A real CLI's behaviour.** The fake CLI models the process contract
  (identity, stdin, exit, stdout, result path). Whether your CLI can write in
  a linked worktree, which verb it uses, or how it reports a rate limit is
  checked once per CLI, by hand, and written into the brief.
