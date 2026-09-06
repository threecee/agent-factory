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
| Artifact directory | `<abs path>` | Receipts (§4) are written here; bank them if they must outlive the session (`run-lifecycle.md` §9 says which receipts and when; `harness/artifact-bank.md` owns the bank's lifecycle) |
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
| 4 choices ledger | `git add <choices dir>/<train>.md && git commit -m "train(<name>): choices protocol"` | exit code | The protocol names every boarder's full SHA (lander-duties §1 step 2); it is amended and re-committed on every resumed attempt |
| 5 build | `<build command>` then `<stamp/manifest command>` | exit code | Runs on EVERY train, regardless of which files changed (verify-portfolio.md, "Build inputs exist before verify") |
| 6 cheap gates | ordered list: `<format check>` · `<lint ratchet>` · `<type ratchet>` · `<complexity/dependency ratchet>` · `<secret scan>` · `<SAST>` · `<planning teeth>` · `<generated-drift check>` | exit code each, first red stops | Same commands as the lane pregate block plus the drift checks; never a lowered baseline |
| 7 import-root probe | `<command that prints where the package under test was loaded from>` | printed path must resolve INSIDE `<root>/<name>` | Python: `python -c 'import <pkg>; print(<pkg>.__file__)'`; Node: `node -p "require.resolve('<pkg>')"` |
| 8a resource check | the §3 contract | refusal stops the train | Run at step 1 as well |
| 8b full verify | `<receipt launcher> <artifacts> <run-id> -- <make verify or equivalent>` (§4) | `<run-id>.exit` (§4) | Never judged from a pipe or wrapper |
| 9 re-confirm currency | `git fetch -q origin && git rev-parse origin/main` (compare with the train's base; if it moved, READ what landed before rebasing) · per boarder `git rev-parse --verify <lane-branch>^{commit}` (must equal the SHA merged at step 2) | printed SHAs, compared by the lander; any mismatch aborts | lander-duties §1 step 9 |
| 10 push | `<verify verdict check> && git push origin HEAD:main` | exit code | One mechanical statement; the owner's landing authorization (user-level, when the owner adopts one) decides whether the lander may push unattended |
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

### 4.1 The verdict rule (this section is its home)

A train's verdict is the `EXIT=` line of the exit receipt whose run id the
lander launched. `BASE=` and `HEAD=` say which tree that verdict is about and
must equal the tree the lander is about to push — and `BASE=` must be an
ancestor of `HEAD=` (`git merge-base --is-ancestor $BASE HEAD`): a green
receipt whose base is not an ancestor verified a train that main has already
moved away from, and the push is rejected (the install trial hit exactly this;
`../verification/lander-duties.md` §3 is the re-assembly). A missing receipt means the
run did not finish — not that it failed, not that it passed. Never judge from
a pipe status, a wrapper's `$?`, a backgrounded job's status, or a log tail.
`setsid cmd; echo $?` is the classic trap: on util-linux `setsid` forks when
the caller is a process-group leader and `$?` is the launcher's exit, recorded
before `cmd` finishes; and `setsid` is absent on some platforms (macOS ships
without it).

### 4.2 Minimum receipt launcher

Whatever launches the heavy step must (a) run the command in its own session
so a harness or terminal exit does not take it down, (b) WAIT for it, (c)
write the four lines to a temporary file and rename, (d) refuse an existing
run id. `run-lifecycle.md` §4 owns the general detached-launch pattern for
lane dispatch (session, writer lock, pin, stdin); the train's heavy step
needs only (a)–(d), and this reference satisfies them on any platform with
Python 3 and git. Save it as `<primary>/scripts/run_receipted.py`
(or wherever the project keeps helpers) and cite it in §2 row 8b:

```python
#!/usr/bin/env python3
"""run_receipted.py <artifacts> <run-id> -- <command...>"""
import subprocess, sys, pathlib

artifacts, run_id = pathlib.Path(sys.argv[1]), sys.argv[2]
cmd = sys.argv[sys.argv.index("--") + 1 :]
log, receipt = artifacts / f"{run_id}.log", artifacts / f"{run_id}.exit"
if log.exists() or receipt.exists():
    sys.exit(f"refused: {run_id} already has a receipt; use the next attempt")
rev = lambda r: subprocess.check_output(["git", "rev-parse", r], text=True).strip()
base, head = rev("origin/main"), rev("HEAD")
with log.open("w") as out:
    code = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT,
                          stdin=subprocess.DEVNULL, start_new_session=True).returncode
tmp = receipt.with_suffix(".exit.tmp")
tmp.write_text(f"EXIT={code}\nBASE={base}\nHEAD={head}\nLOG={log}\n")
tmp.replace(receipt)
sys.exit(code)
```

Run it from the train worktree. To keep the terminal free, background the
LAUNCHER (`python3 scripts/run_receipted.py … &` or under `nohup`); the child
still owns its session (`start_new_session=True` is `os.setsid()` in the
child) and the receipt still appears when the child ends. Checked on the
reference host before this file was written: a green command → `EXIT=0`; a
command exiting 3 → `EXIT=3` and launcher exit 3; the same run id again →
`refused: … already has a receipt`; the child's process group differs from
the launcher's. A `--continue` attempt (lander-duties §3) is simply the next
run id through the same launcher.

## 5. Local policy the project chooses

| Item | Fill in |
|---|---|
| Priority levels and which one qualifies for the single-lane blocker exception (lander-duties §2) | e.g. "P1 = blocks owner-approved work"; who may declare it |
| Port range for served instances | see §3.1 |
| Load threshold and wait window | see §3.4 |
| Agent CLI binary and subcommand token | see §3.3 |
| Derived progress page, if any (lander-duties §5, board-protocol.md) | page URL/path, or `none` |
| Landing authorization for unattended push | `none` until the owner chooses one (a user-level policy; the factory ships none active) |

## 6. Filled-in example (a TypeScript service with a docs site)

The repo is not the source factory; every value is a local choice.

| Step | Command |
|---|---|
| 1 | `git -C ~/src/app fetch -q origin && git -C ~/src/app worktree add -q -b train/t-42 ~/src/app-trains/t-42 origin/main` then `ln -sfn ~/src/app/node_modules ~/src/app-trains/t-42/node_modules` (lockfiles equal) |
| 2 | `git merge --no-ff 3f1c…e9 -m "train(t-42): board api-validation (3f1c…e9)"` ×4 |
| 3 | `npm run migrate:heads` (one head) · `node scripts/check-numbers.mjs` · `npm run docs:build -- --check` |
| 4 | `git add docs/choices/t-42.md && git commit -m "train(t-42): choices protocol"` |
| 5 | `npm run build` then `node scripts/stamp-dist.mjs` — also when only `docs/` changed |
| 6 | `npm run format:check` · `node scripts/lint-ratchet.mjs` · `npx tsc -b` · `node scripts/deps-ratchet.mjs` · `gitleaks detect --config .gitleaks.toml` · `node scripts/check-backlog.mjs` |
| 7 | `node -p "require.resolve('@app/core')"` → must print a path under `~/src/app-trains/t-42/` |
| 8a | contract: range `4300-4399`; binary `codex`, token `exec`; test runners `vitest`, `playwright`; threshold `cores/2`; window `6 × 20 s` |
| 8b | `python3 ~/src/app/scripts/run_receipted.py ~/trains t-42-1 -- npm run verify &` (the §4.2 launcher; the child waits, the receipt lands when it ends) |
| 9 | `git fetch -q origin && git rev-parse origin/main` → equals `BASE=` in the receipt, else read what landed; `git rev-parse --verify api-validation^{commit}` ×4 → each equals the SHA merged at step 2 |
| 10 | `grep -qx 'EXIT=0' ~/trains/t-42-1.exit && grep -qx "HEAD=$(git rev-parse HEAD)" ~/trains/t-42-1.exit && git push origin HEAD:main` |
| 11 | `gh project item-list 7 --owner acme --limit 200 --format json` → sweep; `git -C ~/src/app merge --ff-only origin/main`; `git worktree remove ~/src/app-trains/t-42` |

What `~/trains/t-42-1.exit` looks like when 8b ends green:

```
EXIT=0
BASE=9c2a1f0e7b6d4c3a8e5f2b1d0c9a8b7e6f5d4c3b
HEAD=4d7e2b9c1a0f8e6d5c4b3a2f1e0d9c8b7a6f5e4d
LOG=/Users/dev/trains/t-42-1.log
```

Resume after a conflict in step 2: resolve, `git commit`, re-commit the
protocol (step 4), then run from step 3 with run id `t-42-2` through the same
launcher; `t-42-1.exit` stays on disk with `EXIT=1` and `t-42-2.exit` is the
receipt step 10 reads.

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

The contract above is distilled from one source factory. Its
repository-owned assembler was first tried on a fourteen-lane train, where
it refused on a transient process match (the text-mention trap in §3.3 rule
3) and stopped at the first of four conflicts with no way to resume; the
rest of that train was assembled by hand. The continue contract
(lander-duties §3) and the process-identity criteria (§3.3) were fixed
after that, and the assembler then ran later multi-lane trains end to end —
among them the next train, resumed three times through `--continue`, and a
seven-boarder train that took four attempts (a conflict, a registry
cross-check, a red suite, then green). Its load policy (§3.4) was tuned on
those runs after the assembler's own cheap gates tripped the threshold. It
has NOT been exercised in a second repository; that trial is the acceptance
for any executable port (INSTALL step 7 in this package runs the plan by
hand).
