#!/usr/bin/env bash
# test_guards.sh — exercises harness/guards/ + harness/adapters/ on a throwaway COPY.
#
# Runs under bash 3.2+ or zsh 5 (`bash harness/tests/test_guards.sh`; exit 0 = all hold).
# Needs: python3, /bin/sh, ps, awk, git. Every temp path contains a space on purpose —
# except the fake CLI and the lane directory of case 11, which are space-free because
# `ps` joins its columns with spaces (harness/guards.md §13 names the limitation).
#
# Every case sets FACTORY_GUARD_STATE_DIR and FACTORY_GUARD_LOG under the temp dir,
# scrubs FACTORY_GUARD_ALLOW / FACTORY_GUARD_DISABLED / CLAUDE_ENV_FILE /
# FACTORY_GUARD_DIR / CLAUDE_PROJECT_DIR (the entry runs under `env -i`), sets
# FACTORY_GUARD_OFFLINE=1, feeds a JSON payload to the REAL entry
# `python3 <copy>/adapters/factory_guard.py <event>` and asserts the exit code AND a
# message needle AND which stream carried it. Direct main() calls are never used: a
# direct call without the state-dir override writes into the primary checkout's events log.
#
# TEST_GUARDS_ROOT=<dir containing harness/> selects the tree under test (default: this
# package) — how the self-falsification in guards.md §13 ran the mutated scratch copies.
#
# Cases (harness/guards.md §13 lists what each proves):
#   1  empty / garbage payload and an unknown event → exit 0, no output
#   2  verdict table: denied forms name the pipe stage, the rewritten form and the switch;
#      a subshell, a brace group and a bash -c string are seen through; `git commit -m push`
#      is not a push; allowed forms are silent; GATES bind from env and from the env file
#   3  identity table: text-match process selection denied naming the launcher's identity
#      form; a sh -c string seen through; the launcher form, the ps|awk mention, lsof by
#      port, pgrep -x, grep for the word, kill <pid> allowed
#   4  no-verify table, incl. the `-c core.hooksPath=` override and a bash -c string
#   5  switches: env, command prefix (`prefix:` in the log), state-dir allow file, env-file
#      export, DISABLED=1 (log verdicts {"*":"disabled"}); one events-log line per denial
#      and per switch use; another rule's switch does not silence this one; env + env-file
#      allow sets are unioned and both named
#   6  a crashing rule fails OPEN with a loud note; a module without ID/EVENTS/check is
#      skipped with a loader note, never a crash
#   7  channels: PostToolUse note → stdout JSON only; PreToolUse deny → stderr only, exit 2;
#      GitPrePush pseudo-event with a planted context rule → stderr text, exit 0
#   8  state dir resolves to the PRIMARY from a linked worktree (its allow file is read);
#      the override is honoured (the primary's allow file is not read); a package kept
#      outside the repo (FACTORY_GUARD_DIR) still logs into the primary's state dir, and
#      the reminders script names the same dir
#   9  `falsify` writes the receipt with N ok lines (N = the shipped cases) and exits 0,
#      also under a FACTORY_GUARD_GATES binding; a planted wrong needle in the copy →
#      exactly one FAIL line, exit 1 — the copy carries verification/gates beside the
#      package, because the landing and close-out rules read a gate
#  10  lint helper: a planted forbidden form (pgrep -f) → path:line; marked line → silent; the package's own
#      harness/ tree is lint-clean under the default roots
#  11  reminders: session-start prints the guards line, the GUARD BINDINGS line (unbound or
#      the values), the PROTECTIONS BINDINGS line, the DISABLED warning, the landing line;
#      no GIT HOOKS line while the protections driver is absent; compact prints the keep-list;
#      prompt prints LIVE LANES only while a fakecli runs with the token and dir flag —
#      never for a shell whose text mentions them
#  12  the settings example parses; every command path it names exists in adapters/; it
#      carries an env block; no PreCompact leg, no bulk-read shunt entry
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${TEST_GUARDS_ROOT:-$HERE/../..}"
ROOT="$(cd "$ROOT" && pwd -P)"
SRC="$ROOT/harness"
[ -d "$SRC/guards" ] && [ -d "$SRC/adapters" ] || { echo "need $SRC/guards and $SRC/adapters"; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "need python3"; exit 2; }

T="$(mktemp -d "${TMPDIR:-/tmp}/guards test.XXXXXX")"
T="$(cd "$T" && pwd -P)"
L="$(mktemp -d /tmp/guards-lane.XXXXXX)"   # space-free on purpose: case 11 (ps joins argv)
cleanup() {
  local p
  for p in $(cat "$T/pids" 2>/dev/null); do kill -TERM "$p" 2>/dev/null; done
  sleep 0.2
  rm -rf "$T" "$L"
}
trap cleanup EXIT

PASS=0; FAIL=0; SKIP=0; N=0
ok()   { N=$((N+1)); PASS=$((PASS+1)); printf 'ok %d - %s\n' "$N" "$1"; }
bad()  { N=$((N+1)); FAIL=$((FAIL+1)); printf 'not ok %d - %s\n    %s\n' "$N" "$1" "${2:-}"; }
skip() { N=$((N+1)); SKIP=$((SKIP+1)); printf 'ok %d - SKIP %s\n' "$N" "$1"; }
check() { # name condition-exit-code detail
  if [ "$2" -eq 0 ]; then ok "$1"; else bad "$1" "${3:-}"; fi
}
has() { case "$1" in *"$2"*) return 0 ;; esac; return 1; }

# ---------------------------------------------------------------- fixtures
fresh_copy() { # dir → a copy of guards/ + adapters/ under it, and verification/gates beside them
  mkdir -p "$1"
  cp -R "$SRC/guards" "$1/guards"
  cp -R "$SRC/adapters" "$1/adapters"
  # the landing and close-out rules read a gate (verification/protections.md §5, §6); a copy of
  # guards/ + adapters/ alone would note the missing gate loudly and replay none of their cases
  mkdir -p "$1/verification" && cp -R "$SRC/../verification/gates" "$1/verification/gates"
  find "$1" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
}
COPY="$T/copy one"; fresh_copy "$COPY"
ENTRY="$COPY/adapters/factory_guard.py"
mkdir -p "$T/logs"
OUT="$T/out"; ERR="$T/err"; RC=0
SESSION="sess-1"
PLANTED='make check-backlog 2>&1 | tail -6; echo EXIT=$?'

payload() { # event command [tool]
  python3 -c 'import json,sys; print(json.dumps({"hook_event_name": sys.argv[1], "tool_name": sys.argv[3], "tool_input": {"command": sys.argv[2]}, "cwd": sys.argv[4], "session_id": sys.argv[5]}))' \
    "$1" "$2" "${3:-Bash}" "$T" "$SESSION"
}
run_hook() { # event payload [VAR=value ...] — the real entry, scrubbed environment
  local event="$1" data="$2"; shift 2
  printf '%s' "$data" | env -i PATH="$PATH" HOME="$HOME" \
    FACTORY_GUARD_STATE_DIR="$STATE" FACTORY_GUARD_LOG="$LOG" FACTORY_GUARD_OFFLINE=1 "$@" \
    python3 "$ENTRY" "$event" > "$OUT" 2> "$ERR"
  RC=$?
}
run_raw() { # event payload [VAR=value ...] — no state dir and no log preset (case 8)
  local event="$1" data="$2"; shift 2
  printf '%s' "$data" | env -i PATH="$PATH" HOME="$HOME" FACTORY_GUARD_OFFLINE=1 "$@" \
    python3 "$ENTRY" "$event" > "$OUT" 2> "$ERR"
  RC=$?
}
last_record() { # prints: <verdicts json> <switches joined by space>
  python3 -c 'import json,sys; rows=[json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]; r=rows[-1]; print(json.dumps(r["verdicts"], sort_keys=True), " ".join(r["switches"]))' "$LOG"
}
deny_case() { # label command needle
  run_hook PreToolUse "$(payload PreToolUse "$2")"
  check "$1" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" "$3" && [ ! -s "$OUT" ]; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
}
allow_case() { # label command
  run_hook PreToolUse "$(payload PreToolUse "$2")"
  check "$1" "$( [ "$RC" -eq 0 ] && [ ! -s "$OUT" ] && [ ! -s "$ERR" ]; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
}

# ---------------------------------------------------------------- case 1
STATE="$T/state one"; LOG="$T/logs/1.jsonl"
run_hook PreToolUse ""
check "1a empty payload → exit 0, no output" "$( [ "$RC" -eq 0 ] && [ ! -s "$OUT" ] && [ ! -s "$ERR" ]; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
run_hook PreToolUse "not json at all"
check "1b garbage payload → exit 0, no output" "$( [ "$RC" -eq 0 ] && [ ! -s "$OUT" ] && [ ! -s "$ERR" ]; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
run_hook Bogus "$(payload Bogus "$PLANTED")"
check "1c unknown event with a planted violation → exit 0, no output" "$( [ "$RC" -eq 0 ] && [ ! -s "$OUT" ] && [ ! -s "$ERR" ]; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"

# ---------------------------------------------------------------- case 2
STATE="$T/state two"; LOG="$T/logs/2.jsonl"
deny_case "2a gate | tail is refused naming the stage" "$PLANTED" 'GUARD verdict: a verdict cannot be read through «| tail»'
check "2b the refusal carries the rewritten form and the switch" "$( has "$(cat "$ERR")" 'make check-backlog > <lane>-check-backlog.log 2>&1; echo EXIT=$?' && has "$(cat "$ERR")" 'Switch: FACTORY_GUARD_ALLOW=verdict (logged)'; echo $? )" "$(cat "$ERR")"
deny_case "2c pytest | head" 'pytest tests -q | head -3' '«| head»'
deny_case "2d make verify | grep is refused" "make verify 2>&1 | grep -E 'passed|failed'" '«| grep»'
deny_case "2d2 pipefail after the gate pipeline does not permit a pipe" "make verify | grep passed; set -o pipefail" '«| grep»'
deny_case "2e python3 -m scripts.check_x | tail" 'python3 -m scripts.check_backlog | tail -2' '«| tail»'
deny_case "2f gate; git push in one call" 'make check-backlog; git push origin HEAD:main' '«; git push»'
check "2g the push refusal names the next call" "$( has "$(cat "$ERR")" 'then, in the NEXT call when EXIT=0: git push origin HEAD:main'; echo $? )" "$(cat "$ERR")"
deny_case "2h cat receipt; git push" 'cat t-42-1.exit; git push origin HEAD:main' '«; git push»'
deny_case "2i two gates && push" 'make check-backlog && make check-numbers && git push origin HEAD:main' '«; git push»'
allow_case "2j grep on a log | tail" 'grep -n FAILED verify-t-42.log | tail -5'
allow_case "2k ls | tail" 'ls -t artifacts | tail -3'
deny_case "2l pipefail does not permit gate output through tee" 'set -o pipefail; make check-backlog 2>&1 | tee t-42.log; echo EXIT=${PIPESTATUS[0]}' '«| tee»'
deny_case "2l2 pipefail does not permit gate output through grep" 'set -eo pipefail; make check-backlog | grep passed' '«| grep»'
deny_case "2l3 even gate help output may not be piped" 'make check-backlog --help | head -20' '«| head»'
allow_case "2m redirect + echo EXIT=\$?" 'make check-backlog > lane-backlog.log 2>&1; echo EXIT=$?'
allow_case "2n receipt alone" 'cat t-42-1.exit'
allow_case "2n2 push of a lane branch alone" 'git push origin lane/x'
allow_case "2n3 two gates chained" 'make check-backlog && make check-numbers'
deny_case "2n4 receipt then push of ANY branch in one call is still refused" 'cat t-42-1.exit; git push origin lane/x' '«; git push»'
deny_case "2n5 grep receipt then push is refused" "grep '^EXIT=0$' t-42-1.exit; git push origin lane/x" '«; git push»'
deny_case "2n6 source receipt then push is refused" 'source t-42-1.exit; git push origin lane/x' '«; git push»'
deny_case "2n7 dot-source receipt then push is refused" '. t-42-1.exit; git push origin lane/x' '«; git push»'
allow_case "2n8 deleting a stale receipt before push is not a verdict read" 'rm stale.exit; git push origin lane/x'
run_hook PreToolUse "$(payload PreToolUse 'npm run verify 2>&1 | tail -3')" FACTORY_GUARD_GATES='verify,npm'
check "2o FACTORY_GUARD_GATES binds the gate names (npm runner refused)" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" '«| tail»'; echo $? )" "rc=$RC err=$(cat "$ERR")"
run_hook PreToolUse "$(payload PreToolUse 'make check-backlog | tail -1')" FACTORY_GUARD_GATES='npm'
check "2p a gate outside FACTORY_GUARD_GATES is not gated" "$( [ "$RC" -eq 0 ] && [ ! -s "$ERR" ]; echo $? )" "rc=$RC err=$(cat "$ERR")"
deny_case "2q a gate inside a bash -c string is seen through" 'bash -c "make check-backlog | tail -3"' '«| tail»'
deny_case "2r a gate inside a subshell piped to tail" '(make check-backlog 2>&1) | tail -5' '«| tail»'
deny_case "2s a gate inside a brace group piped to tail" '{ make check-backlog; } | tail -3' '«| tail»'
check "2s2 the subshell refusal rewrites the bare gate, not the wrapper" "$( has "$(cat "$ERR")" 'Fix, exactly: make check-backlog > <lane>-check-backlog.log 2>&1; echo EXIT=$?'; echo $? )" "$(cat "$ERR")"
allow_case "2t git commit -m push after a gate is a commit, not a push" 'make check-backlog; git commit -m push'
printf "export FACTORY_GUARD_GATES='verify,npm'\n" > "$T/bind env"
run_hook PreToolUse "$(payload PreToolUse 'npm run verify 2>&1 | tail -3')" CLAUDE_ENV_FILE="$T/bind env"
check "2u a FACTORY_GUARD_GATES export in the env file binds the gate names too" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" '«| tail»'; echo $? )" "rc=$RC err=$(cat "$ERR")"

# ---------------------------------------------------------------- case 3
STATE="$T/state three"; LOG="$T/logs/3.jsonl"
# forbidden form — planted violations for the identity table
deny_case "3a pkill -f is refused naming the port form" 'pkill -f serve.py' 'GUARD identity: «pkill -f»'
check "3b the pkill refusal names lsof by port and the launcher's identity form with placeholders" "$( has "$(cat "$ERR")" 'lsof -ti :<port>' && has "$(cat "$ERR")" 'harness/launch_lane.sh running <cli> <token>'; echo $? )" "$(cat "$ERR")"
# forbidden form — planted violation
deny_case "3c pgrep -fl" 'pgrep -fl "<cli> <token>"' 'GUARD identity: «pgrep -f» matches the inspecting shell'
# forbidden form — planted violation
deny_case "3d pgrep --full | wc -l" "pgrep --full 'x y' | wc -l" '«pgrep -f»'
# forbidden form — planted violation
deny_case "3e ps aux | grep" "ps aux | grep '[s]erve.py'" 'GUARD identity: «ps aux | grep»'
# forbidden form — planted violation
deny_case "3f cd then pgrep -af" 'cd /tmp && pgrep -af serve' '«pgrep -f»'
# forbidden form — planted violation
run_hook PreToolUse "$(payload PreToolUse 'pgrep -fl "lanecli exec"')" FACTORY_GUARD_CLI=lanecli FACTORY_GUARD_CLI_TOKEN=exec
check "3g the identity form is filled from FACTORY_GUARD_CLI / _CLI_TOKEN" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" 'Fix: harness/launch_lane.sh running lanecli exec.'; echo $? )" "$(cat "$ERR")"
allow_case "3h the launcher's identity form itself" 'harness/launch_lane.sh running lanecli exec'
allow_case "3h2 the ps | awk mention is green (not a text match), though not the recommended form" "ps -axo pid=,comm=,args= | awk '\$2==\"lanecli\" && /exec/'"
allow_case "3i lsof by port; pgrep -x; kill <pid>" 'lsof -ti :4310; pgrep -x lanecli; kill 4711'
allow_case "3j grep for the word" 'grep -rn pgrep docs'
# forbidden form — planted violation inside a shell -c string
deny_case "3k pgrep -f inside sh -c is seen through" "sh -c 'pgrep -f serve'" 'GUARD identity: «pgrep -f»'

# ---------------------------------------------------------------- case 4
STATE="$T/state four"; LOG="$T/logs/4.jsonl"
deny_case "4a git commit --no-verify" "git commit --no-verify -m 'x'" 'GUARD no-verify: «git commit --no-verify» skips the git hooks'
check "4b the refusal names the fix and the switch" "$( has "$(cat "$ERR")" 'Fix: run «git commit» without the flag' && has "$(cat "$ERR")" 'Switch: FACTORY_GUARD_ALLOW=no-verify (logged)'; echo $? )" "$(cat "$ERR")"
deny_case "4c git -C wt commit -n" "git -C wt commit -n -m 'x'" '«git commit --no-verify»'
deny_case "4c2 git commit -an groups --all with --no-verify" "git commit -an -m 'x'" '«git commit --no-verify»'
deny_case "4c3 git commit -qn groups --quiet with --no-verify" "git commit -qn -m 'x'" '«git commit --no-verify»'
deny_case "4d git push --no-verify" 'git push --no-verify origin lane/x' '«git push --no-verify»'
deny_case "4e git merge --no-verify" 'git merge --no-verify lane/x' '«git merge --no-verify»'
allow_case "4f plain commit" "git commit -m 'x'"
allow_case "4f2 git merge -qn keeps merge's non-bypass -n semantics" "git merge -qn lane/x"
allow_case "4f3 git push -qn keeps push's dry-run -n semantics" "git push -qn origin lane/x"
allow_case "4g grep for the flag" 'grep -rn -- --no-verify docs'
deny_case "4h git -c core.hooksPath=… commit is refused as the override" "git -c core.hooksPath=/dev/null commit -m 'x'" 'GUARD no-verify: «git -c core.hooksPath=/dev/null commit» skips the git hooks'
check "4h2 the override refusal names the fix without the override" "$( has "$(cat "$ERR")" 'Fix: run «git commit» without the override'; echo $? )" "$(cat "$ERR")"
deny_case "4i --no-verify inside a bash -c string is seen through" 'bash -c "git commit --no-verify -m x"' '«git commit --no-verify»'
allow_case "4j another -c config on a commit passes" "git -c user.email=lane@example.invalid commit -m 'x'"

# ---------------------------------------------------------------- case 5
STATE="$T/state five"; LOG="$T/logs/5.jsonl"
run_hook PreToolUse "$(payload PreToolUse "$PLANTED")" FACTORY_GUARD_ALLOW=verdict
rec="$(last_record)"
check "5a env switch: the planted violation passes; log says switched + env source" "$( [ "$RC" -eq 0 ] && has "$rec" '"verdict": "switched"' && has "$rec" 'env:FACTORY_GUARD_ALLOW=verdict'; echo $? )" "rc=$RC rec=$rec"
run_hook PreToolUse "$(payload PreToolUse "FACTORY_GUARD_ALLOW=verdict $PLANTED")"
rec="$(last_record)"
check "5b command-prefix switch: passes; log source prefix:" "$( [ "$RC" -eq 0 ] && has "$rec" 'prefix:FACTORY_GUARD_ALLOW=verdict'; echo $? )" "rc=$RC rec=$rec"
mkdir -p "$STATE"; printf '# note\nverdict\n' > "$STATE/factory-guard-allow"
run_hook PreToolUse "$(payload PreToolUse "$PLANTED")"
rec="$(last_record)"
rm -f "$STATE/factory-guard-allow"
check "5c state-dir allow file: passes; log source file:" "$( [ "$RC" -eq 0 ] && has "$rec" 'file:factory-guard-allow=verdict'; echo $? )" "rc=$RC rec=$rec"
printf "export FACTORY_GUARD_ALLOW='verdict'\n" > "$T/claude env"
run_hook PreToolUse "$(payload PreToolUse "$PLANTED")" CLAUDE_ENV_FILE="$T/claude env"
rec="$(last_record)"
check "5d env-file export: passes; log source env-file:" "$( [ "$RC" -eq 0 ] && has "$rec" 'env-file:FACTORY_GUARD_ALLOW=verdict'; echo $? )" "rc=$RC rec=$rec"
run_hook PreToolUse "$(payload PreToolUse "$PLANTED")" FACTORY_GUARD_DISABLED=1
rec="$(last_record)"
check "5e DISABLED=1: passes; log verdicts {\"*\": \"disabled\"}" "$( [ "$RC" -eq 0 ] && has "$rec" '{"*": "disabled"}'; echo $? )" "rc=$RC rec=$rec"
disabled_event="$(awk -F '\t' 'END {print $4 "|" $5 "|" $6}' "$STATE/factory-events.log")"
check "5e2 DISABLED=1 appends a global allow-switch event naming its source" "$( [ "$disabled_event" = 'allow-switch|*|env:FACTORY_GUARD_DISABLED=1' ]; echo $? )" "event=$disabled_event"
run_hook PreToolUse "$(payload PreToolUse "FACTORY_GUARD_ALLOW=landing $PLANTED")"
check "5f another rule's switch does not silence this one" "$( [ "$RC" -eq 2 ]; echo $? )" "rc=$RC"
kinds="$(cut -f4 "$STATE/factory-events.log" 2>/dev/null | sort | uniq -c | tr -s ' ' | tr '\n' ';')"
check "5g events log: one deny line and five allow-switch lines, all for this session" "$( has "$kinds" '5 allow-switch' && has "$kinds" '1 deny' && [ "$(cut -f2 "$STATE/factory-events.log" | sort -u)" = "$SESSION" ]; echo $? )" "kinds=$kinds"
check "5h the allow-switch line names the source" "$( grep 'allow-switch' "$STATE/factory-events.log" | grep -q 'prefix:FACTORY_GUARD_ALLOW=verdict'; echo $? )"
printf "export FACTORY_GUARD_ALLOW='identity'\n" > "$T/claude env two"
run_hook PreToolUse "$(payload PreToolUse "$PLANTED")" FACTORY_GUARD_ALLOW=verdict CLAUDE_ENV_FILE="$T/claude env two"
rec="$(last_record)"
check "5i env ALLOW=verdict + env-file ALLOW=identity: the sets are unioned and both sources named" "$( [ "$RC" -eq 0 ] && has "$rec" '"identity": "switched"' && has "$rec" '"verdict": "switched"' && has "$rec" 'env:FACTORY_GUARD_ALLOW=verdict' && has "$rec" 'env-file:FACTORY_GUARD_ALLOW=identity'; echo $? )" "rc=$RC rec=$rec"

# ---------------------------------------------------------------- case 6
COPY6="$T/copy six"; fresh_copy "$COPY6"
cat > "$COPY6/guards/rules/zz_crash.py" <<'EOF'
ID = "zz-crash"
EVENTS = frozenset({"PreToolUse"})
MATCHER = "Bash"
def check(payload, context):
    raise RuntimeError("planted crash")
def falsification_cases(workdir):
    return []
EOF
printf 'x = 1\n' > "$COPY6/guards/rules/zz_noid.py"
STATE="$T/state six"; LOG="$T/logs/6.jsonl"
ENTRY="$COPY6/adapters/factory_guard.py"
run_hook PreToolUse "$(payload PreToolUse 'ls')"
check "6a a crashing rule fails OPEN: exit 0 + additionalContext with the loud note" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'GUARD zz-crash: rule crashed and let the call through' && has "$(cat "$OUT")" 'planted crash' && [ ! -s "$ERR" ]; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
check "6b a module without ID/EVENTS/check is skipped with a loader note, never a crash" "$( has "$(cat "$OUT")" 'rule module zz_noid.py lacks ID, EVENTS, check and was skipped'; echo $? )" "$(cat "$OUT")"
run_hook PreToolUse "$(payload PreToolUse "$PLANTED")"
check "6c the other rules still refuse beside a crashing one (exit 2)" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" 'GUARD verdict:'; echo $? )" "rc=$RC err=$(cat "$ERR")"
ENTRY="$COPY/adapters/factory_guard.py"

# ---------------------------------------------------------------- case 7
COPY7="$T/copy seven"; fresh_copy "$COPY7"
cat > "$COPY7/guards/rules/zz_note.py" <<'EOF'
from guards._common import Verdict
ID = "zz-note"
EVENTS = frozenset({"PostToolUse", "GitPrePush"})
MATCHER = None
def check(payload, context):
    return Verdict("context", ID, "planted note for the channel test")
def falsification_cases(workdir):
    return []
EOF
STATE="$T/state seven"; LOG="$T/logs/7.jsonl"
ENTRY="$COPY7/adapters/factory_guard.py"
run_hook PostToolUse "$(payload PostToolUse 'ls')"
check "7a PostToolUse note → stdout additionalContext JSON only, exit 0" "$( [ "$RC" -eq 0 ] && [ ! -s "$ERR" ] && python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); h=d["hookSpecificOutput"]; sys.exit(0 if h["hookEventName"]=="PostToolUse" and "planted note" in h["additionalContext"] else 1)' "$OUT"; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
run_hook PreToolUse "$(payload PreToolUse "$PLANTED")"
check "7b PreToolUse deny → stderr only, exit 2" "$( [ "$RC" -eq 2 ] && [ ! -s "$OUT" ] && has "$(cat "$ERR")" 'GUARD verdict:'; echo $? )" "rc=$RC out=$(cat "$OUT")"
git_payload="$(python3 -c 'import json,sys; print(json.dumps({"hook_event_name": "GitPrePush", "git": {"hook": "pre-push", "refs": []}, "cwd": sys.argv[1], "session_id": sys.argv[2]}))' "$T" "$SESSION")"
run_hook GitPrePush "$git_payload"
check "7c GitPrePush pseudo-event: note → stderr text, stdout empty, exit 0" "$( [ "$RC" -eq 0 ] && [ ! -s "$OUT" ] && has "$(cat "$ERR")" 'planted note for the channel test'; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
ENTRY="$COPY/adapters/factory_guard.py"

# ---------------------------------------------------------------- case 8
P="$T/repo primary"; W="$T/repo wt"
mkdir -p "$P"
( cd "$P" && git init -q && git symbolic-ref HEAD refs/heads/main && git -c user.email=t@example.invalid -c user.name=t commit -q --allow-empty -m init ) 2>/dev/null
git -C "$P" worktree add -q -b lane/x "$W" 2>/dev/null
if [ ! -f "$W/.git" ]; then
  skip "8 linked worktree could not be created on this host"
else
  mkdir -p "$P/.factory-guard"; printf 'verdict\n' > "$P/.factory-guard/factory-guard-allow"
  LOG="$T/logs/8.jsonl"
  run_raw PreToolUse "$(payload PreToolUse "$PLANTED")" CLAUDE_PROJECT_DIR="$W" FACTORY_GUARD_LOG="$LOG"
  rec="$(last_record)"
  check "8a from a linked worktree the PRIMARY's allow file is read (state dir = primary)" "$( [ "$RC" -eq 0 ] && has "$rec" 'file:factory-guard-allow=verdict' && [ ! -e "$W/.factory-guard" ]; echo $? )" "rc=$RC rec=$rec"
  run_raw PreToolUse "$(payload PreToolUse "$PLANTED")" CLAUDE_PROJECT_DIR="$W" FACTORY_GUARD_LOG="$LOG" FACTORY_GUARD_STATE_DIR="$T/state eight"
  rec="$(last_record)"
  check "8b FACTORY_GUARD_STATE_DIR overrides: the primary's allow file is not read (exit 2, no file: source)" "$( [ "$RC" -eq 2 ] && ! has "$rec" 'file:factory-guard-allow'; echo $? )" "rc=$RC rec=$rec"
  # the package kept OUTSIDE the repository: FACTORY_GUARD_DIR locates it and nothing else
  rm -rf "$P/.factory-guard"
  ELSEWHERE="$T/else where"; fresh_copy "$ELSEWHERE"
  printf '%s' "$(payload PreToolUse "git commit --no-verify -m 'x'")" | env -i PATH="$PATH" HOME="$HOME" FACTORY_GUARD_OFFLINE=1 \
    FACTORY_GUARD_DIR="$ELSEWHERE/guards" CLAUDE_PROJECT_DIR="$W" python3 "$ELSEWHERE/adapters/factory_guard.py" PreToolUse > "$OUT" 2> "$ERR"; RC=$?
  # observed through the verdict log (like 8a through the allow file), never the events log,
  # so the "drop the events-log write" mutation of guards.md §13 keeps mapping to case 5 alone
  check "8c with FACTORY_GUARD_DIR outside the repo, the verdict log lands in the PRIMARY's state dir, nothing beside the package or the worktree" \
    "$( [ "$RC" -eq 2 ] && grep -q '"no-verify": "deny"' "$P/.factory-guard/factory-guard.log" && [ ! -e "$ELSEWHERE/.factory-guard" ] && [ ! -e "$T/.factory-guard" ] && [ ! -e "$W/.factory-guard" ] && [ ! -e "$T/.factory-guard.log" ] && [ ! -e "$W/.factory-guard.log" ]; echo $? )" \
    "rc=$RC $(find "$T" -name '.factory-guard*' -maxdepth 3 2>/dev/null | tr '\n' ' ')"
  printf '{"train": "t-8"}\n' > "$P/.factory-guard/landing-in-progress.json"
  out="$(printf '{}' | env -i PATH="$PATH" HOME="$HOME" FACTORY_GUARD_DIR="$ELSEWHERE/guards" CLAUDE_PROJECT_DIR="$W" /bin/sh "$ELSEWHERE/adapters/factory_reminders.sh" session-start 2>/dev/null)"
  check "8d the reminders script resolves the same state dir as the dispatcher (names the primary's landing file)" "$( has "$out" "Delete $P/.factory-guard/landing-in-progress.json"; echo $? )" "$out"
  rm -rf "$P/.factory-guard"
fi

# ---------------------------------------------------------------- case 9
expected="$(PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys, pathlib; sys.path.insert(0, sys.argv[1]); from guards import load_report; mods, problems = load_report(); print(sum(len(m.falsification_cases(pathlib.Path(sys.argv[2]))) for m in mods) if not problems else -1)' "$COPY" "$T/w9")"
env -i PATH="$PATH" HOME="$HOME" python3 "$COPY/guards/guard_dispatch.py" falsify --lane t-1 --out "$T/falsify out" > "$OUT" 2> "$ERR"; rc=$?
receipt="$T/falsify out/t-1-guard-falsification.log"
check "9a falsify on the copy: exit 0, receipt written, summary printed" "$( [ "$rc" -eq 0 ] && [ -f "$receipt" ] && has "$(cat "$OUT")" "t-1: $expected cases, $expected ok, 0 FAIL"; echo $? )" "rc=$rc out=$(cat "$OUT") err=$(cat "$ERR")"
check "9b the receipt has exactly N ok lines (N = $expected shipped cases) and no FAIL" "$( [ "$(grep -c ' ok   ' "$receipt")" -eq "$expected" ] && ! grep -q 'FAIL' "$receipt"; echo $? )" "$(grep -c ' ok   ' "$receipt") ok lines"
check "9c every line has the shape RED|GREEN ok <rule>/<case>: <detail>" "$( ! grep -vE '^(RED|GREEN) +ok +[a-z-]+/[a-z0-9-]+: ' "$receipt" >/dev/null; echo $? )" "$(grep -vE '^(RED|GREEN) +ok +[a-z-]+/[a-z0-9-]+: ' "$receipt" | head -2)"
env -i PATH="$PATH" HOME="$HOME" FACTORY_GUARD_GATES=npm FACTORY_GUARD_CLI=othercli python3 "$COPY/guards/guard_dispatch.py" falsify --lane t-3 --out "$T/falsify out" > "$OUT" 2> "$ERR"; rc=$?
check "9c2 falsify under a FACTORY_GUARD_GATES / _CLI binding still exits 0 (the receipt proves the shipped tables)" "$( [ "$rc" -eq 0 ] && has "$(cat "$OUT")" "t-3: $expected cases, $expected ok, 0 FAIL"; echo $? )" "rc=$rc out=$(cat "$OUT") $(grep FAIL "$T/falsify out/t-3-guard-falsification.log" | head -3)"
check "9c3 falsify leaves no __pycache__ beside the package" "$( [ -z "$(find "$COPY" -name __pycache__ -type d)" ]; echo $? )" "$(find "$COPY" -name __pycache__ -type d)"
COPY9="$T/copy nine"; fresh_copy "$COPY9"
python3 -c 'import sys, pathlib; p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8"); old = "\"GUARD no-verify: «git push --no-verify»\""; assert t.count(old) == 1, t.count(old); p.write_text(t.replace(old, "\"GUARD nope: «git push --no-verify»\""), encoding="utf-8")' "$COPY9/guards/rules/no_verify.py"
env -i PATH="$PATH" HOME="$HOME" python3 "$COPY9/guards/guard_dispatch.py" falsify --lane t-2 --out "$T/falsify out" > "$OUT" 2> "$ERR"; rc=$?
receipt9="$T/falsify out/t-2-guard-falsification.log"
check "9d a planted wrong needle → exit 1 and exactly one FAIL line naming the case" "$( [ "$rc" -eq 1 ] && [ "$(grep -c 'FAIL' "$receipt9")" -eq 1 ] && grep -q '^RED   FAIL no-verify/push-no-verify:' "$receipt9"; echo $? )" "rc=$rc $(grep FAIL "$receipt9")"

# ---------------------------------------------------------------- case 10
LR="$T/lint root"; mkdir -p "$LR/harness"
# forbidden form — planted for the lint helper
printf 'pgrep -f serve\n' > "$LR/harness/x.sh"
printf '# the next line is a forbidden form, quoted\npgrep -f serve\n' > "$LR/harness/y.sh"
printf 'ps aux | grep serve  # forbidden form\n' > "$LR/harness/z.md"
lint() { PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys, pathlib; sys.path.insert(0, sys.argv[1]); from guards.rules.identity import lint_findings; print("\n".join(lint_findings(pathlib.Path(sys.argv[2]))))' "$COPY" "$1"; }
found="$(lint "$LR")"
# forbidden form — the expected finding text below quotes it
check "10a a planted pgrep -f is reported as path:line: text" "$( [ "$found" = 'harness/x.sh:1: pgrep -f serve' ]; echo $? )" "found=$found"
check "10b marked lines (same line or previous non-blank line) are silent" "$( ! has "$found" 'y.sh' && ! has "$found" 'z.md'; echo $? )" "found=$found"
found="$(lint "$ROOT")"
check "10c the package's own harness/ tree is lint-clean under the default roots" "$( [ -z "$found" ]; echo $? )" "found=$found"

# ---------------------------------------------------------------- case 11
REM="$COPY/adapters/factory_reminders.sh"
STATE="$T/state eleven"; mkdir -p "$STATE"
rem() { # leg [VAR=value ...]
  local leg="$1"; shift
  printf '{}' | env -i PATH="$PATH" HOME="$HOME" FACTORY_GUARD_STATE_DIR="$STATE" "$@" /bin/sh "$REM" "$leg" 2>"$ERR"
}
out="$(rem session-start)"
check "11a session-start names the mounted rules and the switch forms, no warning" "$( has "$out" 'FACTORY GUARDS' && has "$out" 'identity' && has "$out" 'no-verify' && has "$out" 'verdict' && has "$out" 'FACTORY_GUARD_ALLOW=<id>' && ! has "$out" 'WARNING'; echo $? )" "$out"
check "11a2 session-start prints the bindings line with 'unbound' while nothing is bound" "$( has "$out" 'GUARD BINDINGS: cli=unbound token=unbound dir-flag=unbound gates=unbound'; echo $? )" "$out"
out="$(rem session-start FACTORY_GUARD_CLI=fakecli FACTORY_GUARD_CLI_TOKEN=exec FACTORY_GUARD_GATES=npm)"
check "11a3 session-start prints the bound values" "$( has "$out" 'GUARD BINDINGS: cli=fakecli token=exec dir-flag=unbound gates=npm'; echo $? )" "$out"
check "11a4 session-start prints the PROTECTIONS BINDINGS line with 'unbound' while nothing is bound, and no GIT HOOKS line without the driver" "$( has "$out" 'PROTECTIONS BINDINGS: default-branch=unbound git-email=unbound source-prefix=unbound' && ! has "$out" 'GIT HOOKS'; echo $? )" "$out"
out="$(rem session-start FACTORY_GUARD_DEFAULT_BRANCH=trunk FACTORY_GUARD_GIT_EMAIL=lander@example.invalid)"
check "11a5 the PROTECTIONS BINDINGS line prints the bound values" "$( has "$out" 'PROTECTIONS BINDINGS: default-branch=trunk git-email=lander@example.invalid source-prefix=unbound'; echo $? )" "$out"
out="$(rem session-start FACTORY_GUARD_DISABLED=1)"
check "11b session-start warns when FACTORY_GUARD_DISABLED=1" "$( has "$out" 'WARNING: FACTORY_GUARD_DISABLED=1'; echo $? )" "$out"
printf '{"train": "t-9"}\n' > "$STATE/landing-in-progress.json"
out="$(rem session-start)"
rm -f "$STATE/landing-in-progress.json"
check "11c session-start names an open landing from the state file" "$( has "$out" 'LANDING IN PROGRESS: train t-9'; echo $? )" "$out"
out="$(rem compact)"
check "11d compact prints the keep-list with 'live lanes: none' while the CLI is unbound" "$( has "$out" 'AFTER COMPACTION, KEEP' && has "$out" 'live lanes: none'; echo $? )" "$out"
mkdir -p "$L/bin" "$L/lane-a"
ln -s /bin/sh "$L/bin/fakecli"
rem_cli() { rem "$1" FACTORY_GUARD_CLI=fakecli FACTORY_GUARD_CLI_TOKEN=exec FACTORY_GUARD_CLI_DIR_FLAG=--cd; }
out="$(rem_cli prompt)"
check "11e prompt is silent while no lane runs" "$( [ -z "$out" ]; echo $? )" "out=$out"
# a compound body: a shell given ONE simple command execs it and would report as `sleep`
"$L/bin/fakecli" -c 'sleep 6; :' exec --cd "$L/lane-a" & lane_pid=$!
/bin/sh -c 'sleep 6; : fakecli exec --cd /tmp/lane-text' & text_pid=$!
printf '%s\n%s\n' "$lane_pid" "$text_pid" >> "$T/pids"
sleep 0.5
out="$(rem_cli prompt)"
check "11f prompt names the live lane by identity (comm fakecli + exact exec + --cd operand)" "$( has "$out" 'LIVE LANES: lane-a '; echo $? )" "out=$out"
check "11g a shell whose TEXT mentions 'fakecli exec --cd' is not a lane" "$( ! has "$out" 'lane-text'; echo $? )" "out=$out"
out="$(rem prompt FACTORY_GUARD_CLI=othercli FACTORY_GUARD_CLI_TOKEN=exec FACTORY_GUARD_CLI_DIR_FLAG=--cd)"
check "11h a different bound CLI name lists nothing" "$( [ -z "$out" ]; echo $? )" "out=$out"
out="$(rem_cli compact)"
check "11i compact lists the live lane" "$( has "$out" 'live lanes: lane-a'; echo $? )" "$out"
kill "$lane_pid" "$text_pid" 2>/dev/null; wait "$lane_pid" "$text_pid" 2>/dev/null

# ---------------------------------------------------------------- case 12
check "12a the settings example parses, names only adapter scripts that exist, carries an env block, no PreCompact, no shunt" \
  "$( python3 - "$COPY" <<'EOF'
import json, pathlib, sys
copy = pathlib.Path(sys.argv[1])
data = json.loads((copy / "adapters" / "claude-code-settings.json.example").read_text(encoding="utf-8"))
hooks = data["hooks"]
assert isinstance(data.get("env"), dict) and "FACTORY_GUARD_GATES" in data["env"], "no env block binding the parameters"
assert "PreCompact" not in hooks, "PreCompact leg present"
commands = [h["command"] for rows in hooks.values() for row in rows for h in row["hooks"]]
assert commands, "no commands"
prefix = "$CLAUDE_PROJECT_DIR/harness/adapters/"
for command in commands:
    assert "shunt" not in command, command
    assert prefix in command, command
    rest = command.split(prefix, 1)[1]
    name = rest.split('"', 1)[0].split(" ", 1)[0]
    assert (copy / "adapters" / name).is_file(), name
    assert command.endswith(('" PreToolUse', '" PostToolUse', '" Stop', '" SubagentStop', '" SessionStart', ' session-start', ' compact', ' prompt')), command
for matcher in ("Bash", "Agent|Task", "Edit|Write|MultiEdit|NotebookEdit"):
    assert any(row.get("matcher") == matcher for row in hooks["PreToolUse"]), matcher
assert any(row.get("matcher") == "compact" for row in hooks["SessionStart"])
assert any(row.get("matcher") == "compact|resume" for row in hooks["SessionStart"])
EOF
echo $? )"
ln -s "$COPY" "$T/harness"
check "12b reminder commands execute a mode-0644 adapter through a project path containing spaces" \
  "$( python3 - "$COPY" "$T" <<'EOF'
import json, os, pathlib, subprocess, sys
copy = pathlib.Path(sys.argv[1])
project = pathlib.Path(sys.argv[2])
data = json.loads((copy / "adapters" / "claude-code-settings.json.example").read_text(encoding="utf-8"))
commands = [
    hook["command"]
    for rows in data["hooks"].values()
    for row in rows
    for hook in row["hooks"]
    if "factory_reminders.sh" in hook["command"]
]
assert len(commands) == 3, commands
env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project), "FACTORY_GUARD_STATE_DIR": str(project / "state")}
results = [subprocess.run(command, shell=True, executable="/bin/sh", env=env, capture_output=True, text=True) for command in commands]
assert all(result.returncode == 0 for result in results), [(result.returncode, result.stderr) for result in results]
assert "FACTORY GUARDS" in results[0].stdout, results[0].stdout
assert "AFTER COMPACTION" in results[1].stdout, results[1].stdout
EOF
echo $? )"

# ---------------------------------------------------------------- summary
printf '\n# %d passed, %d failed, %d skipped (tmp: %s)\n' "$PASS" "$FAIL" "$SKIP" "$T"
[ "$FAIL" -eq 0 ]
