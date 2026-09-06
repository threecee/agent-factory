# Protections — git hooks, the branch policy, the status poster, the CI signal, the ledger lint, the close-out check, the gate legs

This file is the ONE home of the protections that sit OUTSIDE the harness
hook: the tracked git hooks (M-10), the server-side branch policy (M-11), the
status poster, the session-start CI signal (M-12), the choices-ledger lint
(M-7), the close-out check (M-13) and the gate legs M-8, M-17a and M-17d.
The harness guard frame — the dispatcher, the switches, fail-open, the
channels — is `../harness/guards.md` and is not restated here; the landing
doctrine (which mode, which commands, what the hold looks like) is
`landing-modes.md`. Every mechanism below is described once, with its
adapters as one-line mappings (§8).

## 1. Git hooks (M-10)

Three tracked POSIX shims under `protections/githooks/` — `pre-commit`,
`commit-msg`, `pre-push` — exec `python3 <protections>/git_hooks.py <hook>
[args]` with git's cwd and stdin. The driver turns each hook into one
dispatcher pseudo-event (`GitPreCommit`; `GitCommitMsg` carrying the proposed
message; `GitPrePush` carrying the parsed `<local ref> <local sha> <remote
ref> <remote sha>` lines) and runs the SAME rule modules, switches and log as
the harness hook (`../harness/guards.md` §3). Switches come from the
environment and the state directory's allow file — a git hook has no command
prefix to read. A denial is exit 2 with the message on stderr (git aborts on
any non-zero exit); a WARN is stderr text with exit 0.

- `git_hooks.py install [--hooks-dir <dir>]` sets `core.hooksPath` once per
  repository — shared by every linked worktree — to the tracked shims
  (`<toplevel>/.githooks` when the repository keeps them there, else the
  directory beside the driver; relative inside the toplevel, absolute
  otherwise) and adds the executable bit. `status` exits 1 until installed
  and every shim is executable. The session-start reminder prints a `GIT
  HOOKS:` line while `core.hooksPath` is unset.
- The interpreter is `FACTORY_GUARD_PYTHON`, else `<repo>/.venv/bin/python`,
  else `python3`.
- The driver locates the guards package through `FACTORY_GUARD_DIR`, else
  `harness/guards` beside the package, else `<toplevel>/harness/guards`,
  else `<toplevel>/scripts/guards`; a package that is not found lets the
  commit or push through with one loud line (fail-open, as every guard).
- The hooks never run the verify portfolio and are never called by a guard.
- Git's `--no-verify` and `-c core.hooksPath=…` cannot be removed on the git
  side. Inside a hooked harness session the `no-verify` rule refuses both
  (`../harness/guards.md` §7); outside one, the branch policy of §2 makes a
  bypassed pre-push harmless — a push without the status is refused by the
  host.

### 1.1 pre-push — the landing check in the override mode

For every update whose remote ref is `refs/heads/<default>`
(`FACTORY_DEFAULT_BRANCH`, default `main`) the rule `pre_push` runs exactly
the landing guard's check (`landing.check` over a `git push <remote>
HEAD:<default>` payload — receipt for exactly HEAD, boarders, ledger, the
optional legs, the ledger lint), so the guard holds for a coding-CLI session,
a plain terminal and a foreign harness. A local SHA other than HEAD is
refused (a receipt binds exactly HEAD); a deletion of the default branch is
refused; any other destination — `lane/*`, `train/*` — is silent: the
integration-branch push is never gated. Same id (`landing`), same switch,
because it is the same guard.

### 1.2 commit-msg — the decision-record trailer

A commit whose staged diff touches `FACTORY_SOURCE_PREFIX` (default `src/`;
comma-separated) must carry the decision-record trailer
(`FACTORY_TRAILER_RE`, default `^Refs: (ADR-\d{4})`), and every record it
names must exist under `FACTORY_DECISIONS_DIR` (default `docs/decisions`) on
disk or in the same commit — a claimed number is a dangling reference until
its file exists. Merges (`MERGE_HEAD` present, or an amended merge commit)
and subjects starting `Revert "`, `Merge `, `fixup! ` or `squash! ` are
exempt: the boarded or reverted commits carry the trailer. An amend measures
the index against `HEAD~1`, so `git commit --amend -m` cannot launder the
trailer away (an amend of the root commit measures the whole index). The
subject form `<type>(<scope>): <imperative>` is a WARN (`commit-subject`)
until a reviewed diff to the operations doc flips it. Leg switches:
`commit-refs`, `commit-subject`; each use is logged.

**Pull-request merge commits.** A merge commit the host writes (`Merge pull
request #N …`) never passes a local hook. Any range scan over history — a
trailer scan, a subject scan — must exempt the `Merge ` subject as this rule
does, or the first verify after a pr-mode landing goes red.

### 1.3 pre-commit — the identity git will write

The author and committer e-mail git will ACTUALLY write — `git var
GIT_AUTHOR_IDENT` / `GIT_COMMITTER_IDENT`, which honour `GIT_AUTHOR_EMAIL`,
`GIT_COMMITTER_EMAIL`, `EMAIL` and `--author` before `user.email` — must be
in `FACTORY_GIT_EMAIL` (comma-separated). The identity is declared, never
guessed: unset, the leg checks nothing and says so once (`GUARD
commit-identity (warn): identity not declared`). A config-only check lets an
environment override through; the source factory rewrote thousands of
commits after one. Refusal: `GUARD commit-identity: the identity git will
write is «<x>» (<author|committer>, git var), not the declared «<emails>».
Fix: git config user.email <email> — or, when config is right: unset
GIT_AUTHOR_EMAIL GIT_COMMITTER_EMAIL EMAIL. Switch:
FACTORY_GUARD_ALLOW=commit-identity (logged).`

A pull-request merge commit carries the host's web-flow committer and never
passes this hook; an identity scan over history must exempt it.

**The optional staged-secret leg (described, not shipped).** Materialise the
STAGED blobs (`git show :<path>`, never the working tree) into a shadow tree
and scan them with the repository's secret scanner against its config and
baseline, restricted to what this commit would add; a new finding refuses
the commit with the redacted location (the fix is a generated literal, never
a baseline update); a missing or crashing scanner is a loud WARN that lets
the commit through — the verify gate over the committed history
(`gates/check_gitleaks.py`) stays fail-closed, the hook is its early
warning. An installer adds it as a rule module when the repository has a
scanner and a baseline.

## 2. The default-branch ruleset (M-11)

The payload `ci/ruleset-main.json.example` states five facts: the target is
the default branch; deletion is refused; non-fast-forward is refused; the
status `local-verify` is required on the exact commit; the strict up-to-date
policy is ON. Three absences are deliberate and are what admits BOTH landing
modes (`landing-modes.md` §3): no pull-request rule (it would kill the direct
push), no review rule (a one-account owner cannot approve their own pull
request, and the ruling lives on the item), no bypass actor (silent on push,
and it would make the status theatre).

`protections/bootstrap_ruleset.py` applies it idempotently through the host
CLI: dry run by default, `--apply` to create or update by name, `--check`
(exit 1 on drift; offline exit 0, `--strict` exit 2), `--enforcement
evaluate|disabled` as the logged escape for ONE landing, restored right
after and ledgered as an orchestrator entry. After `--apply` it prints the
repository-settings command — merge commits only, delete-branch-on-merge —
for the owner to run; it never runs it and never deletes a ruleset. A 403 or
"upgrade" answer prints the paid-plan hint: rulesets on a private user-owned
repository need a paid plan — make the repository public, move it to an
organisation, or apply the classic branch-protection fallback of
`ci/README.md` §3. Another host implements the two properties of
`landing-modes.md` §3 with its own means.

**Reviewed-diff substitute on a one-account repository.** Where a reviewed
diff to the operations doc is wanted and CODEOWNERS cannot act (review rules
work only through pull requests, and one account cannot approve its own), a
push ruleset restricting that file's path with the repository admin as the
always-bypass actor turns every edit into a host-logged bypass. An option,
described here; no payload ships.

## 3. The status poster

`protections/post_local_verify.sh <receipt.exit> [--tree <train worktree>]
[--context local-verify]` posts ONE commit status — context `local-verify`,
state `success`, description `EXIT=0 run=<run-id>` — on the receipt's
`HEAD=`. It refuses `EXIT≠0` naming the receipt; refuses a `HEAD=` that is
not the tree's HEAD naming both SHAs; refuses a `BASE=` that is not an
ancestor; needs `gh` on PATH and an authenticated session (else exit 1 with
the manual `gh api repos/{owner}/{repo}/statuses/<HEAD> …` form); reads the
combined status first and exits 0 `already posted` when the context stands
in state success (idempotent by read-back — no local state file, no second
call); on HTTP 422 exits 1 naming `git push origin HEAD:refs/heads/<current
branch>` (origin does not hold the commit yet). It never posts any state but
success, never posts `LOG=`, never rewrites a receipt, and is run by the
lander, never by a lane.

## 4. The CI signal (M-12)

`protections/ci_signal.sh [--workflow verify.yml] [--branch main]` prints
nothing offline; authenticated, it prints the last conclusion of the verify
workflow on the default branch and, when any exist, one line per open train
pull request (`landing-modes.md` §7 has the line shapes). A red run is
announced with the failing job names and the command that tells the three
red causes apart — a red X is three different things (`verify-portfolio.md`)
— never with a verdict. The mode table for every workflow example is
`ci/README.md` §2; the pull-request-triggered review and security lanes are
kept as the PR-mode advisory lanes and are never deleted for being idle in
direct-push mode (owner ruling).

## 5. The ledger lint (M-7)

`gates/check_choices_protocol.py` lints the FORM of the choices ledger, never
its truth. The schema it lints is `../interpretation/choices-ledger-README.md`
§1–§4, read as: the title names the train; one `## Lane \`<name>\`` section
per boarder — boarders from `--boarders`, else the `board <lane> (<sha>)`
lines of `<train>-*.log` under `--receipts` (`TRAIN_ARTIFACTS`), else the
sections themselves — and every lane section names its boarded SHA; every
entry line carries a stable ID (`<lane>-<n>` / `O-<n>`, in bold or as
`id:`), a verdict word and a confidence; no `unsound` without a fix note in
the same section; no hedge phrase (one English list, shared with the report
lint); a single-boarder train carries the blocker line `single-lane train —
priority …`; with `--at-push`, a `## Landing` section with `landing mode:`,
`receipts:` and `local-verify: posted|skipped <reason>` lines, `pr: <n>` in
pr mode, and `override reason:` when direct-push overrides a pr default
(`--default-mode`, default pr).

`[HARD]` findings exit 1; `--warn` prints `[WARN]` and exits 0 — the first
train's form (`WARN` on the first train, `HARD` on the next, by a reviewed
diff). A missing ledger is HARD. The fix is always to finish the ledger. The
landing guard runs the lint at every landing under its own switch
`protocol`: `FACTORY_GUARD_ALLOW=landing` skips the receipt, boarder and
registry checks but never the lint, and `FACTORY_GUARD_ALLOW=protocol` turns
findings into a logged context note; the guard passes the project's declared
default mode from `FACTORY_LANDING_MODE_DEFAULT` (unset = `pr`) so the
`override reason:` rule matches train-plan §5. The boarder list the guard
hands the lint is the union of the train's merge commits (`board <lane>
(<sha>)` subjects, second parents) and the ledger's own sections, so a
renamed or missing lane section is a finding. The assembler exports
`TRAIN_NAME` and `TRAIN_ARTIFACTS` into the gate environment so the WARN
cheap gate finds its inputs (`../harness/train-plan.md` §2 row 6).

## 6. The close-out (M-13)

The duties list is `lander-duties.md` §8, one list for both modes.
`gates/check_landing_closeout.py --state <state file>` reads the
`landing-in-progress.json` the landing guard wrote after a registered landing
and prints one `[CLOSEOUT] [ ] <duty>. Fix: <command>` line per open duty —
every check written as CONTAINS, never equals (in pr mode main's tip is the
merge commit); exit 0 when all are closed, 1 otherwise, 2 when the
apparatus is missing. Optional legs run only when bound: `--port-range` for
listeners, `--floor-gb` for disk, `--build-check <cmd>` for freshness.

The `closeout` rule (harness `Stop`, and `SessionStart` with source
`compact|resume`) runs the same check while the state file exists. All
closed on `Stop` → the state file and its marker are deleted, one `closeout`
line goes to the events log, silence. Open → on `Stop` a denial (exit 2)
listing every duty with its exact command and naming the escape — up to
three times; after three the stop is allowed with a loud note and the duties
stay in the state file (the Stop-hook law, `../harness/guards.md` §5). After a
compaction or resume the list is context, never a block. The escape is the
word `closeout` in the state directory's allow file (a Stop hook has no
command to read a prefix from); a state file deleted by hand is logged as
`state-removed` the next time the rule runs. The rule performs no duty.

## 7. Gate legs that protect the criteria

- **Drift leg (M-8)** — `gates/check_migration_heads.py` (registry helpers,
  the part `check_backlog.py` imports; the ADR side is wired into
  `check_backlog.adr_registry_problems`): a `claimed` row whose numbered
  file already exists on `origin/<default>` or `<default>` → `[HARD] claimed
  <kind> number NNNN is landed on main; flip the row`. On a lane branch where
  the file exists only locally the leg is silent; outside git it is silent.
  No switch — fix the leg if it is wrong, never the row.
- **Duplicate-id leg (M-17a)** — `gates/check_backlog.py`
  `duplicate_row_id_problems`, wired into `main()` before the
  closing-evidence leg: two rows with the same id → `[HARD] duplicate backlog
  row id <id> appears N times (lines a, b)`. The canonical id form is the
  parser's own.
- **Never-weaken check (M-17d)** — `gates/check_gate_weakening.py` over a
  train range: a baseline whose tolerated volume grew without an `--update`
  commit touching it; a gate script changed without a paired changed test
  naming it; a net loss of `assert` lines under the tests dir. WARN on the
  first train, `--hard` after; a `Gate-change: ADR-NNNN` trailer in the
  range documents the exception and is printed. Globs and directories are
  parameters (`--baseline-glob`, `--gate-glob`, `--tests-dir`).

`verify-portfolio.md` ("Legs that bring lane-green closer to train-green")
owns where each leg runs.

## 8. Adapter table

| Mechanism | Claude Code | Coding CLI | git hooks | CI | Server |
|---|---|---|---|---|---|
| M-10 git hooks | the same rules through the dispatcher's `Git*` pseudo-events | the AGENTS.md paragraph: a red hook is fixed, never bypassed | the three tracked shims + `git_hooks.py` | — | — |
| M-11 ruleset | the `landing` rule refuses the landing forms client-side | the wrapper's pre-landing check | `pre-push` (override mode) | — | `ci/ruleset-main.json.example` via `bootstrap_ruleset.py` |
| Status poster | a lander shell step | a wrapper step | — | — | the status the policy requires |
| M-12 CI signal | `SessionStart` plain stdout (reminders script) | printed before the first prompt | — | `verify.yml.example`; the advisory lanes | — |
| M-7 ledger lint | inside the `landing` rule under switch `protocol` | the wrapper runs the gate at handback | inside `pre-push` | a WARN cheap gate on the train | — |
| M-13 close-out | `Stop` deny / `SessionStart compact\|resume` context | the wrapper prints `check_landing_closeout` | — | — | — |
| M-8 / M-17a / M-17d legs | — | — | — | cheap gates in verify | — |

## 9. What stays human

The pull-request merge ruling (landing authority is read by the lander,
never delegated to the host); the content of an `override reason:`; whether
to promote CI to a required context; the adjudication of a red run
(product bug, starvation, stale state); the fate of an advisory lane. A
mechanism here can require that a choice is RECORDED — the ledger lint
checks that `override reason:` exists, not that it is good — never that it
is right (`../harness/guards.md` §12).

## 10. What the tests prove — and what they do not

`bash verification/tests/test_git_hooks.sh` — real `git commit` and `git
push` through the tracked shims against a bare local origin, plus the
landing rule's pull-request forms through the harness entry — and
`bash verification/tests/test_landing_protections.sh` — the poster, the
bootstrap and the CI signal against a fake `gh` that RECORDS every call, the
three gates and the two legs by the documented `python3 -m scripts.<gate>`
form on a temp copy, the close-out Stop rule through the harness entry:

| Test / case | Proves | Section |
|---|---|---|
| hooks 1 | `status` exits 1 until `install`; the shims are executable | §1 |
| hooks 2 | a push to main without a receipt, with a red receipt, or with a receipt for another HEAD is refused naming the cause and both sha8; a green receipt for HEAD is accepted and origin/main moves exactly there | §1.1 |
| hooks 3 | `train/*` and `lane/*` pushes are silent; deleting main is refused | §1.1 |
| hooks 4 | source without the trailer refused; trailer + record accepted; `--amend -m` dropping the trailer refused "measured against HEAD~1"; a dangling record refused; docs-only, a merge commit accepted; a bad subject is a WARN with exit 0 | §1.2 |
| hooks 5 | a config identity other than the declared one, and an environment override over a declared config, are refused via `git var`; an unset declaration is a WARN; the log holds only the declared identity | §1.3 |
| hooks 6 | the `landing` switch from the environment and the `commit-refs` switch from the state-dir allow file are honoured from a linked worktree and logged with their source | `../harness/guards.md` §4 |
| hooks 8 | `gh pr merge --merge --match-head-commit <HEAD>` with a green receipt allowed; `--squash/--rebase/--auto/--admin` and a missing `--match-head-commit` denied naming the form; `gh pr create` from `lane/*` denied; after a merge whose SECOND PARENT is HEAD the landing registers (contains, never equals) and the state file says mode pr; an origin/main that does not contain HEAD is exit 2 | `landing-modes.md` §4 |
| hooks 7 | `git push --no-verify` bypasses the hook and logs nothing — git's own escape; the harness rule (`harness/tests/test_guards.sh` case 4) is the only refusal of the flag | §1 |
| protections 1–7 | the poster: one statuses call with context/state/description on a green receipt; no call on `EXIT=2` or a HEAD mismatch; `already posted` without a second call; 422 names the integration-branch push; no `gh` and an unauthenticated `gh` each name the manual step | §3 |
| protections 8–14 | the bootstrap: create on an empty listing with nothing written in a dry run; `--apply` POSTs the example JSON byte-for-byte; a round-tripped identical ruleset is `unchanged`; `evaluate` on the host is `update` (`PUT rulesets/<id>`, `--check` exit 1); 403 prints the paid-plan hint; no `gh` is `not verified (offline)` exit 0, `--strict` exit 2; the payload carries no pull-request rule, no review rule, no bypass actor and strict on | §2 |
| protections 15–20 | the CI signal: RED with the failing job and the `--log-failed` hint; GREEN as one exact line; unauthenticated and absent `gh` silent; an open train pull request line | §4 |
| protections 21 | close-out duties over a real primary + train worktree merged through a merge commit: reap with unlink + remove + branch -d; the remote train branch; pr OPEN → duty, MERGED → none, offline → a note; the primary behind → the exact `pull --ff-only`; floor 0 silent, an unreachable floor a duty; reaped → exit 0 | §6 |
| protections 22 | the Stop rule: denial with the checklist and the escape; the count in the state file; three → allowed with a note; the allow-file word logged as a switch; manual deletion → `state-removed`; every duty closed → state deleted and `closeout` logged | §6 |
| protections 23 | the ledger lint: missing ledger; entry without an ID; unsound without a fix note; a hedge; `--at-push` without `## Landing`; direct-push against a pr default without `override reason:`; the complete ledger; `--warn`; `TRAIN_NAME` | §5 |
| protections 24 | the drift leg: claimed migration and ADR rows whose files are on origin/main are HARD naming the numbers; a claim whose file exists only on the lane branch is silent | §7 |
| protections 25 | the duplicate-id leg names both lines and is wired before the closing-evidence leg | §7 |
| protections 26 | never-weaken: a grown baseline, an unpaired gate edit and a net assert loss are WARN findings, `--hard` exit 1, an `--update` commit and a paired test clear them, a `Gate-change:` trailer documents the exception | §7 |

Self-falsification (authoring run, on scratch copies through
`TEST_PROTECTIONS_ROOT`): replacing the ancestor test in the landing rule's
post-tool check with an equality test turned exactly hooks 8f and 8g red (the
merge whose second parent is HEAD no longer registers, so no state file);
short-circuiting the `HEAD~1` measurement in `commit_msg.staged_diff` turned
exactly hooks 4c red; making the poster skip the read-back turned exactly
protections case 4 red. Nothing else moved. `guard_dispatch.py falsify` on
the package replays 101 cases (49 planted violations, 52 green forms) over
the eight rules, and 101/101 again on a copy that keeps `verification/gates`
beside the package.

What the tests do **not** prove:

- **A live host.** The hooks are proved over a bare local origin and the
  bootstrap against a fake `gh`; whether a real host refuses a push without
  the status, or a pull request behind main, is INSTALL step 7's falsification
  in a throwaway repository (`falsification.md` rule 16, `ci/README.md` §5).
- **The train filter of the CI signal.** The `train/*` selection runs inside
  the host CLI's `--jq`; the fake returns the formatted line and cannot
  exercise the filter.
- **The advisory lanes' bodies.** They are the source factory's workflows
  and run only on that factory's host; the package proves their headers and
  the regime by reading, not by running.
- **`falsify` on a copy of `guards/` + `adapters/` alone.** The landing and
  close-out rules read a gate; a copy without `verification/gates` beside
  the package notes the missing gate loudly (fail-open) and its landing
  cases cannot be replayed there. The package's own test copies the gates
  beside the package.

## 11. Provenance

Distilled from a source factory's 2026 analysis of what could be made
deterministic and its second implementation wave (the git-hook driver and
shims, the ruleset script, the status producer, the CI line, the ledger
lint, the close-out check and the gate legs). The adaptation moves the
ruleset payload into a JSON example, sets the strict up-to-date policy and
admits a pull-request merge beside the direct push, replaces the per-SHA
state file with a status read-back, lints this package's ledger schema, reads
every check as contains-not-equals, and removes every repository name, port,
identity, issue reference and non-English string (`../skills/ATTRIBUTION.md`).
