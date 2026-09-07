# Install trial — a Node hello-world, 2026-09-06

`INSTALL.md` run end to end, as an installing agent would, against a repo
that has nothing the source factory has: a Node 25 hello-world with one
test, no Python project, no eval bank, no GitHub project. One lane, one
train, one landing, every falsification the runbook asks for. This file is
the record: what was done, what INSTALL got wrong, what was changed in the
package because of it, and what the trial does not prove. The artifacts it
produced that a next installer can reuse are in `node/` beside this file.

## 1. The target and the apparatus

| | |
|---|---|
| Target | `hello-node`: `src/hello.js` (`greet()`), `test/hello.test.js` (`node --test`), no dependencies; a bare local `origin.git` so `origin/main` exists without GitHub |
| Host | macOS, Node v25.8.1, `python3` 3.12 (pyenv), `gitleaks` on PATH, no Go, no Python project in the repo |
| Decision gates run with | a CLEAN `python3 -m venv` with only PyYAML installed — not the host's pyenv, which had `alembic` and `yaml` by accident and would have hidden the dependency set |
| "Model" | `fakecli`, a `/bin/sh` symlink driving a scripted body (`node/fakecli-body.sh`) — the lane's authoring is scripted, so what the trial exercises is the runbook and the harness, never a model's quality. The operator policy file says so in its implementation-lane row |
| Home | a trial `HOME` with its own `.claude/CLAUDE.md` and `model-policy.md`; the real `~/.claude` was never touched |

## 2. What was done, per INSTALL step

| Step | Done | Evidence |
|---|---|---|
| 0 survey | Node, `npm test`, no lint, no CI, no frontend, no board; verify portfolio = import-root probe + decision gates + ratchet + `node --test` | `node/Makefile` |
| 1 planning | docs copied, five `{{…}}` placeholders resolved in the brief, NUMBERS created, ADR-0001 claimed then written, board stood in by a file | `docs/BOARD.md` marked "NOT an installed board" |
| 2 gates | all 24 scripts run the documented way; 7 kept; a JavaScript lint ratchet written to the contract and falsified; a runtime import-boundary test written and falsified (first version vacuous); `make verify` green | §3 rows 3–8 |
| 3 interpretation | choices README, docs under `docs/factory/` keeping the pillar layout | — |
| 4 skills | 38 skills copied; `verify_skills_lock.py --check --root .agents/skills` → `verified: 38`; routing translated | — |
| 5 harness | `test_launch_lane.sh` on the host: 41 passed, `detach method exercised: python`; `run_receipted.py` saved from train-plan §4.2; `copy-isolation.sh` red→red→red→green, source unchanged; `identity_and_history.py` green, `--plant count-all` red | — |
| 6 user level | snippet appended; model policy filled for the one role used, 18 placeholders left in roles the trial never dispatched into; landing policy left inactive | — |
| 7.1 smoke | lane `greet-name` dispatched through the launcher: `verdict=built`, report with `run_id`, `task`, `round: 1`, `measurements`, one `choices` entry with a sidecar; wrapper committed and pushed the branch; audit → `docs/choices/t-1.md` with ID `t-1/greet-name-1` and the scenario; single-lane train (the install exception) verified through the receipt launcher: attempt 1 `EXIT=2`, attempt 2 `EXIT=0` but push rejected, attempt 3 `EXIT=0` and landed; sweep; rewrite check (0 red gates, both IDs, the negation, 28 lines / 1,217 bytes) | §3 rows 9–12 |
| 7.2 falsify | ratchet, boundary test, backlog closing evidence (non-ancestor SHA refused), gitleaks history leg (random secret on a throwaway branch → exit 1; `git branch -D` alone → exit 0) | — |
| 7.3 documented entry | every gate via `python3 -m scripts.<gate>`; `make verify` read by its own lines; no served surface → no functional trial, stated in the operations doc | — |
| 7.4 landing | no owner present, no policy file → a real install holds here; the trial landed to its local bare origin and says so in the protocol | — |
| 7.5 rounds | same task re-dispatched as `greet-name-r2`, report `round: 2`; a `Round: 3 of 2` brief refused by the wrapper's check; the launcher accepted it (it does not read the brief) | — |

## 3. What INSTALL got wrong, and what changed

| # | Finding (observed) | Change in this package |
|---|---|---|
| 1 | "Copy `planning/*.md` → `docs/`" leaves ~30 `../harness/…`, `../interpretation/…`, `../verification/…`, `../user-level/…` links dangling; `CLAUDE.md.example` is not matched by `*.md` | Step 1.1: copy the doc tree under one root keeping the pillar layout; copy the example by name |
| 2 | Step 1.6 needs `gh` + a GitHub owner; no path for a trial without a remote | Step 1.6 says what a file stand-in is (not an installed board) |
| 3 | `python scripts/<gate>.py` (INSTALL's form) → `ModuleNotFoundError: No module named 'scripts'` for every gate importing a sibling; the docstrings say `python -m scripts.<gate>` | Steps 2.1 and 7.3 use the `-m` form; gates README explains why |
| 4 | Of 24 scripts, 7 run outside a Python repo; `check_contract_touch.py` imports `scripts.check_egress`, which the package does not ship — it cannot run anywhere | Classification table in `gates/README.md`; INSTALL 2.1 copies seven |
| 5 | In a clean interpreter the decision gates need PyYAML; `check_backlog` also needed `alembic` transitively, in a repo with no migrations | `check_migration_heads.py`: `alembic` imported inside `get_heads()` (the one deviation from verbatim, recorded in the gates README); dependency stated as `python3` + PyYAML + `gitleaks` |
| 6 | ADR front matter needs `id: ADR-NNNN` (`id_mismatch` otherwise); INSTALL and `adr-and-numbers.md` listed only `status:` + `code:`. `path::Symbol` on a JS `function greet()` → "symbol gone" (Python grammar); back-references read only `*.py` | `adr-and-numbers.md`, INSTALL 1.5, gates README "ADR front matter" |
| 7 | The CI examples and `review-prompt.md` are the source factory's (Norwegian, its ADRs, its deploy target); copied under `docs/`, the prompt's ADR-0074/75/78/87 made the assembled train's `check_backlog` red — the lane's pregate never runs that gate | INSTALL 1.1 and 2.7: translate, never store under `docs/` |
| 8 | Step 4 asked to "verify the hash lock (`skills-lock.json`)" that did not exist and to copy a routing table "the template carries" — it did not | `skills/skills-lock.json` + `verify_skills_lock.py` + its test; `skills/ROUTING.md`; Step 4 rewritten |
| 9 | The report's `head_sha` is the pin when the wrapper commits; the launcher banks its four receipts, not the choices sidecar or the pregate log | `report-schema.md` comment; INSTALL 5.2/5.3 name the wrapper's banking and the handback SHA |
| 10 | Lander order: after attempt 1's `EXIT=2` nothing was pushed, but the sweep ran and marked SMOKE-1 done against the wrong SHA (my error; reverted with a revert commit). Attempt 2 was green but its push was rejected: `origin/main` had moved and the receipt's `BASE=` was not an ancestor of `HEAD=` — nothing checked that | INSTALL 7.1: receipt → push → sweep, in that order; train-plan §4.1: `BASE` must be an ancestor of `HEAD` |
| 11 | The first import-boundary test stayed green with `require('node:test')` planted: it matched `NativeModule node:test`, Node lists `NativeModule test` | INSTALL 2.6 keeps the falsification and says why; `node/import_boundary.test.js` is the corrected test |
| 12 | "Confirm it is refused" for round 3 read as if the launcher refused; it does not read the brief | INSTALL 7.5 names the wrapper's check |
| 13 | A cross-check by `grep -c claimed NUMBERS.md` counted the template's prose line | trial protocol only: count table rows by column |

## 4. The non-Python variant of the gate choice

`node/check_lint_ratchet.mjs` is the package's ratchet contract with no
Python and no linter: three regex rules over `src/`, a committed per-rule
baseline `.lint-baseline.json`, exit 1 on any increase or new rule with the
file:line of each hit, `--update` the only path to a new baseline,
`--report` exit 0, and a missing baseline is HARD. Observed: missing
baseline → exit 1; `--update` → green; one planted `console.log` →
`HARD: 1 regression(s) no-console: 3 > baseline 2 src/hello.js:7`; restored
→ exit 0. A real project replaces the regexes with `eslint --format json`
(or `tsc`, `npm audit --json`) and keeps everything else.

The import-root probe for Node is the documented entry point printing its
own origin (`node src/hello.js --where`, compared with `$(CURDIR)/src/hello.js`
in the Makefile); the runtime boundary is a subprocess that requires the
production entry and asserts nothing under `test/` and no `node:test`
builtin was loaded, with the tree's root pinned from the test file's own
path.

## 5. What the trial does not prove

- Nothing about any model: the lane was a script. The policy file is honest
  about that (`model: fakecli (scripted, no model behind it)`), and no
  number in this record is a token or cost figure.
- Nothing about landing authority: no owner was present and no policy file
  existed; the landing went to a local bare remote. A real smoke test lands
  on the owner's live ruling (INSTALL 7.4) or holds.
- Nothing about evaluation readiness beyond "not applicable": the repo has
  no served surface and no AI role, so no pre-flight smoke, functional
  trial or AI evaluation ran; the receipt shape (`evaluation-readiness.md`
  §4) is unexercised here.
- Nothing about the bulk-read pilot (unbound), the board's derived view (the
  file was the only view), or the resource contract under load (one lane on
  an idle machine).
- Single-lane trains are the install exception, not the batch policy
  (`lander-duties.md` §2 rule 5); this trial did not exercise a shared train.
- Host-specific: detachment was proven for `python` on macOS; another host
  proves its own.
