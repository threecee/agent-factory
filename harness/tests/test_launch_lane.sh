#!/usr/bin/env bash
# test_launch_lane.sh — exercises harness/launch_lane.sh against a FAKE CLI.
#
# Runs under bash 3.2+ or zsh 5 (`bash harness/tests/test_launch_lane.sh`,
# `zsh harness/tests/test_launch_lane.sh`). Needs: /bin/sh, ps, awk, git, and
# ONE detach method (setsid, python3 or perl) for the parent-termination case —
# that case is reported as SKIP, never as a pass, when none is available.
#
# Every temp path contains a space on purpose. The fake CLI is a symlink to
# /bin/sh named `fakecli`, so the kernel reports its executable identity as
# `fakecli` (a shebang script would report the interpreter instead).
#
# Cases (harness/run-lifecycle.md §10 lists what each one proves):
#   1  missing variable is refused BEFORE anything starts, naming the variable
#   2  two concurrent lanes in paths with spaces; receipts and logs never cross
#   3  same run id in start receipt, log name, report and exit receipt
#   4  non-zero exit is `died`; a log containing 42906 is NOT rate-limited
#   5  exit 0 without a report is `no-deliverable`
#   6  a named status field 429 with non-zero exit IS rate-limited
#   7  a 429 field in the log with exit 0 and a valid report is not a verdict
#   8  old receipts cannot approve a new run (not-started / unbound / stale)
#   9  process identity: an inspecting shell whose text says "fakecli exec" is
#      not a lane; the real fakecli process is
#  10  a delayed start waits for the writer lock held by a commit
#  11  a moved HEAD refuses the start (pin check); a matching pin runs
#  12  read-only run: report extracted from stdout, validated, banked
#  13  parent-harness termination: the run survives SIGTERM+SIGHUP to the
#      dispatcher's process group and still writes its exit receipt
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
LAUNCHER="$HERE/../launch_lane.sh"
[ -x "$LAUNCHER" ] || chmod +x "$LAUNCHER"
[ -x /bin/sh ] || { echo "need /bin/sh"; exit 2; }

T="$(mktemp -d "${TMPDIR:-/tmp}/launch lane test.XXXXXX")"
T="$(cd "$T" && pwd -P)"   # canonical: the launcher canonicalizes every path too
LANE_SENTINEL_DIR="$T/lane sentinel"
LANE_RESULT_PATH="$LANE_SENTINEL_DIR/default.result.md"
export LANE_SENTINEL_DIR LANE_RESULT_PATH
mkdir -p "$LANE_SENTINEL_DIR"
cleanup() {
  # kill anything still running from this test, then remove the tree
  local p
  for p in $(cat "$T/pids" 2>/dev/null); do kill -TERM "$p" 2>/dev/null; done
  for p in $(cat "$T/pgids" 2>/dev/null); do kill -TERM -- "-$p" 2>/dev/null; done
  sleep 0.3
  rm -rf "$T"
}
trap cleanup EXIT

PASS=0; FAIL=0; SKIP=0; N=0
ok()   { N=$((N+1)); PASS=$((PASS+1)); printf 'ok %d - %s\n' "$N" "$1"; }
bad()  { N=$((N+1)); FAIL=$((FAIL+1)); printf 'not ok %d - %s\n    %s\n' "$N" "$1" "${2:-}"; }
skip() { N=$((N+1)); SKIP=$((SKIP+1)); printf 'ok %d - SKIP %s\n' "$N" "$1"; }
check() { # name condition-exit-code detail
  if [ "$2" -eq 0 ]; then ok "$1"; else bad "$1" "${3:-}"; fi
}
rget() { grep "^$2=" "$1" 2>/dev/null | tail -n 1 | cut -d= -f2-; }

# ---------------------------------------------------------------- fixtures
BIN="$T/bin dir"; RUN="$T/run dir"; BANK="$T/bank dir"
mkdir -p "$BIN" "$RUN" "$T/wt a" "$T/wt b" "$T/wt c"
ln -s /bin/sh "$BIN/fakecli"
FAKE="$BIN/fakecli"
printf 'brief for the fake CLI\n' > "$T/brief a.md"
BRIEF="$T/brief a.md"

# fake CLI bodies: invoked as  fakecli <body> exec <args...>
cat > "$T/body-ok.sh" <<'EOF'
sleep "${FAKE_SLEEP:-1}"
echo "lane $LANE run $LANE_RUN_ID working in $(pwd)"
printf 'lane: %s\nrun_id: %s\nstatus: built\nreport: |-\n  fake deliverable\n' "$LANE" "$LANE_RUN_ID" > "$LANE_RESULT_PATH"
exit 0
EOF
cat > "$T/body-nodeliverable.sh" <<'EOF'
echo "did some work, wrote nothing"
exit 0
EOF
cat > "$T/body-fail.sh" <<'EOF'
echo "processed 42906 items before crashing"
exit 3
EOF
cat > "$T/body-429.sh" <<'EOF'
echo "provider replied status=429 too many requests"
exit 1
EOF
cat > "$T/body-429-ok.sh" <<'EOF'
echo "retry after status=429 succeeded"
printf 'lane: %s\nrun_id: %s\nstatus: built\n' "$LANE" "$LANE_RUN_ID" > "$LANE_RESULT_PATH"
exit 0
EOF
cat > "$T/body-readonly.sh" <<'EOF'
echo "read-only investigation, cannot write files"
echo "LANE-RESULT-BEGIN"
printf 'lane: %s\nrun_id: %s\nstatus: built\nreport: |-\n  extracted from stdout\n' "$LANE" "$LANE_RUN_ID"
echo "LANE-RESULT-END"
echo "trailing chatter"
exit 0
EOF
cat > "$T/body-timed.sh" <<'EOF'
date +%s > "$FAKE_STAMP"
printf 'lane: %s\nrun_id: %s\nstatus: built\n' "$LANE" "$LANE_RUN_ID" > "$LANE_RESULT_PATH"
exit 0
EOF

# start one lane; args: lane worktree run-id body [extra env assignments via env]
start_lane() { # lane wt run_id body
  LANE="$1" LANE_WORKTREE="$2" LANE_RUN_ID="$3" LANE_RUN_DIR="$RUN" LANE_SENTINEL_DIR="$RUN" \
    LANE_RESULT_PATH="$RUN/$1.$3.result.md" LANE_BRIEF="$BRIEF" \
    "$LAUNCHER" start -- "$FAKE" "$T/$4" exec --cd "{worktree}" --lane "{lane}"
}
wait_lane() {
  LANE="$1" LANE_RUN_ID="$2" LANE_RUN_DIR="$RUN" LANE_SENTINEL_DIR="$RUN" \
    LANE_RESULT_PATH="$RUN/$1.$2.result.md" "$LAUNCHER" wait "${3:-30}" > /dev/null
}
verdict() {
  LANE="$1" LANE_RUN_ID="$2" LANE_RUN_DIR="$RUN" LANE_SENTINEL_DIR="$RUN" \
    LANE_RESULT_PATH="$RUN/$1.$2.result.md" "$LAUNCHER" verdict
}

if [ "${1:-}" = "--caller-isolation-probe" ]; then
  start_lane c "$T/wt c" isolated body-ok.sh >/dev/null || exit $?
  wait_lane c isolated
  verdict c isolated >/dev/null
  exit $?
fi

# ---------------------------------------------------------------- caller-environment isolation
CALLER_RESULT="$T/caller result.md"; CALLER_SENTINEL="$T/caller sentinel"
probe="$(env LANE_RESULT_PATH="$CALLER_RESULT" LANE_SENTINEL_DIR="$CALLER_SENTINEL" /bin/bash "$0" --caller-isolation-probe 2>&1)"; probe_rc=$?
check "0 caller-set lane artifact paths are never written by this test" \
  "$( [ "$probe_rc" -eq 0 ] && [ ! -e "$CALLER_RESULT" ] && [ ! -e "$CALLER_SENTINEL" ]; echo $? )" "$probe"

# ---------------------------------------------------------------- case 1
out="$(LANE=one LANE_WORKTREE="$T/wt a" LANE_RUN_DIR="$RUN" "$LAUNCHER" start -- "$FAKE" "$T/body-ok.sh" exec 2>&1)"; rc=$?
check "1a missing LANE_BRIEF refused with exit 2 naming it" "$( [ "$rc" -eq 2 ] && [ "${out#*LANE_BRIEF}" != "$out" ]; echo $? )" "rc=$rc out=$out"
out="$(LANE=one LANE_WORKTREE="$T/wt a" LANE_RUN_DIR="$RUN" LANE_BRIEF="$T/nope.md" "$LAUNCHER" start -- "$FAKE" "$T/body-ok.sh" exec 2>&1)"; rc=$?
check "1b missing brief file refused with exit 2 naming the path" "$( [ "$rc" -eq 2 ] && [ "${out#*nope.md}" != "$out" ]; echo $? )" "rc=$rc out=$out"
check "1c nothing was started by the refusals" "$( [ -z "$(ls "$RUN" 2>/dev/null)" ]; echo $? )" "$(ls "$RUN")"
out="$(LANE=one LANE_WORKTREE="$T/wt a" LANE_RUN_DIR="$RUN" LANE_BRIEF="$BRIEF" "$LAUNCHER" start 2>&1)"; rc=$?
check "1d missing CLI argv refused with exit 2" "$( [ "$rc" -eq 2 ]; echo $? )" "rc=$rc out=$out"

# ---------------------------------------------------------------- case 2
outa="$(start_lane a "$T/wt a" r1 body-ok.sh)"; rca=$?
outb="$(start_lane b "$T/wt b" r1 body-ok.sh)"; rcb=$?
check "2a two lanes dispatched concurrently in paths with spaces" "$( [ "$rca" -eq 0 ] && [ "$rcb" -eq 0 ]; echo $? )" "a=$rca b=$rcb $outa $outb"
wait_lane a r1; wait_lane b r1
va="$(verdict a r1)"; rva=$?; vb="$(verdict b r1)"; rvb=$?
check "2b both verdicts are valid deliverables (exit 0, report_status=built)" "$( [ "$rva" -eq 0 ] && [ "$rvb" -eq 0 ] && [ "${va#*report_status=built}" != "$va" ] && [ "${vb#*report_status=built}" != "$vb" ]; echo $? )" "a=$rva b=$rvb"
loga="$RUN/a.r1.log"; logb="$RUN/b.r1.log"
check "2c each log holds only its own lane" "$( grep -q 'lane a run r1' "$loga" && ! grep -q 'lane b' "$loga" && grep -q 'lane b run r1' "$logb" && ! grep -q 'lane a' "$logb"; echo $? )"
check "2d the CLI ran inside its own worktree (cwd)" "$( grep -q "working in $T/wt a" "$loga" && grep -q "working in $T/wt b" "$logb"; echo $? )" "$(cat "$loga")"
check "2e placeholders substituted the worktree path with spaces" "$( args="$(rget "$RUN/a.r1.start" cli_argc)"; [ "$args" = 7 ]; echo $? )"

# ---------------------------------------------------------------- case 3
check "3a start receipt, exit receipt and report all carry run_id r1" \
  "$( [ "$(rget "$RUN/a.r1.start" run_id)" = r1 ] && [ "$(rget "$RUN/a.r1.exit" run_id)" = r1 ] && grep -q '^run_id: r1$' "$RUN/a.r1.result.md"; echo $? )"
check "3b log and result paths are named by lane and run id" "$( [ -f "$RUN/a.r1.log" ] && [ -f "$RUN/a.r1.result.md" ]; echo $? )"
check "3c the CLI saw LANE_RUN_ID and LANE_RESULT_PATH in its environment" "$( grep -q 'run r1' "$loga"; echo $? )"
check "3d a run id is single-use" "$( start_lane a "$T/wt a" r1 body-ok.sh >/dev/null 2>&1; [ $? -eq 2 ]; echo $? )"

# ---------------------------------------------------------------- case 4
start_lane c "$T/wt c" fail1 body-fail.sh > /dev/null; wait_lane c fail1
v="$(verdict c fail1)"; rv=$?
check "4a non-zero exit is verdict=died with LANE_EXIT=3 (exit 20)" "$( [ "$rv" -eq 20 ] && [ "${v#*LANE_EXIT=3}" != "$v" ] && [ "${v#*verdict=died}" != "$v" ]; echo $? )" "$v"
check "4b a log containing 42906 is NOT classified as rate-limited" "$( grep -q 42906 "$RUN/c.fail1.log" && [ "${v#*rate_limited=no}" != "$v" ]; echo $? )" "$v"

# ---------------------------------------------------------------- case 5
start_lane c "$T/wt c" nod1 body-nodeliverable.sh > /dev/null; wait_lane c nod1
v="$(verdict c nod1)"; rv=$?
check "5 exit 0 without a report is verdict=no-deliverable (exit 21)" "$( [ "$rv" -eq 21 ] && [ "${v#*deliverable=missing}" != "$v" ]; echo $? )" "$v"

# ---------------------------------------------------------------- case 6
start_lane c "$T/wt c" rl1 body-429.sh > /dev/null; wait_lane c rl1
v="$(verdict c rl1)"; rv=$?
check "6 named status field 429 + non-zero exit is died AND rate_limited=yes" "$( [ "$rv" -eq 20 ] && [ "${v#*rate_limited=yes}" != "$v" ]; echo $? )" "$v"

# ---------------------------------------------------------------- case 7
start_lane c "$T/wt c" rl2 body-429-ok.sh > /dev/null; wait_lane c rl2
v="$(verdict c rl2)"; rv=$?
check "7 a 429 field in the log with exit 0 + valid report is built, not rate-limited" "$( [ "$rv" -eq 0 ] && [ "${v#*rate_limited=no}" != "$v" ]; echo $? )" "$v"

# ---------------------------------------------------------------- case 8
v="$(verdict a r2)"; rv=$?
check "8a a new run id with only old receipts present is not-started (exit 12)" "$( [ "$rv" -eq 12 ]; echo $? )" "$v"
# an old, valid report copied to the new run's result path does not approve it
cp "$RUN/a.r1.result.md" "$RUN/a.r2.result.md"
start_lane a "$T/wt a" r2 body-nodeliverable.sh > /dev/null; wait_lane a r2
v="$(verdict a r2)"; rv=$?
check "8b an old report (run_id r1) at the new run's path is unbound-report (exit 22)" "$( [ "$rv" -eq 22 ] && [ "${v#*deliverable=unbound}" != "$v" ]; echo $? )" "$v"
# a report with the right run id but written BEFORE this start is stale
printf 'lane: a\nrun_id: r3\nstatus: built\n' > "$RUN/a.r3.result.md"
sleep 1.1
start_lane a "$T/wt a" r3 body-nodeliverable.sh > /dev/null; wait_lane a r3
v="$(verdict a r3)"; rv=$?
check "8c a correctly bound report older than this start is stale-report (exit 22)" "$( [ "$rv" -eq 22 ] && [ "${v#*deliverable=stale}" != "$v" ]; echo $? )" "$v"
# the exit receipt of r1 is not consulted for r2/r3: it still says built
check "8d r1's own exit receipt is untouched and still approves only r1" "$( [ "$(rget "$RUN/a.r1.exit" deliverable)" = valid ] && [ "$(verdict a r1 >/dev/null; echo $?)" = 0 ]; echo $? )"

# ---------------------------------------------------------------- case 9
FAKE_SLEEP=3 start_lane c "$T/wt c" ident1 body-ok.sh > /dev/null
cli_pid="$(rget "$RUN/c.ident1.start" cli_pid)"
/bin/sh -c 'sleep 3; : fakecli exec --cd "x"' & shell_pid=$!
printf '%s\n' "$shell_pid" >> "$T/pids"
sleep 0.5
running="$(LANE_RUN_DIR="$RUN" "$LAUNCHER" running fakecli exec)"
check "9a the real fakecli process is listed by executable identity" "$( printf '%s\n' "$running" | grep -q "^$cli_pid "; echo $? )" "pid=$cli_pid running=$running"
check "9b the inspecting shell whose text says 'fakecli exec' is not listed" "$( ! printf '%s\n' "$running" | grep -q "^$shell_pid "; echo $? )" "shell=$shell_pid running=$running"
check "9c the start receipt observed the CLI's executable as fakecli" "$( [ "$(rget "$RUN/c.ident1.start" cli_comm_observed)" = fakecli ]; echo $? )" "$(rget "$RUN/c.ident1.start" cli_comm_observed)"
v="$(verdict c ident1)"; rv=$?
check "9d verdict while alive is running (exit 10)" "$( [ "$rv" -eq 10 ]; echo $? )" "$v"
wait "$shell_pid" 2>/dev/null; wait_lane c ident1

# ---------------------------------------------------------------- case 10
# hold the writer lock as if a wrapper commit were in progress, then dispatch a
# delayed start whose delay elapses INSIDE the commit window.
LANE=hold LANE_WORKTREE="$T/wt c" LANE_RUN_DIR="$RUN" "$LAUNCHER" with-writer-lock -- \
  /bin/sh -c 'sleep 3; date +%s > "$1"' sh "$T/commit done" &
lock_pid=$!; printf '%s\n' "$lock_pid" >> "$T/pids"
sleep 0.3
LANE_DELAY_S=1 FAKE_STAMP="$T/cli started" start_lane c "$T/wt c" delay1 body-timed.sh > "$T/start delay.out"
check "10a delayed start returns immediately with state=delayed" "$( grep -q '^state=delayed$' "$T/start delay.out"; echo $? )" "$(cat "$T/start delay.out")"
v="$(verdict c delay1)"; rv=$?
check "10b verdict during the delay is delayed (exit 11)" "$( [ "$rv" -eq 11 ]; echo $? )" "$v"
wait "$lock_pid"; wait_lane c delay1
commit_done="$(cat "$T/commit done")"; cli_started="$(cat "$T/cli started")"
check "10c the CLI started only after the commit released the writer lock" "$( [ "$cli_started" -ge "$commit_done" ]; echo $? )" "cli_started=$cli_started commit_done=$commit_done"
check "10d the delayed run still delivered (exit 0)" "$( verdict c delay1 >/dev/null; echo $? )"

# ---------------------------------------------------------------- case 11
mkdir -p "$T/wt git"
( cd "$T/wt git" && git init -q && git -c user.email=t@example.invalid -c user.name=t commit -q --allow-empty -m init ) 2>/dev/null
pin="$(git -C "$T/wt git" rev-parse HEAD)"
out="$(LANE_PIN_SHA=0000000000000000000000000000000000000000 start_lane g "$T/wt git" pin1 body-ok.sh 2>&1)"; rc=$?
check "11a a HEAD that does not match the pin is refused at start (exit 4, head-moved)" "$( [ "$rc" -eq 4 ] && [ "${out#*head-moved}" != "$out" ]; echo $? )" "rc=$rc $out"
v="$(verdict g pin1)"; rv=$?
check "11b verdict for the refused run is refused-start (exit 14)" "$( [ "$rv" -eq 14 ]; echo $? )" "$v"
check "11c no CLI log was produced by the refused run" "$( [ ! -f "$RUN/g.pin1.log" ]; echo $? )"
LANE_PIN_SHA="$pin" start_lane g "$T/wt git" pin2 body-ok.sh > /dev/null; rc=$?
wait_lane g pin2
check "11d a matching pin runs and delivers" "$( [ "$rc" -eq 0 ] && verdict g pin2 >/dev/null; echo $? )"

# ---------------------------------------------------------------- case 12
LANE_MODE=read-only LANE_ARTIFACT_BANK="$BANK" start_lane c "$T/wt c" ro1 body-readonly.sh > /dev/null; wait_lane c ro1
v="$(verdict c ro1)"; rv=$?
check "12a read-only run: report extracted from stdout and valid (exit 0)" "$( [ "$rv" -eq 0 ] && grep -q '^run_id: ro1$' "$RUN/c.ro1.result.md" && grep -q 'extracted from stdout' "$RUN/c.ro1.result.md"; echo $? )" "$v"
check "12b extraction stops at the end marker (no trailing chatter)" "$( ! grep -q 'trailing chatter' "$RUN/c.ro1.result.md"; echo $? )"
check "12c receipts and report were banked under <bank>/<lane>/<run_id>" "$( [ -f "$BANK/c/ro1/c.ro1.result.md" ] && [ -f "$BANK/c/ro1/c.ro1.log" ] && [ "$(rget "$BANK/c/ro1/c.ro1.exit" LANE_EXIT)" = 0 ]; echo $? )" "$(ls "$BANK/c/ro1" 2>&1)"
LANE_MODE=read-only start_lane c "$T/wt c" ro2 body-nodeliverable.sh > /dev/null; wait_lane c ro2
v="$(verdict c ro2)"; rv=$?
check "12d read-only exit 0 without markers is no-deliverable (exit 21)" "$( [ "$rv" -eq 21 ]; echo $? )" "$v"

# ---------------------------------------------------------------- case 13
# a "parent harness" in its own session dispatches the lane, then is killed
# (TERM + HUP to its whole process group) while the lane is still running.
parent_cmd="LANE=orphan LANE_WORKTREE='$T/wt c' LANE_RUN_ID=o1 LANE_RUN_DIR='$RUN' LANE_SENTINEL_DIR='$RUN' LANE_RESULT_PATH='$RUN/orphan.o1.result.md' LANE_BRIEF='$BRIEF' FAKE_SLEEP=3 '$LAUNCHER' start -- '$FAKE' '$T/body-ok.sh' exec > '$T/orphan start.out' 2>&1; sleep 60"
parent_pid=""
if command -v setsid >/dev/null 2>&1; then
  setsid /bin/sh -c "$parent_cmd" & parent_pid=$!
elif command -v python3 >/dev/null 2>&1; then
  python3 -c 'import os,sys; os.setsid(); os.execvp("/bin/sh", ["/bin/sh","-c",sys.argv[1]])' "$parent_cmd" & parent_pid=$!
elif command -v perl >/dev/null 2>&1; then
  perl -e 'use POSIX qw(setsid); setsid(); exec "/bin/sh","-c",$ARGV[0]' "$parent_cmd" & parent_pid=$!
fi
disown 2>/dev/null || true
if [ -z "$parent_pid" ]; then
  skip "13 parent-harness termination: no setsid/python3/perl on this platform"
else
  printf '%s\n' "$parent_pid" >> "$T/pgids"
  waited=0
  while [ ! -f "$RUN/orphan.o1.start" ] || [ "$(rget "$RUN/orphan.o1.start" state)" != started ]; do
    sleep 0.2; waited=$((waited+1)); [ "$waited" -gt 100 ] && break
  done
  pgid="$(ps -o pgid= -p "$parent_pid" | tr -d ' ')"
  runner_pgid="$(rget "$RUN/orphan.o1.start" runner_pgid)"
  check "13a the run's session is not the dispatcher's process group" "$( [ -n "$runner_pgid" ] && [ "$runner_pgid" != "$pgid" ]; echo $? )" "runner_pgid=$runner_pgid parent_pgid=$pgid"
  kill -TERM -- "-$pgid" 2>/dev/null; sleep 0.2; kill -HUP -- "-$pgid" 2>/dev/null
  sleep 0.5
  check "13b the dispatcher's process group is gone" "$( ! kill -0 "$parent_pid" 2>/dev/null; echo $? )"
  wait_lane orphan o1 20; rw=$?
  v="$(verdict orphan o1)"; rv=$?
  check "13c the run survived and wrote its exit receipt; verdict built (exit 0)" "$( [ "$rw" -eq 0 ] && [ "$rv" -eq 0 ]; echo $? )" "wait=$rw $v"
  printf 'detach method exercised: %s\n' "$(rget "$RUN/orphan.o1.start" detach)"
fi

# ---------------------------------------------------------------- summary
printf '\n# %d passed, %d failed, %d skipped (tmp: %s)\n' "$PASS" "$FAIL" "$SKIP" "$T"
[ "$FAIL" -eq 0 ]
