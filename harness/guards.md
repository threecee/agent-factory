# Harness guards — one dispatcher, switches that leave a trace, rules that fail open, adapters as short mappings

**Status: pilot, measurement-gated. Nothing here activates by itself.** This
file is the one home of every rule about guards; `harness/guards/` is the
mechanism and `harness/tests/test_guards.sh` the proof that it does what this
file says. Installing the package registers no hook; §9 says what registration
is and §11 what must exist before it happens.

Depends on `run-lifecycle.md` §6 (process identity: executable name plus an
exact argv token), `train-plan.md` §3 and §4 (the resource contract and the
receipt a verdict is read from), `../interpretation/choices-ledger-README.md`
§2 (the `O-<n>` entry a switch use becomes) and `bulk-read-contract.md` §3
rule 5 and §8 (the switch precedent: a hook whose block message does not name
its escape hatches is not compliant, and an adapter is a harness option, never
a default).

## 1. What a guard is and is not

A guard is a hook-mounted check that reads **one** signal available without
network at a harness event (pre-tool, post-tool, stop, session start) or a git
hook, and answers `allow`, `deny` or `context`. Four properties, none optional:

1. **One signal, no network.** The command text, a file in the tree, the
   process table, a receipt. A guard that needs the network (a board lookup)
   runs after the tool, advisory, never before it (§6, M-9).
2. **A denial names the exact alternative.** A guard never refuses what it
   cannot rewrite into the command the operator should have typed (§5).
3. **The switch exists before the guard is mounted** (§4). A rule with no
   switch is one of the few un-overridable conditions listed there, and says
   so in its message.
4. **A guard fails OPEN on its own crash**, with a loud context note (§3).
   Three neighbours that look alike and are not: a **gate** runs inside
   verify and fails CLOSED — a crashing gate is red; the **board
   verification** (M-9) is fail-open even on a logic error, because the board
   is not an air-gap-critical invariant; a **dispatch quota canary**
   (`run-lifecycle.md` §11 rule 1) is deliberately NOT fail-open, because a
   dispatch without quota is the failure it exists to prevent. Each of those
   is stated once, in its own home.

**No guard does any of this:** push, commit, reap a worktree, flip a registry
row, create a symlink, weaken a gate or a threshold, rewrite a baseline or a
receipt, bypass a hold, read production data, measure load, kill a process,
or call the network in a pre-tool event. A guard can refuse and name the
alternative; it never performs it.

## 2. Hook channel facts

What a hook can do depends on the event, and getting this wrong produces
reminders nobody receives (§10). The table is the documented behaviour of the
Claude Code hook model as read at analysis time (§14); other harnesses map
onto it or are post-hoc (§9).

| Event | Exit 2 blocks? | Context channel at exit 0 | Plain stdout reaches the model? |
|---|---|---|---|
| `PreToolUse` | yes — or JSON `permissionDecision: deny` with a reason | `hookSpecificOutput.additionalContext` | no |
| `PostToolUse`, `PostToolUseFailure`, `PostToolBatch` | exit 2 shows stderr to the model **after** the tool ran; nothing is undone | `additionalContext` | no |
| `Stop`, `SubagentStop` | yes — prevents the stop, the turn continues | `additionalContext` | no |
| `PreCompact` | yes — blocks the compaction | **none**: the event discards `systemMessage` and `continue` | no |
| `SessionStart` (sources `startup`, `resume`, `compact`), `SubagentStart` | no | `additionalContext` | **yes** (`SessionStart` only) |
| `UserPromptSubmit`, `UserPromptExpansion` | exit 2 blocks the prompt | `additionalContext` | **yes** |
| `PostModelSwitch` | no | `additionalContext` | **yes** |

Consequences the package builds on:

- Anything that must **survive a compaction** goes to a `SessionStart` hook
  with matcher `compact` (plain stdout reaches the model there), or to the
  next `UserPromptSubmit`. Nothing a `PreCompact` hook writes is preserved;
  `PreCompact` is a block, never a context channel.
- Timeouts: 600 s per command hook by default, **30 s** on the prompt and
  model-switch events — a `UserPromptSubmit` leg must finish well inside that.
- The hook process **inherits the environment of the session start**. A
  variable exported mid-session does not reach a hook; hence the command
  prefix and the state-file switch forms (§4). The harness env file
  (`CLAUDE_ENV_FILE`, written by a `SessionStart` hook) is documented for the
  shell tool's environment, and the dispatcher reads its `export` lines as a
  courtesy, not as the primary switch.
- **Coding-CLI hooks are post-hoc and unverified.** Never claim a blocking
  hook for a coding CLI; what such a lane can be forced to is what the
  wrapper checks at handback and what the git hooks refuse (§9,
  `run-lifecycle.md` §11 rule 3).
- **An instruction file is never a check.** A rule file or a
  directory-local instruction file delivers text the reader may reject —
  never claim one as a guard, a gate or a hook. This bullet is the home of
  that rule; the channel that delivers such a file is described in §9.

## 3. Dispatcher and rule contract

One dispatcher (`guards/guard_dispatch.py`) serves every event; adapters feed
it (§9). Per invocation:

- **Input.** The hook payload as JSON on stdin; the event from `argv[1]`
  (falling back to the payload's `hook_event_name`). An empty or garbage
  payload is an allow with no output.
- **Rules.** One module per mechanism under `guards/rules/`, loaded sorted by
  file name, exposing `ID` (the switch name), `EVENTS` (a set of event names),
  `MATCHER` (a tool name, a set of tool names, or `None` for tool-less
  events), optional `HONORS_ALLOW = True` (the rule reads its own switch and
  decides — a switch that is a precondition, or none at all), `check(payload,
  context) -> Verdict` and `falsification_cases(workdir)`. A module that
  fails to import or lacks `ID`/`EVENTS`/`check` is skipped and reported as a
  context note under `loader` — never a crash, never a denial.
- **Parameters.** A rule reads the §8 parameters from the hook process
  environment overlaid with the `FACTORY_GUARD_*` exports of the harness env
  file (a binding written mid-session is the later value); §8 says how a
  binding gets there.
- **Verdict.** `allow`, `deny` or `context` with a message. Any `deny` →
  the refusal on stderr, exit 2. Otherwise the `context` notes go out on the
  event's channel: `hookSpecificOutput.additionalContext` JSON on stdout for
  the harness events of §2; plain text on stderr, exit 0, for the git
  pseudo-events `GitPreCommit`, `GitCommitMsg`, `GitPrePush` (git has no JSON
  channel; the driver that feeds them is the git-hook adapter,
  `../verification/protections.md` §1). An event outside both sets has no
  context channel and the notes stay in the log.
- **Crash.** A rule that raises is reported as a context note under its own
  id, in the label shape of §5: `GUARD <id>: rule crashed and let the call
  through (<error>). Fix it before it counts as standard.` The other rules
  still run and still refuse.
- **One state location.** The repository root is `CLAUDE_PROJECT_DIR`, else
  the checkout the current directory is in, else the tree the package lives
  in — never `FACTORY_GUARD_DIR`, which only locates the package. The state
  directory is `FACTORY_GUARD_STATE_DIR`, else `.factory-guard/` in the
  **primary** checkout of that root (the parent of `git rev-parse
  --git-common-dir`), so every linked worktree, a session started in a
  worktree, the reminders adapter and the git hooks share one allow file,
  one events log, one landing state and one verdict log. It **must be
  gitignored** (INSTALL step 5 item 8). **Tests MUST set the override**; a
  direct call without it writes into the primary's events log. Inside it:
  - **the verdict log** `factory-guard.log` (`FACTORY_GUARD_LOG` overrides;
    named per train during the pilot): one JSON line per invocation —
    timestamp, session, event, tool, cwd, the first 200 characters of the
    command, the switch sources, one verdict per rule
    (`allow`/`deny`/`context`/`switched`, or `{"*": "disabled"}`), and the
    messages;
  - **the events log** `factory-events.log`: one tab-separated line per
    **denial** and per **switch use** (timestamp, session, event, kind
    `deny`|`allow-switch`, rule id, message or the switch sources). The
    memory nudge reads it; the ledger cites it (§4);
  - the allow file `factory-guard-allow` (§4) and `landing-in-progress.json`
    (M-13).

## 4. Switches

Two switches, four sources, every use logged.

| Switch | Effect |
|---|---|
| `FACTORY_GUARD_DISABLED=1` | every rule off for the session; the log records `{"*": "disabled"}` |
| `FACTORY_GUARD_ALLOW=<id>[,<id>]` | the named rules off; a rule with `HONORS_ALLOW` still runs and decides itself |

A switch silences only this kit's guard. A coding CLI's auto-mode classifier
may independently decline the command or decline a bypass switch; no guard
switch promises execution. Switches are last resorts: every documented
switch presents the working fix path first and the switch second. Try the fix
before setting the switch, then record any use as the `O-<n>` entry below.
Provenance: source factory Varde w137, 2026-09-08.

Sources **add**: the allow sets of all four are unioned, `DISABLED=1` in
either of the first two disables, and every source that contributed is named
in the log record's `switches` field (`env:`, `env-file:`, `prefix:`,
`file:`) — a switch the operator set never stops working because another
source set a different one:

1. the hook process environment (set before the session started);
2. `export` lines in the harness env file named by `CLAUDE_ENV_FILE` (a
   value written mid-session);
3. a `FACTORY_GUARD_ALLOW=<id>` **prefix on the command text itself**, so the
   switch stands in the transcript exactly where it was used — the form to
   prefer;
4. for events with no command (`Stop`, `SessionStart`, the git hooks), the
   state directory's allow file `factory-guard-allow`, one id per line.

Every switch use writes one `allow-switch` line to the events log **and** one
orchestrator entry `O-<n>` in the train's choices ledger with the rule id and
the reason (`../interpretation/choices-ledger-README.md` §1); a switch without
a ledger entry is a finding at landing. The clause is the bulk-read
contract's: a switch is for when the apparatus is down or the guard is wrong,
never a permanently disabled gate.

**Legs.** A rule may carry legs with their own switch ids under another
module id (`commit-refs` and `commit-subject` under `commit-msg`; `protocol`
under `landing`). One mechanism logs every switch use, in the dispatcher: a
rule it silenced, a leg that answered a `switched off` verdict under its own
id, or a context note under a switched id (a leg that delivered its finding
as context instead of a refusal). A rule never writes the events log itself.
The module's own id switches every leg of it.

To aggregate this trace by session or time window, use the anti-pattern
report in §15; it reads this events log and does not create a second log.

**Conditions with no switch.** A few refusals name a fact no switch can
change and are refused with the switch set, saying so: a server listening in
the project's port range, a test runner descending from a live lane
(`train-plan.md` §3.1 hard stops, M-5), and the gate legs of §6 that are not
hooks at all (M-7, M-8, M-17 — the fix *is* the correction).

## 5. Hard and soft forms

A **hard form** is refused (exit 2) because an exact, always-available
alternative exists: a verdict through a pipe, `--no-verify`, text-match
process selection, a raw lane dispatch, a push without a receipt. A **soft
form** is a context note or a `WARN` at exit 0: a reminder, a lint on its
first train, a check whose apparatus is offline.

The refusal shape, every hard form, no exceptions — the label is the word
`GUARD` and the rule's switch id, so a grep for the id over the events log
or the ledger finds every refusal and note of that rule:

```
GUARD <id>: <cause>. <evidence>. Fix: <exact command>. Switch: FACTORY_GUARD_ALLOW=<id> (logged).
```

Rules of form:

- A soft form becomes hard only by a **reviewed diff** to the operations doc
  after one train with the hook on, never by default.
- A rule that produces one false positive without a named alternative drops
  to `WARN` until fixed (§11).
- A `Stop`-style rule that refuses because of its own bug would hold the
  session in a loop. Such a rule **counts its refusals** in its state file
  and gives up loudly after three; the duties stay listed.

## 6. Mechanism table

Every mechanism of the source factory's analysis, with its trigger, the one
signal it reads, its form, and its home. `shipped` rows are code in this
package; `documented` rows are one sentence in their existing home plus this
row. No row restates its home. **Landing** in this table means the default
form — a PR merge with required checks — or the documented override, a
direct push carrying the `local-verify` status
(`../verification/landing-modes.md`); no row assumes one mode.

| Mechanism | Trigger | Signal read | Form | Home | Status |
|---|---|---|---|---|---|
| M-1 landing | a landing (pre-tool on the PR merge or the direct push; the git pre-push hook in the override mode) | the verify receipt for exactly this HEAD (`EXIT=`, `HEAD=`, `BASE=`), boarder heads on origin, the choices ledger, a `landing-in-progress.json` written after the landing is registered | hard | `../verification/protections.md` §1.1 + the `landing` rule (§7) | shipped |
| M-2 verdict | pre-tool shell | a gate invocation whose output enters any pipe, or a gate/receipt verdict followed by a push in the same call | hard | §7 | shipped |
| M-3 identity | pre-tool shell; lint leg over the tree | `pgrep -f`-style text-match selection; the grep form outside lines marked `forbidden form` | hard; lint red | §7 | shipped |
| M-4 ritual | post-tool after `git worktree add`; pre-tool before a dispatch into the tree | symlinks, lockfile equality, `info/exclude`, HEAD vs the remote default branch | hard (dispatch), context (post-tool) | `worktree-ritual.md` | documented |
| M-5 idle | pre-tool before verify, assembly, an evaluation driver | the process table and listeners by identity; never load | hard conditions have no switch; soft conditions yield to `idle` | `train-plan.md` §3 | documented |
| M-6 built-bundle | pre-tool before a serve/standup | the built bundle's entry set and stamp against the tree it will serve | hard | this row — only with a bundle to serve | documented |
| M-7 ledger lint | landing (M-1) and a cheap gate on a train branch | the choices ledger's form: one section per boarder, verdict + confidence per entry, no `unsound` without a fix note, no hedge | hard on the second train, `WARN` on the first | `../verification/protections.md` §5 (`check_choices_protocol`) | shipped |
| M-8 drift leg | a gate leg | a `claimed` registry row whose file is already on the remote default branch | gate, no switch | `../verification/protections.md` §7 | shipped |
| M-9 board | post-tool after a configured launcher/dispatcher invocation with its dispatch verb, not any `#<issue>` token; and after a registered push | the targeted repository's board-item status via the board CLI (network — hence post-tool, never in verify) | context; **fail-open by design** | §7 for selection; `../planning/board-protocol.md` item 5 for transaction/readback | documented |
| M-10 git hooks | `pre-commit`, `commit-msg`, `pre-push` | the identity git will write, the staged blobs, the trailer, the landing check when the override mode pushes the default branch directly | hard; git's `--no-verify` cannot be removed on the git side | `../verification/protections.md` §1 | shipped |
| M-11 ruleset / status | a change to the default branch on the hosting side | the ruleset accepts both paths — a PR merge after the required checks, or a direct push whose SHA carries the `local-verify` status posted from the receipt — and refuses everything else | hosting refuses | `../verification/protections.md` §2 | shipped |
| M-12 CI signal | `SessionStart` | the last CI conclusion for the default branch, when the CLI is authenticated; offline silent | context | `../verification/protections.md` §4 | shipped |
| M-13 close-out | `Stop` while `landing-in-progress.json` exists; `SessionStart` `compact`/`resume` as context | the open lander duties (ff, registry flip, reap, listeners, disk) | hard on `Stop` with the three-refusal rule; context after compaction | `../verification/protections.md` §6 | shipped |
| M-14 memory nudge | `Stop` and `SessionStart` `compact` | the events log and the operations doc's mtime (the thresholds are the home's) | soft — a question, never a block | `../interpretation/memory-conventions.md` | documented |
| M-15 dispatch preconditions, result lint, rows `raw-dispatch`, `justification`, `subagent-result` | the wrapper before launch; the wrapper at handback; pre-tool on a raw lane-shaped CLI call; pre-tool on a harness-subagent dispatch; `SubagentStop` | the brief's pin, the model policy, the quota-canary receipt, the round file, the dispatch gap (the conditions are the home's); the report's form; a lane-shaped invocation outside the wrapper; a `justification:` line (logged, not judged); a result file passing the machine check | hard (wrapper refusal, `raw-dispatch`, `justification`); `subagent-result` hard with the three-refusal rule | `run-lifecycle.md` §11 + `report-schema.md` "Machine check at handback" | documented |
| M-16 destructive and forbidden forms | pre-tool shell / edit | see the rows below | hard, one switch per row | the row table below is the home of every row; `no-verify` is also §7, `commit-identity` is `../verification/protections.md` §1.3 | `no-verify` and `commit-identity` shipped; the others documented |
| M-17 gate legs | cheap gates and lane pregate | duplicate registry ids, registry pin tests, the diff-triggered legs table (the brief's `DIFF_TRIGGERED_LEGS` placeholder, byte-equal to the operations doc's; a row runs when its glob matches the lane's working tree against the pin, or the train's committed range), "never weaken" (a baseline that rises without an `--update` commit, a gate changed without a test change, net assertion loss), brief↔operations consistency (the pregate block AND the legs table), skills lock, env scrub, seed-in-migration | gates, no switch; the "never weaken" leg `WARN` on its first train | `../verification/verify-portfolio.md` "Legs that bring lane-green closer to train-green" + `../verification/protections.md` §7 | M-17a (duplicate ids) and M-17d (never weaken) shipped; the rest documented |
| M-18 watchdog | a recurring task, not a hook | every `<lane>.sentinel.json` at `--max-age-min`, the exit sentinel, log and result mtimes, the branch head on origin; one line only on change | context; nudges, never kills | `run-lifecycle.md` §11 rule 6 (consumer of `../verification/gates/lane_sentinel.py`) | documented |
| M-19 hygiene | none — a rule about the hook table itself | every registered entry exists and its channel reaches the model | — | §10 | shipped as §10 + the settings example |
| M-20 disk floor | pre-tool before a big spender (dispatch, assembly, serve); the staging ceiling only before the configured coding-CLI command class that grows it | `df -k <volume>` against the floor, `du -sk <staging-root>` under a time budget | hard; a `du` that does not finish is a note | `train-plan.md` §3.1 row + the reminders' session-start line | documented |
| M-21 kind | the assembly cross-check (`../verification/lander-duties.md` §1 step 3) and the landing (M-1) | the repo's kind classifier (`FACTORY_GUARD_KIND_CMD`, §8) over `BASE..HEAD` against the ledger's `kind:` line — a classification of what the diff contains, never a policy | text today — the lander's reading at step 3, no code; `context`, never hard, when this row ships — the legs a kind selects are the hard ones (M-1's optional legs, M-17), and a kind that fell without an `O-<n>` entry is then a finding at landing (the rose/fell rule is `../planning/execution-contract.md` §9.2) | `../planning/execution-contract.md` §9 | documented |

**M-16 rows.** Each row has one switch (`FACTORY_GUARD_ALLOW=<row>`) so a false
positive never turns off the whole table.

| Row | Refuses | Alternative named |
|---|---|---|
| `no-verify` | `git commit\|push\|merge\|rebase\|am --no-verify`, `git commit -n`, and any of those under `git -c core.hooksPath=…` — always | the same command without the flag or the override (§7, shipped) |
| `baseline` | a ratchet `--update` unless the cwd is the primary, the tree is clean and the row's own switch is set (`HONORS_ALLOW`) | fix the findings, or rebaseline deliberately in the primary on a clean HEAD with the switch as a prefix |
| `stash-live` | `git stash\|checkout\|restore\|reset\|clean` while a writer whose directory flag resolves to this tree is alive (by identity) | wait for the sentinel to say done/parked, or tear the lane down first |
| `restore-dirty` | `git restore <path>` / `git checkout -- <path>` over uncommitted changes | commit first, or `git stash push -m <lane> -- <path>` |
| `worktree-remove` | `git worktree remove` / `git branch -D` while the branch holds unpushed commits, a dirty tree, ritual symlinks, large ignored files or a parked result — a branch merged into the remote default branch passes first | push, bank, unlink; then remove |
| `signal-probe` | `kill -USR1` / `-30` at a live process | the artefact's mtime and a stack dump tool |
| `shared-sentinel` | a redirect or `tee` to a shared default log/exit name without a lane prefix | `<lane>-<name>` |
| `second-writer` | a second writing lane CLI in a tree that already has one | wait, or run the second read-only |
| `edit-scope` | an edit to a script a running process holds open; an edit to historical documents from a subagent session | write the finding in the result file; only the orchestrator touches history |
| `commit-identity` | shipped as the pre-commit hook leg — the identity git will actually write, read with `git var` (environment overrides included), not one of the declared `FACTORY_GUARD_GIT_EMAIL` identities (`../verification/protections.md` §1.3) | `git config user.email <identity>`, or unsetting the environment override the refusal names |

A repository may list known no-op build forms as further rows (a type-check
flag that neither checks nor emits; the source factory had one) with the
honest form as the alternative.

## 7. Shipped rules

Eight rules ship as code, each with its falsification table (§11). Every gate
name, CLI name and token in their messages is a parameter (§8). The three
shipped rules below are this chapter's; its documented board selector follows
them. The five rules of the protections chapter — `landing`
(M-1, both landing modes, plus the hard-form rows `gh pr merge
--squash|--rebase|--auto|--admin` and `gh pr create` from a lane branch),
`pre-push` (M-10, the same id and switch as `landing`), `commit-msg`
(legs `commit-refs`, `commit-subject`), `commit-identity` (the M-16 row) and
`closeout` (M-13) — are described in `../verification/protections.md` §1,
§5 and §6 with their falsification tables in its §10.

### `verdict` (M-2)

- **Signal.** A gate invocation — `make <target>` matching a make pattern, a
  runner name, or `python -m scripts.<module>` / `python scripts/<module>.py`
  matching a module pattern of `FACTORY_GUARD_GATES` — whose output enters
  ANY pipe, including `--help | head` and regardless of `pipefail`, or followed
  in the same tool call by a `git push` statement (the subcommand, never the
  word `push` in a commit message);
  and a `cat`, `grep`, `source` or `.` read of `<x>.exit` followed by `git push`
  (verdict and push in one call). A subshell, a brace group or a
  `bash|sh|zsh -c` string around the gate is seen through (§13 names what
  is not). Only invocations are gated, never mentions: `grep` on a log,
  `ls | tail`, `git log | head` pass.
- **Parameter.** `FACTORY_GUARD_GATES` (§8).
- **Refusal.** `GUARD verdict: a verdict cannot be read through «| tail».
  Run the gate with a redirect to <lane>-<gate>.log and echo EXIT=$? in ONE
  call; read the log in the NEXT call; push in a later call
  (harness/train-plan.md §4.1). Fix, exactly: <rewritten command>. Switch:
  FACTORY_GUARD_ALLOW=verdict (logged).` The push form
  adds `— then, in the NEXT call when EXIT=0: <push>`. The command is never
  rewritten silently; the exact form stands in the message so the operator
  learns it.
- **Falsification** (19 denied, 11 allowed):

| Denied (red) | Allowed (green) |
|---|---|
| `make check-backlog 2>&1 \| tail -6; echo EXIT=$?` | `grep -n FAILED verify-t-42.log \| tail -5` |
| `pytest tests/test_backlog.py -q \| tail -1` | `ls -t artifacts \| tail -3` |
| `python3 -m scripts.check_backlog \| head -20` | `make check-backlog > lane-backlog.log 2>&1; echo EXIT=$?` |
| `make check-backlog --help \| head -20` | `cat t-42-1.exit` |
| `make verify 2>&1 \| grep -E 'passed\|failed'` | `rm stale.exit; git push origin lane/x` |
| `make verify \| grep passed; set -o pipefail` | `pytest tests/test_backlog.py -q -p no:cacheprovider` |
| `set -o pipefail; make check-backlog 2>&1 \| tee t-42-backlog.log` | `python3 -m scripts.check_backlog` |
| `set -eo pipefail; make check-backlog \| grep passed` | `make check-backlog && make check-numbers` |
| `python3 -m scripts.assemble_train t-42 --run-id t-42-1 \| tail` | `git push origin lane/x` |
| `make check-backlog; git push origin HEAD:main` | `make check-backlog; git commit -m push` |
| `cat t-42-1.exit; git push origin HEAD:main` | `git log --oneline \| head -3` |
| `grep '^EXIT=0$' t-42-1.exit; git push origin lane/x` | |
| `source t-42-1.exit; git push origin lane/x` | |
| `. t-42-1.exit; git push origin lane/x` | |
| `pytest tests -q 2>&1 \| tee lane-full.log` | |
| `make verify-fast \| tail -2` | |
| `make check-backlog && make check-numbers && git push origin HEAD:main` | |
| `bash -c "make check-backlog \| tail -3"` | `make check-backlog; git commit -m push` |
| `(make check-backlog 2>&1) \| tail -5` | |

Provenance: source factory Varde w137, 2026-09-08.

### `identity` (M-3b, plus the lint leg M-3a)

- **Signal.** The forbidden forms `pgrep -f`/`--full`, `pkill -f`, and `ps
  aux|-ef|ax|-ax … | grep|egrep|rg`, at statement level, `cd` prefixes
  honoured, a shell `-c` string seen through. Never kills.
- **Parameters.** `FACTORY_GUARD_CLI`, `FACTORY_GUARD_CLI_TOKEN` fill the
  identity form in the message (placeholders `<cli>`/`<token>` when unset).
- **Refusal** (it quotes the forbidden form). `GUARD identity: «pgrep -f»
  matches the inspecting shell (harness/run-lifecycle.md §6). Fix:
  harness/launch_lane.sh running <cli> <token>. Switch:
  FACTORY_GUARD_ALLOW=identity (logged).` The named alternative is the
  kit's implemented identity form — the launcher's `running` subcommand
  reads the untruncated `comm` of one pid at a time and matches the token
  exactly (`run-lifecycle.md` §6, `train-plan.md` §3.3 rule 2); a
  multi-column `comm` is truncated on macOS and a `/token/` is a substring
  match, so the `ps … | awk` form is green but never the recommendation.
  The `pkill` form says `kills by text match and hits other lanes' processes`
  and adds `tear down by port: lsof -ti :<port>` before the identity form.
- **Lint leg.** `lint_findings(root, roots=('harness',), marker='forbidden
  form')` returns `path:line: text` for the same three patterns outside lines
  that carry the marker (on the line, or on the previous non-blank line). The
  installer's own lint test and the shell test use it; the package's `harness/`
  tree is clean under it, so every quoted forbidden form here carries the
  marker.
- **Falsification** (6 forbidden forms denied, 6 allowed): `pkill -f serve.py` ·
  `pgrep -fl "<cli> <token>"` · `pgrep --full '<cli> <token>' | wc -l` (forbidden forms) ·
  `ps aux | grep '[s]erve.py'` · `cd /tmp && pgrep -af serve` · `sh -c 'pgrep -f serve'`
  (forbidden forms, all red) versus the identity form itself · the `ps -axo
  pid=,comm=,args= | awk …` mention · `lsof -ti :<port>` · `pgrep -x <cli>` ·
  `grep -rn pgrep docs` · `kill 4711` (green).

### `no-verify` (M-16 row)

- **Signal.** `git commit|push|merge|rebase|am --no-verify`, `git commit
  -n` (including grouped forms such as `-an` and `-qn`), and any of those
  under a global `-c core.hooksPath=…` (the second way
  to skip the hooks); `git -C <dir>` honoured, a shell `-c` string seen
  through — always, no precondition. Git's own `--no-verify` cannot be
  removed on the git side, so this harness-side row is what gives the git
  hooks of `../verification/protections.md` their meaning inside a hooked
  session.
- **Refusal.** `GUARD no-verify: «git <sub> --no-verify» skips the git hooks
  (planning/lane-brief-template.md §2; verification/protections.md). Fix: run
  «git <sub>» without the flag — a red hook is fixed, never bypassed. Switch:
  FACTORY_GUARD_ALLOW=no-verify (logged).` The override form quotes `«git -c
  core.hooksPath=<x> <sub>»` and says `without the override`.
- **Falsification** (6 denied, 5 allowed): `git commit --no-verify -m 'x'` ·
  `git -C /tmp/wt commit -n -m 'x'` · `git commit -an -m 'x'` ·
  `git push --no-verify origin lane/x` ·
  `git -c core.hooksPath=/dev/null commit -m 'x'` · `bash -c "git commit
  --no-verify -m x"` (red) versus `git commit -m 'x'` · `git -c
  user.email=<x> commit -m 'x'` · `git merge -qn lane/x` · `git push -qn
  origin lane/x` · `grep -rn -- --no-verify docs` (green).

### `board` (M-9; documented)

- **Selector.** The board rule runs only after the configured launcher or
  dispatcher invocation with its dispatch verb. A bare `#<issue>` token is
  never a dispatch signal.
- **Repository scope.** Resolve the item in the repository targeted by that
  dispatch command. Issue references in another repository are out of scope;
  a source-factory dispatch that mentions a kit issue does not select the kit
  board.
- **Measured false-positive classes.** Editing a brief, commenting on an
  issue, and cross-repository dispatch all triggered the old token selector;
  the command selector excludes all three. Board status, readback and
  fail-open semantics remain in `../planning/board-protocol.md` item 5.
  Provenance: source factory Varde w137, 2026-09-08.

## 8. Parameters

The package names roles; the operator binds each to a value in the
repository's operations doc. Nothing here is a universal constant.

**How a binding reaches the rules.** A rule reads the hook process
environment, which is locked at session start (§2); a value that only
stands in the operations doc binds nothing. The mechanism is one: the
`FACTORY_GUARD_*` variables are present in the environment the harness
starts its hooks with. Per adapter: Claude Code — the `env` block of the
settings file (the example ships one; the hook inherits it), or an `export`
written to `CLAUDE_ENV_FILE` by a `SessionStart` hook (read as the later
value, §3); a coding CLI — its own config's environment or the shell profile
the wrapper runs under; the git hooks — the driver's environment
(`../verification/protections.md`). The session-start reminder prints a
`GUARD BINDINGS:` line with every value or `unbound`, so an unbound
parameter is visible in the transcript instead of silently narrowing a
rule (`verdict` gates only its default table, `identity` prints
placeholders, the live-lane legs list nothing).

| Role | Placeholder | Suggested default | Owner |
|---|---|---|---|
| Package location | `FACTORY_GUARD_DIR` | beside the entry script (`<adapters>/../guards`) | the entry script; set only when the two directories are not copied together — the package directory must keep the name `guards`, and the variable never moves the state directory or the log (§3) |
| State directory | `FACTORY_GUARD_STATE_DIR` | `.factory-guard/` in the primary checkout (§3), gitignored | tests set it always; operators only when the primary is not writable |
| Verdict log | `FACTORY_GUARD_LOG` | `factory-guard.log` inside the state directory; named per train during the pilot | operator; banked as produced during the pilot |
| Global switch | `FACTORY_GUARD_DISABLED` | unset; `1` only while the apparatus is down | operator (`../user-level/README.md`) |
| Per-rule switch | `FACTORY_GUARD_ALLOW` | unset; `<id>[,<id>]`, preferably as a command prefix | operator; every use ledgered |
| Offline mode | `FACTORY_GUARD_OFFLINE` | unset; `1` makes every network-reading rule (M-9) answer with context instead of calling out — the falsification runner and the tests set it | operator; the apparatus always |
| Gate names for `verdict` | `FACTORY_GUARD_GATES` | `verify,verify-*,check-*,pytest,scripts.check_*,scripts.assemble_*` — make target patterns and runner names (no dot), module patterns (with a dot) | repo operations doc |
| Board dispatch form | `FACTORY_GUARD_BOARD_DISPATCH` | unset — M-9 remains documented; `<launcher-or-dispatcher> <dispatch-verb>` identifies a dispatch before the rule reads any issue token | repo operations doc |
| Lane CLI identity | `FACTORY_GUARD_CLI` / `FACTORY_GUARD_CLI_TOKEN` / `FACTORY_GUARD_CLI_DIR_FLAG` | unset — the identity refusal prints placeholders and the live-lane legs list nothing; e.g. `codex` / `exec` / `--cd` | repo operations doc (`train-plan.md` §3.3 names the same two values) |
| Port range | `FACTORY_GUARD_PORT_RANGE` | unset; e.g. `4300-4399` (`train-plan.md` §3.1) | repo operations doc |
| Data volume | `FACTORY_GUARD_DATA_VOLUME` | unset; the volume the repo lives on | repo operations doc |
| Disk floor | `FACTORY_GUARD_DISK_FLOOR_GB` | unset; e.g. `20` | repo operations doc |
| Entry script for `falsify` | `FACTORY_GUARD_ENTRY` | `<package>/../adapters/factory_guard.py` | the falsification runner |
| Default branch | `FACTORY_GUARD_DEFAULT_BRANCH` | `main` — read by the `landing` rule, the pre-push hook, the close-out gate, the drift leg and the CI signal (`../verification/protections.md`) | repo operations doc |
| Commit identity | `FACTORY_GUARD_GIT_EMAIL` | unset — the pre-commit leg checks nothing and says so on every commit; comma-separated e-mails (`../verification/protections.md` §1.3) | repo operations doc |
| Source prefix for the trailer rule | `FACTORY_GUARD_SOURCE_PREFIX` | `src/`; comma-separated (`../verification/protections.md` §1.2) | repo operations doc |
| Trailer form | `FACTORY_GUARD_TRAILER_RE` | `^Refs: (ADR-\d{4})` — group 1 is the record id, its digits locate the file (§1.2) | repo operations doc |
| Decision records directory | `FACTORY_GUARD_DECISIONS_DIR` | `docs/decisions` (§1.2) | repo operations doc |
| Declared landing mode | `FACTORY_GUARD_LANDING_MODE_DEFAULT` | `pr`; `direct-push` only when `train-plan.md` §5 declares it — the lint's `override reason:` rule reads it (`../verification/protections.md` §5) | repo operations doc (train-plan §5) |
| Gates directory for the rules that read one | `FACTORY_GUARD_GATES_DIR` | unset — `<repo>/scripts`, then `<repo>/verification/gates`, then beside the package (`guards/rules/_gates.py`) | operator, when the gates live elsewhere |
| Ledger directory | `FACTORY_GUARD_LEDGER_DIR` | `docs/choices` | repo operations doc |
| Receipt directory for a landing | `FACTORY_GUARD_ARTIFACTS` | unset — the ledger's `receipts:` line; a command prefix wins (`../verification/protections.md` §1.1) | the lander, per train |
| Registry check | `FACTORY_GUARD_REGISTRY_CMD` / `FACTORY_GUARD_REGISTRY_FILE` | unset — the leg is skipped / `docs/decisions/NUMBERS.md` | repo operations doc |
| UI pass glob | `FACTORY_GUARD_UI_GLOB` | unset — the leg is skipped; comma-separated globs; bound, a train touching them needs `ui-pass:` in the ledger | repo operations doc |
| Docs-only classifier | `FACTORY_GUARD_DOCS_ONLY_CMD` | unset — a receipt carrying `DOCS_ONLY=1` is refused; `<cmd> <BASE> <HEAD>` (§1.1) | repo operations doc |
| Change-kind classifier | `FACTORY_GUARD_KIND_CMD` | unset — the M-21 leg is skipped and the brief's `Kind:` line reads `none — classifier unbound`; `<cmd> <path>...` prints the applicable kinds, one per line (`../planning/execution-contract.md` §9.3); built from the docs-only classifier, the source prefix, the decisions directory, the registry file, the never-weaken check's baseline and gate globs and the guarded-boundary list already bound here — that the kind and the landing legs never disagree about a path is the design constraint INSTALL step 7.7 falsifies, not a property this row checks; printed on `PROTECTIONS BINDINGS:` once the leg ships (documented row) | repo operations doc |
| Hook interpreter | `FACTORY_GUARD_PYTHON` | `<toplevel>/.venv/bin/python`, else `python3` (the shims; `../verification/protections.md` §1) | repo operations doc |
| Protections location | `FACTORY_PROTECTIONS_DIR` | `<adapters>/../../verification/protections` — locates `git_hooks.py` and `ci_signal.sh` for the shims and the reminders script; a location like `FACTORY_GUARD_DIR`, never a rule parameter | the operator, when the chapter is kept elsewhere |

The `falsify` runner scrubs every row above that a rule or a gate reads
(`guard_dispatch.PARAMETER_VARS`), so the receipt proves the shipped tables
whatever the operator has bound (§11); the session-start reminder prints the
protections rows on a `PROTECTIONS BINDINGS:` line beside `GUARD BINDINGS:`.

## 9. Adapters

An adapter is the short, harness-specific mapping that feeds events to the
one dispatcher. Registration of an adapter is a separate, deliberate operator
step (§11); the package registers nothing.

| Harness | Adapter | What it is |
|---|---|---|
| Claude Code | `adapters/claude-code-settings.json.example` + `adapters/factory_guard.py` + `adapters/factory_reminders.sh` | the `env` block (the §8 bindings) and the hooks block: `PreToolUse` matchers `Bash`, `Agent\|Task`, `Edit\|Write\|MultiEdit\|NotebookEdit`; `PostToolUse` `Bash`; `Stop`; `SubagentStop`; `SessionStart` matcher `compact\|resume` — all to the entry script with the event as `argv[1]`; the two text legs (`SessionStart` incl. `compact`, `UserPromptSubmit`) to the reminders script (§10). Every event the dispatcher can serve is registered once: a leg with no shipped rule logs an empty verdict set and costs one interpreter start, and a new rule needs a rule module, never a settings edit. `$CLAUDE_PROJECT_DIR/<path>` is the only thing to edit in the hooks block |
| Coding CLI with post-hoc hooks | `adapters/AGENTS.md.example` | one paragraph: the session is not hooked; the git hooks, the wrapper's result lint at handback (`report-schema.md` "Machine check at handback") and the standing brief's hard rules bind the lane; write the report to `$LANE_RESULT_PATH` |
| git | the tracked hook shims + driver | `pre-commit`, `commit-msg`, `pre-push` → the pseudo-events of §3 (`../verification/protections.md` §1) |
| CI | a workflow | the pull-request advisory lanes and the CI signal (`../verification/protections.md` §4, `../verification/ci/README.md`). The contract between the two chapters: the protections chapter ships `verification/protections/ci_signal.sh` (or points `FACTORY_PROTECTIONS_DIR` at the directory holding it); the reminders script calls it at session start when it is executable, for `FACTORY_GUARD_DEFAULT_BRANCH`, and prints nothing when it is absent |

The entry script only locates the package (`FACTORY_GUARD_DIR`, else beside
itself), puts the package's parent on `sys.path`, and calls `main(argv)`
under a `__main__` guard — importing it runs nothing. It works wherever the
two directories are copied together, and writes no bytecode into the tree.

**Domain guidance delivery (advisory, never a check).** The `reads first`
column of the diff-triggered legs table
(`../verification/verify-portfolio.md`, "Legs that bring lane-green closer
to train-green", leg (c)) names the repo document a lane reads before it
touches a surface; the brief's §2 already requires that reading. A harness
that loads instructions on demand may deliver the pointer at the moment of
contact — the mapping, per harness:

| Harness | Delivery form |
|---|---|
| Any harness that reads directory-local instruction files (a nested `CLAUDE.md` loaded when a file in that directory is read; a nested `AGENTS.md` read per directory by coding CLIs) | the harness-neutral form: one pointer-only file in the directory the row's `touches` globs cover, whose whole body is the `reads first` pointer |
| Claude Code, Cursor | the refinement: a path-scoped rule file (`paths:` frontmatter; a glob-scoped rule) whose globs are the row's `touches` globs verbatim — fired when the harness READS a matching file, which covers an edit only because the harness reads before it edits |
| Coding CLI without on-demand loading, git hooks, CI | none — the brief's `reads first` pointer is the delivery; a post-hoc hook cannot inject text before the read |

Rules of the channel: a rule file loaded unconditionally is not
path-scoped and is not this channel; no phase files (the package has no
phase machine — phases are separated by role and tree: lanes author, the
wrapper commits, only the lander verifies, in a train tree); the file is a
pointer, never a second statement of a rule (one home); the installer's
consistency test (`../verification/verify-portfolio.md`, leg (e)) checks
each such file against its legs-table row so the two cannot drift; after a
compaction the file fires again only when a matching file is read again
(§2 — the `compact` reminder leg is the only guaranteed post-compaction
channel); and none of it is a check — §2 is the home of that rule.

## 10. Hook hygiene (M-19)

Two facts per registered entry, checked when the table changes and once per
install: **the script exists**, and **its channel reaches the model** (§2).
An entry that fails either is a reminder nobody receives, and worse than no
entry: it looks like coverage.

| Was | Reroute to |
|---|---|
| a `PostToolUse` hook printing plain stdout | the dispatcher, as `additionalContext` |
| a `PreCompact` hook printing "keep this after compaction" | `SessionStart` with matcher `compact` (plain stdout reaches the model there) |
| a hook entry pointing at a script that does not exist | delete the entry, or write the script |

One owner per reminder: the post-dispatch checklist is a `PostToolUse` note
from the dispatcher; the lander list comes from the landing guard (M-1); the
worktree ritual from the ritual guard (M-4); the reminders script owns only
the two plain-stdout legs and says so in its header. A reminder with two
owners is stated twice and maintained by neither.

**Hook children.** A rule that spawns a child (`landing._run`, `_common.git`)
passes `child_environ()` — the caller's environment without git's hook
repository pins — so a check running inside `pre-push` cannot act on the
pushed repository through `GIT_DIR`. `../verification/protections.md` §1.1
states the rule and the incident that set it.

## 11. Falsification and mounting

Every rule ships its falsification list: planted violations with the needle
the refusal must contain (expected `RED`), and green forms expected silent
(`GREEN`). The runner replays them through the **real** entry script as a
subprocess with the case's environment merged over a scrubbed one
(`FACTORY_GUARD_ALLOW`, `FACTORY_GUARD_DISABLED`, `CLAUDE_ENV_FILE` and every
§8 parameter removed, so the receipt proves the **shipped** tables whatever
the operator has bound — the binding itself is proved on the first hooked
train; `FACTORY_GUARD_OFFLINE=1`; a per-run state directory and log under
`--out`), judges the exit code **and** the needle in the **right** stream
(`../verification/falsification.md` rule 2: the message, not the exit code;
a green form is silent when no `additionalContext` reached stdout and no
`GUARD` text reached stderr — an interpreter warning is not a refusal), and
writes the receipt:

```sh
python3 harness/guards/guard_dispatch.py falsify --lane <lane> --out <dir>
#   → <dir>/<lane>-guard-falsification.log, one line per case:
#     RED|GREEN ok|FAIL <rule>/<case>: <detail>
#   exit 0 when every case is ok, 1 on any FAIL
```

Mounting is then a trial, not a switch flip:

1. The receipt log is **banked** before the adapter is registered
   (`artifact-bank.md` §2).
2. The first live train runs with the hooks on from assembly start, and the
   ledger's `O-` section records every refusal and every switch use.
3. Measured on that train: refusals, true and false; assembly runs per train
   before and after; switch use. A false positive without a named alternative
   sends the rule to `WARN` until fixed (§5).
4. Adoption enters the loop of `../interpretation/continuous-improvement.md`:
   a machinery change with a measurement, a finding with the numbers, a board
   item for making the rule standard. No rule counts as standard before it
   has run one train with (a) the receipt for red on a planted violation, (b)
   silence on a green train, (c) zero switch uses without a reason in the
   ledger.

## 12. What stays human

Binding. The signal a hook can read is the **existence or form** of text,
never its truth. A hook that checks that `root_cause:` exists does not check
that the hypothesis is true; one that counts assertions does not tell a
rewrite from a deletion; a lint that finds "should work now" does not find the
same hedge in another sentence or another language. Therefore:

- **Review content** — whether a red→green proof is real, whether an
  invariant is right, whether a reviewer was independent, whether the
  close-out order was followed. A form lint (M-7, M-15) is useful because it
  forces text a reader can reject; it is not the proof.
- **Role and policy choices** — who is the lander, which effort level, which
  model, how CI is read. A hook may require that the choice is **logged**
  (the `justification:` line of M-15); it never judges whether it is right.
- **Events that need reading** — a purge in progress, whether three
  hypotheses were distinct, whether a failure was a quota wall, the right
  moment to bank, a parallel fixer. The signal is often printed (M-14); the
  decision is a reading.
- **Rules the operations doc exempts by design** — a session trailer's form
  ("do not invent a check"), a disable variable that is only for a dead
  worker chain, the absence of compliance ceremony on interior surfaces. A
  guard there would contradict the manual it serves.

Three patterns of false security, each seen in the source factory:

1. **The guard measures itself.** A text-match idle check that matched the
   inspecting shell; a load check that measured its own pregate burst; a
   freshness stamp computed from the wrong entry set. A guard that was never
   falsified with a planted violation is a claim, and an operator who stops
   believing it starts forcing past it.
2. **The guard can be bypassed silently.** `--no-verify` without a git hook,
   `--update` without a dirty-tree refusal, `--force` as a habit. A switch
   must leave a trace and be per rule, not global.
3. **The guard locks the operator out.** A hook mounted before its switch
   existed or before the alternative it named could work. The switch exists
   first; the refusal always names the exact alternative.

And the `Stop`-hook warning: a `Stop` hook that holds a session in its turn
because of its own bug is worse than no hook. It counts and gives up after
three (§5).

## 13. What the test proves — and what it does not

`bash harness/tests/test_guards.sh` (or `zsh …`) runs in about a minute on
a throwaway copy of `guards/` and `adapters/` — with `verification/gates`
beside them, because the landing and close-out rules read a gate
(`../verification/protections.md` §10) — under a path with a space, through
the real entry script, every case with its own state directory and log (§3):

| Case | Proves | Section |
|---|---|---|
| 1 | an empty payload, a garbage payload and an unknown event are exit 0 with no output | §3 |
| 2 | the `verdict` table: denied forms name the pipe stage, the rewritten form and the switch; the push form names the next call; a subshell, a brace group and a `bash -c` string are seen through; `git commit -m push` is not a push; green forms are silent; `FACTORY_GUARD_GATES` binds the gate names both ways, from the environment and from the env file | §7, §8 |
| 3 | the `identity` table: the three forbidden forms are refused naming the launcher's identity form and, for `pkill`, the port form; the form is filled from the CLI variables; a `sh -c` string is seen through; the green forms — the launcher form, the `ps … \| awk` mention, `lsof`, `pgrep -x`, `kill <pid>` — pass | §7, §8 |
| 4 | the `no-verify` table, `-C` honoured, `merge --no-verify` included, `-c core.hooksPath=` refused as the override, `bash -c` seen through, another `-c` config passes | §7 |
| 5 | all four switch sources are honoured and each is named in the log (`env:`, `prefix:`, `file:`, `env-file:`); the environment's and the env file's allow sets are unioned and both named; `DISABLED=1` logs `{"*": "disabled"}`; another rule's switch does not silence this one; the events log holds one line per denial and per switch use, naming the source | §4, §3 |
| 6 | a rule that raises fails OPEN: exit 0 and the loud `GUARD <id>:` note in `additionalContext`; a module without `ID`/`EVENTS`/`check` yields a loader note, never a crash; the other rules still refuse beside a crashing one | §3 |
| 7 | channels: a `PostToolUse` note is stdout JSON only; a `PreToolUse` denial is stderr only with exit 2; a `GitPrePush` pseudo-event's note is stderr text with exit 0 | §3, §2 |
| 8 | from a linked worktree the state directory resolves to the primary (its allow file is read, nothing is written under the worktree); `FACTORY_GUARD_STATE_DIR` overrides it; with the package kept outside the repository (`FACTORY_GUARD_DIR`) and `CLAUDE_PROJECT_DIR` set, the verdict log and the events log land in the primary's state directory, nothing beside the package, and the reminders script names the same directory | §3, §8 |
| 9 | `falsify` writes the receipt with exactly the shipped number of `ok` lines in the documented shape and exits 0, also under a `FACTORY_GUARD_GATES` binding in the environment (scrubbed); a planted wrong needle in the copy gives exactly one `FAIL` line naming the case and exit 1 | §11 |
| 10 | the lint helper reports a planted forbidden form as `path:line: text`, is silent on a marked line, and finds nothing in the package's own `harness/` tree | §7 |
| 11 | the reminders script prints the guards line, the `GUARD BINDINGS:` and `PROTECTIONS BINDINGS:` lines with `unbound` or the bound values, no `GIT HOOKS:` line while the protections driver is absent, the `DISABLED` warning and the open-landing line; `compact` prints the keep-list; `prompt` names a live lane by identity (a symlink named `fakecli`, the exact token, the directory flag) and never a shell whose text mentions the same words; a different bound CLI name lists nothing | §8, §9, §10 |
| 12 | the settings example parses, names only adapter scripts that exist, carries the required matchers and an `env` block, has no `PreCompact` leg and no bulk-read entry | §8, §9, §10 |

Self-falsification of the test (authoring run, on scratch copies of the
package through `TEST_GUARDS_ROOT`): dropping the events-log write turned
exactly 5g and 5h red; removing the rule try/except turned 6a–6c red (the
crash takes the whole hook down, so the loader note and the neighbouring
denial vanish with it); emptying `CONTEXT_EVENTS` turned 7a red and, because
the crash and loader notes travel on the same channel, 6a and 6b with it.
Nothing else moved.

What the test does **not** prove:

- **A real CLI's hook behaviour.** The payloads are the documented shapes,
  fed by the test. Whether a given harness version sends them, honours exit
  2 on every event of §2, surfaces `additionalContext` on `PostToolUse`, or
  passes its settings `env` block to the hook process (§8) is checked once
  per harness, by hand, against a live session.
- **The `compact` matcher firing.** That a `SessionStart` hook with source
  `compact` runs right after a compaction and that its plain stdout reaches
  the model was read from the source harness's documentation, not tried.
- **Forms the parser cannot see.** It reads the command text one statement
  at a time and sees through a subshell, a brace group and up to three
  levels of `bash|sh|zsh -c` strings. It does not see a gate, a flag or a
  forbidden form inside `eval`, a string built at run time, a script file,
  `xargs`/`find -exec`, or a command substitution inside another command's
  arguments — those pass silently, with no refusal and no log line. The git
  hooks (M-10) and the wrapper's handback check are what catch the
  outcome, not the text.
- **Process identity for a directory operand containing a space.** `ps`
  joins argv with spaces; the reminders script and `live_agents` read such an
  operand up to its first space. Lane directories without spaces are the
  contract; the test's fake lane is space-free for this reason.
- **The documented-not-shipped rows of §6.** They are contract rows with a
  home each; their falsification lists are written when their code is.

## 14. Provenance and what is still provisional

This chapter was distilled from a source factory's 2026 analysis of what
could be made deterministic and its two implementation waves; the dispatcher,
the shared primitives and the three rules keep that implementation's
semantics (fail-open on a crashing rule, four logged switch sources, denial
reserved for hard forms) with every gate name, CLI name, port, path and
identity replaced by the parameters of §8 (`../skills/ATTRIBUTION.md`). The
one-state-location rule of §3 comes from that factory's assembly finding
that a direct dispatcher call without the override wrote into the primary's
events log.

Provisional:

- The false-positive rate of `verdict` and `identity` is unknown until one
  train has run with the hooks on (§11). The source factory expected the
  first mounting to send at least one row to `WARN`.
- The git hooks and the hosting-side ruleset were untried in the source
  factory at analysis time; `../verification/protections.md` carries them
  with their own falsification (its §10), the live-host half of which is
  INSTALL step 7's duty in a throwaway repository.
- The channel table of §2 is the source harness's documented behaviour at
  analysis time; the one empirical confirmation there was that `PostToolUse`
  plain stdout never reached the model. Re-read the table against the
  harness version you run.

## 15. Anti-pattern report

`python3 harness/guard_report.py [--session <id> | --since <ISO>] [--log
<path>] [--json]` reads the six-column `factory-events.log` contract from §3.
It reports denials per rule with count, first timestamp, last timestamp, and
newest message; it also lists every `allow-switch` trace from §4. The default
log is `<FACTORY_GUARD_STATE_DIR>/factory-events.log`, falling back to
`.factory-guard/factory-events.log`. A supplied log path is read verbatim.

The named anti-pattern table is one ordered regex table named
`ANTI_PATTERNS` in `guard_report.py`; an operator extends that table rather
than adding report branches. Its stable names are `verdict-pipe`,
`gate-plus-push`, `self-matching-kill`, `stale-canary`,
`raw-cli-outside-launcher`, `no-justification`, `idle-violation`,
`stale-build`, `board-unverified`, and `unbounded-read`. The derived
`looping-denial` row means the exact same denial message occurred at least
three times within a ten-minute window. A climbing count usually means one
broken guard is looping, not that the operator made many independent errors.

Text output is a set of Markdown tables; `--json` emits the same denials,
switches, and named matches as objects for another local tool. Malformed TSV
rows are ignored with a warning, while an unreadable log is red. The report
only interprets the existing trace: it changes no switch, guard, or state.

Provenance and what is still provisional: the names capture recurring
failure forms from the source factory and the 2026 Uber efficiency lesson
recorded by issue 23. `test_guard_report.sh` exercises every name and removes
one regex to prove the fixture reds; thresholds other than the observed
three-in-ten-minute loop remain an operator choice.

## 16. A mounted guard retires the prose rule it replaces

**Rule.** Once a guard in §7 is mounted, operational documents remove the
prose prohibition it enforces and keep only a one-line pointer to that guard's
home. The executable rule, refusal, alternative, switch and falsification then
have one owner.

**Reason.** Parallel prose drifts from the executable condition, consumes the
brief and repository-primer context that every lane pays for, and makes a
reader reconcile two authorities. Retirement is recorded in the choices
ledger with the rule ID, mounted guard, retired prose path, verdict and proof
that the guard's falsification remains green.

Do not prune skills expecting material Codex input savings. The source
factory's A/B changed the listing from 50 skills to 35 and changed a trivial
Codex call by about 150 input tokens out of about 24,400; the skills listing
was not the cost driver. The brief and the repository primer were.
