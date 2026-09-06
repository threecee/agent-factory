# Train plan — the project's commands and resource contract

This file is a TEMPLATE the installing agent fills in once against the
target repo and commits as `docs/train-plan.md` (or the project's equivalent).
It owns two things: the exact commands a landing train runs, in order, and
the resource contract that decides whether the heavy step may start. The
ORDER and the batch/resume/sweep rules are owned by
`../verification/lander-duties.md`; this file never restates them.

No assembler script ships with the factory (lander-duties §6). Land at least
one train by hand from this plan before scripting it.

## 1. Identity

| Field | Value (fill in) | Rule |
|---|---|---|
| Primary checkout | `<abs path>` | The checkout whose shared environment lanes link to (worktree-ritual.md) |
| Worktree root | `<abs path>` | Where train worktrees are created: `<root>/<train>` |
| Train branch | `train/<name>` | One branch per train, from the current origin/main SHA |
| Artifact directory | `<abs path>` | Receipts (§4) are written here; bank them if they must outlive the session (artifact-bank.md, introduced by PR5) |
| Run id | `<train>-<attempt>` | Attempt counts from 1; a resumed run is the next attempt (lander-duties §3) |
| Import root | `<how the package under test is resolved>` | e.g. `PYTHONPATH=<wt>/src`, `NODE_PATH`, a workspace `file:` link — the probe in §2 must be able to print the resolved path |

## 2. Command table

Every row is one exact command run from the train worktree unless the row
says otherwise. "Verdict" is how the lander reads the result: a direct exit
code from the foreground command, or a receipt file for a backgrounded step.
Fill every row; a row the project does not need says `none — <why>` so a
reader can tell "not applicable" from "forgotten".

| Step (lander-duties §1) | Command | Verdict | Notes |
|---|---|---|---|
| 1 fetch + worktree | `git -C <primary> fetch -q origin && git -C <primary> worktree add -q -b train/<name> <root>/<name> origin/main` | exit code | Then link the shared environment exactly as worktree-ritual.md says |
| 2 merge each boarder | `git merge --no-ff <sha> -m "train(<name>): board <lane> (<sha>)"` | exit code; a conflict stops the train | Full 40-char SHA, resolved beforehand with `git rev-parse --verify <lane-branch>^{commit}` |
| 3 cross-checks | `<one migration head>` · `<number registry consistent>` · `<count literals = union>` · `<generated artifacts regenerated once>` | exit code each | List every project-specific cross-check; see lander-duties §1 step 3 |
| 5 build | `<build command>` then `<stamp/manifest command>` | exit code | Runs on EVERY train, regardless of which files changed (verify-portfolio.md, "Build inputs exist before verify") |
| 6 cheap gates | ordered list: `<format check>` · `<lint ratchet>` · `<type ratchet>` · `<complexity/dependency ratchet>` · `<secret scan>` · `<SAST>` · `<planning teeth>` · `<generated-drift check>` | exit code each, first red stops | Same commands as the lane pregate block plus the drift checks; never a lowered baseline |
| 7 import-root probe | `<command that prints where the package under test was loaded from>` | printed path must resolve INSIDE `<root>/<name>` | Python: `python -c 'import <pkg>; print(<pkg>.__file__)'`; Node: `node -p "require.resolve('<pkg>')"` |
| 8 resource check | the §3 contract | refusal stops the train | Run at step 1 as well |
| 8 full verify | `<make verify or equivalent>` under the harness's detached-launch pattern (run-lifecycle.md, introduced by PR2) | `<run-id>.exit` (§4) | Never judged from a pipe or wrapper |
| 10 push | `<verify verdict check> && git push origin HEAD:main` | exit code | One mechanical statement; landing authorization (user-level, introduced by PR11) decides whether the lander may push unattended |
| 11 sweep | `<board sweep commands>` (planning/board-protocol.md) · `<NUMBERS flip>` · `git -C <primary> merge --ff-only origin/main` · `git worktree remove …` | exit code each | Reap only after the ancestor check |

## 3. Resource contract

The check answers one question: may the heavy step start NOW on this
machine? It is run at train creation and again immediately before the heavy
step. It is a snapshot; it is not a lock (§3.6).

### 3.1 Hard stops — never overridable, never delayed

| Condition | How it is detected | Fill in |
|---|---|---|
| A served instance is listening in the project's port range | `lsof -nP -iTCP:<range> -sTCP:LISTEN` (or the platform equivalent) returns any row | `<range>`: the range the project's serve/standup/eval scripts bind |
| A test runner is running UNDER a delegated agent lane | a process whose command matches the test runner (`pytest`, `vitest`, …) and whose ancestor chain contains a live agent lane (§3.3) | `<test runner names>` |
| The detection apparatus itself is unavailable | `ps`/`lsof` missing or erroring | fail CLOSED: refuse and say the apparatus failed, never "idle" |

A hard stop is re-checked before EVERY load sample in the wait window
(§3.4). `--force` cannot override or delay it.

### 3.2 Soft stops — overridable with a logged warning

| Condition | Rule |
|---|---|
| A delegated agent lane is live (§3.3) but not running tests | refuse by default; `--force` overrides and prints `[FORCED IDLE WARNING] <reason>` into the run log |
| Sustained load above the threshold (§3.4) | wait up to the bounded window, then refuse; `--force` overrides after the same warning |

### 3.3 Process-match criteria — what counts as a live agent lane

1. **Executable identity first.** The process's executable basename
   (`ps -o comm=`) equals the agent CLI's binary name (`<binary>`, e.g. the
   coding CLI the lanes are launched with).
2. **Exact subcommand token.** The argv of that process, split on
   whitespace, contains the lane subcommand as ONE token (`<token>`, e.g.
   `exec`). A substring match is not a match.
3. **Text mentions are not lanes.** A shell, a watcher, an editor, or the
   process-table command itself whose command TEXT merely contains the words
   is NOT a lane. `pgrep -f "<binary> <token>"` violates this rule — it once
   refused a train on the orchestrator's own inspecting shell, which was gone
   seconds later.
4. **Descendants count for the hard stop.** A test runner anywhere below a
   matched process is the hard condition in §3.1; the matched process alone
   is the soft condition in §3.2.
5. **Process names carried by the harness.** The binary name and token are
   parameters (fill them in below); a project with two coding CLIs lists both.

Fill in: `<binary>` = ____ ; `<token>` = ____ ; `<test runner names>` = ____.

### 3.4 Load policy

| Parameter | Fill in | Source-factory value (a local choice, not a default) |
|---|---|---|
| Threshold | `<load average limit>` | half the core count |
| Burst rule | if load1 > threshold and load5 ≤ threshold → treat as a short burst and proceed | same |
| Sustained rule | if load1 AND load5 > threshold → wait | same |
| Wait window | `<attempts> × <seconds>` | 6 × 20 s |
| Per-sample ritual | hard stops (§3.1) → process match (§3.3) → load sample; in that order, every sample | same |
| After the window | refuse; `--force` overrides with the warning | same |

The train's own cheap gates raise load1 just before the pre-verify check;
that is exactly the burst the load5 rule exists for. A slow-rising load from
lanes that started recently has a LOW load5 — the process-match rule, not
the load rule, catches those.

### 3.5 What the check prints

`uptime`, the numeric load1/load5/core count/threshold, every matched
process id with its comm and argv, every listener row, and each wait step
`wait <n>/<attempts> for <seconds>s`. All of it goes into `<run-id>.log`
(§4). A refusal names the condition verbatim
(`refused: a server is listening in TCP <range>`; `refused: <binary> is
running <test runner> (pid …)`), never a bare non-zero exit.

### 3.6 What the contract does not claim

- It is a snapshot at probe time. A lane, standup or eval that starts after
  the probe is invisible to it. The lander closes that window by procedure
  (lander-duties §4): nothing is dispatched or served while a train is
  between its pre-verify check and its verdict.
- It is not a mutex. Two landers on one machine are not coordinated by it;
  serialization is a rule of the lander, not a property of the check.
- A green probe followed by a red verify is still adjudicated
  (verify-portfolio.md): starvation looks like a product failure.

## 4. Receipts

| Artifact | Path | Rule |
|---|---|---|
| Run log | `<artifacts>/<run-id>.log` | Every command, its label and its output; the shared env file's CONTENTS never appear in it |
| Exit receipt | `<artifacts>/<run-id>.exit` | Lines `EXIT=<code>`, `BASE=<full sha>`, `HEAD=<full sha>`, `LOG=<path>`; written atomically (temp file + rename) when the run ends, whatever the outcome |
| Overwrite policy | never | A run id that already has a log or exit file is refused; the next attempt gets the next run id |

A verdict is read from the exit receipt's `EXIT=` line and nothing else. A
missing receipt means the run did not finish — not that it failed, not that
it passed.

## 5. Local policy the project chooses

| Item | Fill in |
|---|---|
| Priority levels and which one qualifies for the single-lane blocker exception (lander-duties §2) | e.g. "P1 = blocks owner-approved work"; who may declare it |
| Port range for served instances | see §3.1 |
| Load threshold and wait window | see §3.4 |
| Agent CLI binary and subcommand token | see §3.3 |
| Derived progress page, if any (lander-duties §5, board-protocol.md) | page URL/path, or `none` |
| Landing authorization for unattended push | `none` until the owner chooses one (user-level, introduced by PR11) |

## 6. Filled-in example (a TypeScript service with a docs site)

The repo is not the source factory; every value is a local choice.

| Step | Command |
|---|---|
| 1 | `git -C ~/src/app fetch -q origin && git -C ~/src/app worktree add -q -b train/t-42 ~/src/app-trains/t-42 origin/main` then `ln -sfn ~/src/app/node_modules ~/src/app-trains/t-42/node_modules` (lockfiles equal) |
| 2 | `git merge --no-ff 3f1c…e9 -m "train(t-42): board api-validation (3f1c…e9)"` ×4 |
| 3 | `npm run migrate:heads` (one head) · `node scripts/check-numbers.mjs` · `npm run docs:build -- --check` |
| 5 | `npm run build` then `node scripts/stamp-dist.mjs` — also when only `docs/` changed |
| 6 | `npm run format:check` · `node scripts/lint-ratchet.mjs` · `npx tsc -b` · `node scripts/deps-ratchet.mjs` · `gitleaks detect --config .gitleaks.toml` · `node scripts/check-backlog.mjs` |
| 7 | `node -p "require.resolve('@app/core')"` → must print a path under `~/src/app-trains/t-42/` |
| 8 | contract: range `4300-4399`; binary `codex`, token `exec`; test runners `vitest`, `playwright`; threshold `cores/2`; window `6 × 20 s` |
| 8 | `setsid npm run verify > ~/trains/t-42-1.log 2>&1; echo "EXIT=$?" > ~/trains/t-42-1.exit` (the actual pattern is run-lifecycle.md's) |
| 10 | `grep -qx 'EXIT=0' ~/trains/t-42-1.exit && git push origin HEAD:main` |
| 11 | `gh project item-list 7 --owner acme --limit 200 --format json` → sweep; `git -C ~/src/app merge --ff-only origin/main`; `git worktree remove ~/src/app-trains/t-42` |

Resume after a conflict in step 2: resolve, `git commit`, then run from
step 3 with run id `t-42-2`; `t-42-1.exit` stays on disk with `EXIT=1`.

## 7. Falsify the plan before trusting it

Do each once, on a throwaway train, and record the outcomes in the install
smoke test:

1. Start a listener in the port range (`python3 -m http.server <port>` or
   `nc -l <port>`); the check must refuse and name the range. Stop it.
2. Run `sh -c 'sleep 60 # <binary> <token>'` in another terminal; the check
   must NOT refuse (text mention, §3.3 rule 3).
3. Run the real agent CLI in a scratch directory with the lane subcommand;
   the check must refuse as a soft stop; `--force` must proceed with the
   warning in the log.
4. Run the resumed form on a tree with an uncommitted file; it must refuse
   with the "commit the conflict resolution" message.
5. Re-run a finished run id; it must refuse to overwrite the receipt.

## 8. Provenance and what is provisional

The contract above is distilled from one source factory where a
repository-owned assembler executed it across roughly ten multi-lane trains,
including a fourteen-lane train with four conflicts and a resumed
seven-lane train. Its conflict/resume and process-identity findings were
fixed and re-exercised there. It has NOT yet been exercised in a second
repository; that trial is the acceptance for any executable port
(INSTALL step 7 in this package runs the plan by hand).
