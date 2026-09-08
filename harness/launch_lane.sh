#!/usr/bin/env bash
# launch_lane.sh — parameterized lane launcher with run-bound receipts.
#
# The CONTRACT lives in harness/run-lifecycle.md (every rule has its home there);
# this file is the mechanism. Nothing here knows your repo, your paths, your
# provider or your credentials: every input is an environment variable or an
# argument, and the launcher never reads a .env or a key file.
#
# Usage
#   launch_lane.sh start -- <cli> [args...]        dispatch ONE run of ONE lane, detached
#   launch_lane.sh wait [timeout-s]                block until this run's exit receipt exists
#   launch_lane.sh verdict                         judge THIS run from THIS run's receipts
#   launch_lane.sh running <cli-name> <token>      live lane processes by executable identity
#   launch_lane.sh with-writer-lock -- <cmd...>    run <cmd> holding the worktree's writer lock
#   launch_lane.sh env                             print the resolved contract (never secrets)
#
# argv placeholders (substituted in every argument after `--`):
#   {brief}       the contents of $LANE_BRIEF        {brief_path}  its path
#   {worktree}    $LANE_WORKTREE (absolute)          {lane}        $LANE
#   {run_id}      $LANE_RUN_ID                       {result_path} $LANE_RESULT_PATH
#
# Environment — required for `start`: LANE, LANE_WORKTREE, LANE_RUN_DIR, LANE_BRIEF,
# LANE_QUOTA_RECEIPT, LANE_ROSTER_CHECK.
# Required for `wait`/`verdict`: LANE, LANE_RUN_DIR, LANE_RUN_ID.
# Optional (defaults in resolve_contract): LANE_RUN_ID, LANE_DELAY_S, LANE_DETACH,
# LANE_MODE, LANE_PIN_SHA, LANE_ARTIFACT_BANK, LANE_RATE_LIMIT_REGEX,
# LANE_RESULT_BEGIN, LANE_RESULT_END, LANE_START_TIMEOUT_S, LANE_LOCK_TIMEOUT_S,
# LANE_SENTINEL_DIR, LANE_RESULT_PATH, LANE_USAGE_PARSER, LANE_LOOP_OWNER,
# LANE_EXPECTED_END, LANE_STOP_CMD, LANE_QUOTA_MAX_AGE_MIN.
# Required for `start`: LANE_QUOTA_RECEIPT and executable LANE_ROSTER_CHECK.
#
# Exit codes — start: 0 dispatched (state started or delayed), 2 contract violation
# (the message names the variable/file), 3 runner never checked in, 4 refused at
# start (head moved, writer lock timeout, identity mismatch).
# verdict: 0 valid deliverable; 10 running; 11 delayed; 12 not-started; 13 vanished;
# 14 refused-start; 20 died (non-zero exit or signal); 21 no-deliverable (exit 0,
# no report); 22 unbound/stale report (wrong run_id, or older than this start);
# 23 invalid report (missing lane/status); 2 contract violation.
#
# Compatible with bash 3.2 (macOS) and newer; the receipts are plain key=value text.

set -u

SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
STATUSES_RE='^status: (built|parked|blocked|refused|failed)[[:space:]]*$'

# ---------------------------------------------------------------- utilities

die() { printf 'launch_lane: %s\n' "$*" >&2; exit 2; }
say() { printf '%s\n' "$*"; }
now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }
now_epoch() { date +%s; }

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
  elif command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else printf 'unavailable'; fi
}
sha256_str() {
  if command -v shasum >/dev/null 2>&1; then printf '%s' "$1" | shasum -a 256 | cut -d' ' -f1
  elif command -v sha256sum >/dev/null 2>&1; then printf '%s' "$1" | sha256sum | cut -d' ' -f1
  else printf '%s' "$1" | cksum | cut -d' ' -f1; fi
}
mtime_epoch() {
  if stat -f %m "$1" >/dev/null 2>&1; then stat -f %m "$1"; else stat -c %Y "$1"; fi
}
pid_alive() { kill -0 "$1" 2>/dev/null; }

# comm of ONE pid, untruncated (a multi-column `ps -o comm=` truncates on macOS).
pid_comm() { ps -o comm= -p "$1" 2>/dev/null | sed 's/^[[:space:]]*//'; }
pid_args() { ps -ww -o args= -p "$1" 2>/dev/null; }

# Process identity = executable basename + exact argv token (never a text match
# on the command line, which also selects the shell that is inspecting).
is_lane_process() { # pid cli-name token
  local comm base tok
  comm="$(pid_comm "$1")"; [ -n "$comm" ] || return 1
  base="$(basename "$comm")"
  [ "$base" = "$2" ] || return 1
  for tok in $(pid_args "$1"); do [ "$tok" = "$3" ] && return 0; done
  return 1
}

# receipts: append-only key=value lines; the LAST occurrence of a key wins.
receipt_set() { printf '%s=%s\n' "$2" "$3" >> "$1"; }
receipt_get() { [ -f "$1" ] && grep "^$2=" "$1" | tail -n 1 | cut -d= -f2-; }

# ------------------------------------------------------------- the contract

require_var() {
  local name="$1"
  eval "local v=\${$name:-}"
  [ -n "$v" ] || die "missing required variable $name"
}

resolve_contract() { # $1 = start|wait|verdict|lock|env
  local mode="$1"
  require_var LANE
  require_var LANE_RUN_DIR
  case "$LANE" in *[!A-Za-z0-9._-]*|"") die "LANE must match [A-Za-z0-9._-]+ (got '$LANE')";; esac
  mkdir -p "$LANE_RUN_DIR" || die "cannot create LANE_RUN_DIR=$LANE_RUN_DIR"
  LANE_RUN_DIR="$(cd "$LANE_RUN_DIR" && pwd -P)"

  if [ "$mode" = start ] || [ "$mode" = lock ] || [ "$mode" = env ]; then
    require_var LANE_WORKTREE
    [ -d "$LANE_WORKTREE" ] || die "LANE_WORKTREE is not a directory: $LANE_WORKTREE"
    LANE_WORKTREE="$(cd "$LANE_WORKTREE" && pwd -P)"
  fi
  if [ "$mode" = start ] || [ "$mode" = env ]; then
    require_var LANE_BRIEF
    [ -f "$LANE_BRIEF" ] || die "LANE_BRIEF is not a file: $LANE_BRIEF"
    LANE_BRIEF="$(cd "$(dirname "$LANE_BRIEF")" && pwd -P)/$(basename "$LANE_BRIEF")"
    require_var LANE_QUOTA_RECEIPT
    [ -f "$LANE_QUOTA_RECEIPT" ] || die "LANE_QUOTA_RECEIPT is not a file: $LANE_QUOTA_RECEIPT"
    LANE_QUOTA_RECEIPT="$(cd "$(dirname "$LANE_QUOTA_RECEIPT")" && pwd -P)/$(basename "$LANE_QUOTA_RECEIPT")"
    require_var LANE_ROSTER_CHECK
    [ -x "$LANE_ROSTER_CHECK" ] || die "LANE_ROSTER_CHECK is not executable: $LANE_ROSTER_CHECK"
    LANE_ROSTER_CHECK="$(cd "$(dirname "$LANE_ROSTER_CHECK")" && pwd -P)/$(basename "$LANE_ROSTER_CHECK")"
  fi

  if [ "$mode" = start ] || [ "$mode" = env ] || [ "$mode" = lock ]; then
    : "${LANE_RUN_ID:=$LANE-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
  else
    require_var LANE_RUN_ID
  fi
  case "$LANE_RUN_ID" in *[!A-Za-z0-9._-]*|"") die "LANE_RUN_ID must match [A-Za-z0-9._-]+ (got '$LANE_RUN_ID')";; esac

  : "${LANE_DELAY_S:=0}"
  case "$LANE_DELAY_S" in ''|*[!0-9]*) die "LANE_DELAY_S must be a non-negative integer";; esac
  : "${LANE_DETACH:=auto}"
  : "${LANE_MODE:=write}"
  case "$LANE_MODE" in write|read-only) ;; *) die "LANE_MODE must be write or read-only";; esac
  : "${LANE_PIN_SHA:=}"
  : "${LANE_ARTIFACT_BANK:=}"
  : "${LANE_RATE_LIMIT_REGEX:=(^|[^A-Za-z0-9_])(status|code|HTTP/[0-9.]+)[ =:]+429([^0-9]|$)}"
  : "${LANE_RESULT_BEGIN:=LANE-RESULT-BEGIN}"
  : "${LANE_RESULT_END:=LANE-RESULT-END}"
  : "${LANE_START_TIMEOUT_S:=30}"
  : "${LANE_LOCK_TIMEOUT_S:=600}"
  : "${LANE_QUOTA_MAX_AGE_MIN:=30}"
  case "$LANE_QUOTA_MAX_AGE_MIN" in ''|*[!0-9]*) die "LANE_QUOTA_MAX_AGE_MIN must be a non-negative integer";; esac
  : "${LANE_SENTINEL_DIR:=$LANE_RUN_DIR}"
  : "${LANE_USAGE_PARSER:=}"
  : "${LANE_LOOP_OWNER:=$LANE}"
  : "${LANE_EXPECTED_END:=none}"
  : "${LANE_STOP_CMD:=}"

  RUN_BASE="$LANE_RUN_DIR/$LANE.$LANE_RUN_ID"
  START_RECEIPT="$RUN_BASE.start"
  EXIT_RECEIPT="$RUN_BASE.exit"
  COST_RECEIPT="$RUN_BASE.cost"
  RUN_LOG="$RUN_BASE.log"
  RUNNER_LOG="$RUN_BASE.runner.log"
  : "${LANE_RESULT_PATH:=$RUN_BASE.result.md}"

  export LANE LANE_RUN_ID LANE_RUN_DIR LANE_SENTINEL_DIR LANE_RESULT_PATH
  export LANE_DELAY_S LANE_DETACH LANE_MODE LANE_PIN_SHA LANE_ARTIFACT_BANK
  export LANE_RATE_LIMIT_REGEX LANE_RESULT_BEGIN LANE_RESULT_END
  export LANE_START_TIMEOUT_S LANE_LOCK_TIMEOUT_S
  export LANE_QUOTA_RECEIPT LANE_QUOTA_MAX_AGE_MIN LANE_ROSTER_CHECK
  export LANE_USAGE_PARSER LANE_LOOP_OWNER LANE_EXPECTED_END LANE_STOP_CMD
  [ "${LANE_WORKTREE:-}" ] && export LANE_WORKTREE
  [ "${LANE_BRIEF:-}" ] && export LANE_BRIEF
  return 0
}

print_env() {
  local k
  for k in LANE LANE_RUN_ID LANE_WORKTREE LANE_BRIEF LANE_RUN_DIR LANE_SENTINEL_DIR \
           LANE_RESULT_PATH LANE_DELAY_S LANE_DETACH LANE_MODE LANE_PIN_SHA \
           LANE_ARTIFACT_BANK LANE_RATE_LIMIT_REGEX LANE_RESULT_BEGIN LANE_RESULT_END \
           LANE_START_TIMEOUT_S LANE_LOCK_TIMEOUT_S LANE_QUOTA_RECEIPT \
           LANE_QUOTA_MAX_AGE_MIN LANE_ROSTER_CHECK LANE_USAGE_PARSER \
           LANE_LOOP_OWNER LANE_EXPECTED_END LANE_STOP_CMD; do
    eval "printf '%s=%s\n' \"$k\" \"\${$k:-}\""
  done
  say "start_receipt=$START_RECEIPT"
  say "exit_receipt=$EXIT_RECEIPT"
  say "cost_receipt=$COST_RECEIPT"
  say "log=$RUN_LOG"
  say "detach_method=$(detach_method)"
}

# ------------------------------------------------------------- detachment

detach_method() {
  case "$LANE_DETACH" in
    none) printf 'none';;
    setsid) command -v setsid >/dev/null 2>&1 && printf 'setsid' || printf 'unavailable';;
    python) command -v python3 >/dev/null 2>&1 && printf 'python' || printf 'unavailable';;
    perl) command -v perl >/dev/null 2>&1 && printf 'perl' || printf 'unavailable';;
    auto)
      if command -v setsid >/dev/null 2>&1; then printf 'setsid'
      elif command -v python3 >/dev/null 2>&1; then printf 'python'
      elif command -v perl >/dev/null 2>&1; then printf 'perl'
      else printf 'unavailable'; fi;;
    *) printf 'unavailable';;
  esac
}

# Spawn "$@" in a NEW SESSION (own process group) so the harness that called us
# can be torn down — SIGTERM/SIGHUP to its group — without taking the run with it.
spawn_detached() { # method cmd...
  local method="$1"; shift
  case "$method" in
    setsid) setsid "$@" < /dev/null > "$RUNNER_LOG" 2>&1 & ;;
    python) python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' "$@" \
              < /dev/null > "$RUNNER_LOG" 2>&1 & ;;
    perl)   perl -e 'use POSIX qw(setsid); setsid() or die "setsid: $!"; exec @ARGV or die "exec: $!"' "$@" \
              < /dev/null > "$RUNNER_LOG" 2>&1 & ;;
    none)   "$@" < /dev/null > "$RUNNER_LOG" 2>&1 & ;;
    *) die "no detach method available (LANE_DETACH=$LANE_DETACH); set LANE_DETACH=none to run in this session deliberately";;
  esac
  disown 2>/dev/null || true
}

# ------------------------------------------------------------- writer lock

lock_dir() { printf '%s/writer-lock.%s' "$LANE_RUN_DIR" "$(sha256_str "$LANE_WORKTREE" | cut -c1-16)"; }

acquire_writer_lock() { # returns 0 when held, 1 on timeout
  local dir waited=0 holder
  dir="$(lock_dir)"
  while :; do
    if mkdir "$dir" 2>/dev/null; then printf '%s\n' "$$" > "$dir/pid"; printf '%s\n' "$LANE_WORKTREE" > "$dir/worktree"; return 0; fi
    holder="$(cat "$dir/pid" 2>/dev/null || true)"
    if [ -n "$holder" ] && ! pid_alive "$holder"; then rm -rf "$dir"; continue; fi
    [ "$waited" -ge "$LANE_LOCK_TIMEOUT_S" ] && return 1
    sleep 1; waited=$((waited + 1))
  done
}
release_writer_lock() {
  local dir; dir="$(lock_dir)"
  [ "$(cat "$dir/pid" 2>/dev/null || true)" = "$$" ] && rm -rf "$dir"
  return 0
}

quota_preflight() {
  local checked verdict age now
  checked="$(receipt_get "$LANE_QUOTA_RECEIPT" checked_epoch)"
  verdict="$(receipt_get "$LANE_QUOTA_RECEIPT" verdict)"
  case "$checked" in ''|*[!0-9]*) return 1;; esac
  [ "$verdict" = go ] || return 1
  now="$(now_epoch)"
  [ "$checked" -le "$now" ] || return 1
  age=$((now - checked))
  [ "$age" -le $((LANE_QUOTA_MAX_AGE_MIN * 60)) ]
}

roster_preflight() {
  "$LANE_ROSTER_CHECK" "$LANE_BRIEF" "$@" >/dev/null 2>&1
}

# ------------------------------------------------------------- deliverable

# validate_report <path> <lane> <run_id> <started_at_epoch>
# prints one of: valid <status> | missing | unbound | stale | invalid
validate_report() {
  local path="$1" lane="$2" run_id="$3" started="$4" status
  [ -s "$path" ] || { printf 'missing'; return; }
  if ! grep -Eq "^run_id: $run_id[[:space:]]*$" "$path"; then printf 'unbound'; return; fi
  if [ -n "$started" ] && [ "$(mtime_epoch "$path")" -lt "$started" ]; then printf 'stale'; return; fi
  grep -Eq "^lane: $lane[[:space:]]*$" "$path" || { printf 'invalid'; return; }
  status="$(grep -E "$STATUSES_RE" "$path" | head -n 1 | sed 's/^status:[[:space:]]*//; s/[[:space:]]*$//')"
  [ -n "$status" ] || { printf 'invalid'; return; }
  printf 'valid %s' "$status"
}

# read-only runs: the CLI cannot write the report; extract it from stdout between
# the documented markers (first BEGIN … first END after it). Exit 0 without an
# extracted report is not a deliverable.
extract_stdout_report() { # log result_path -> 0 when extracted
  local begin="$LANE_RESULT_BEGIN" end="$LANE_RESULT_END"
  awk -v b="$begin" -v e="$end" '
    $0 == b && !on { on = 1; next }
    $0 == e && on { found = 1; exit }
    on { print }
    END { exit found ? 0 : 1 }' "$1" > "$2.tmp" || { rm -f "$2.tmp"; return 1; }
  mv "$2.tmp" "$2"
}

bank_receipts() { # -> prints bank path or nothing
  [ -n "$LANE_ARTIFACT_BANK" ] || return 0
  local dest="$LANE_ARTIFACT_BANK/$LANE/$LANE_RUN_ID" f
  mkdir -p "$dest" || return 0
  for f in "$START_RECEIPT" "$RUN_LOG" "$LANE_RESULT_PATH" "$COST_RECEIPT" "$EXIT_RECEIPT.tmp"; do
    [ -f "$f" ] && cp "$f" "$dest/$(basename "$f" .tmp)"
  done
  printf '%s' "$dest"
}

# ------------------------------------------------------------- the runner

# `_run` executes in its own session. It owns: delay → quota → roster → writer lock → pin check →
# CLI start with stdin closed → identity check → wait → validation → banking →
# exit receipt (written atomically, LAST).
CLI_PID=""
LOOP_REGISTRY="$(cd "$(dirname "$SELF")" && pwd)/loop_registry.sh"

write_cost_receipt() {
  local tmp="$COST_RECEIPT.tmp" parsed="$COST_RECEIPT.parser.tmp" started ended elapsed key value
  rm -f "$tmp" "$parsed"
  started="$(receipt_get "$START_RECEIPT" started_epoch)"; ended="$(now_epoch)"
  case "$started" in ''|*[!0-9]*) elapsed=unknown;; *) elapsed=$((ended - started));; esac
  receipt_set "$tmp" tokens_in unknown
  receipt_set "$tmp" tokens_out unknown
  receipt_set "$tmp" cached_tokens unknown
  receipt_set "$tmp" requests unknown
  receipt_set "$tmp" model unknown
  receipt_set "$tmp" effort unknown
  receipt_set "$tmp" wall_s "$elapsed"
  receipt_set "$tmp" source unavailable
  if [ -n "$LANE_USAGE_PARSER" ] && "$LANE_USAGE_PARSER" "$RUN_LOG" > "$parsed" 2>/dev/null; then
    while IFS='=' read -r key value; do
      case "$key" in
        tokens_in|tokens_out|cached_tokens|requests|model|effort|wall_s|source)
          [ -n "$value" ] && receipt_set "$tmp" "$key" "$value"
          ;;
      esac
    done < "$parsed"
  fi
  rm -f "$parsed"
  mv "$tmp" "$COST_RECEIPT"
}

loop_done() {
  [ -x "$LOOP_REGISTRY" ] || return 0
  LOOP_REGISTRY_FILE="$LANE_SENTINEL_DIR/loops.tsv" "$LOOP_REGISTRY" done "$LANE.$LANE_RUN_ID" >/dev/null 2>&1 || true
}

write_exit_receipt() { # code
  local tmp="$EXIT_RECEIPT.tmp" code="$1" verdict status rl="no" bank
  receipt_set "$tmp" run_id "$LANE_RUN_ID"
  receipt_set "$tmp" lane "$LANE"
  receipt_set "$tmp" ended_at "$(now_iso)"
  receipt_set "$tmp" ended_epoch "$(now_epoch)"
  write_cost_receipt
  if [ "$LANE_MODE" = read-only ]; then
    if extract_stdout_report "$RUN_LOG" "$LANE_RESULT_PATH"; then receipt_set "$tmp" stdout_extract extracted
    else receipt_set "$tmp" stdout_extract none; fi
  fi
  verdict="$(validate_report "$LANE_RESULT_PATH" "$LANE" "$LANE_RUN_ID" "$(receipt_get "$START_RECEIPT" started_epoch)")"
  status="${verdict#valid }"; [ "$status" = "$verdict" ] && status=""
  receipt_set "$tmp" deliverable "${verdict%% *}"
  [ -n "$status" ] && receipt_set "$tmp" report_status "$status"
  case "$code" in
    0) ;;
    *) grep -Eq "$LANE_RATE_LIMIT_REGEX" "$RUN_LOG" 2>/dev/null && rl="yes";;
  esac
  receipt_set "$tmp" rate_limited "$rl"
  receipt_set "$tmp" result_path "$LANE_RESULT_PATH"
  receipt_set "$tmp" log "$RUN_LOG"
  bank="$(bank_receipts)"; [ -n "$bank" ] && receipt_set "$tmp" bank_path "$bank"
  receipt_set "$tmp" LANE_EXIT "$code"
  mv "$tmp" "$EXIT_RECEIPT"
  loop_done
  [ -n "$bank" ] && cp "$EXIT_RECEIPT" "$bank/" 2>/dev/null
  return 0
}
runner_signal() { # name
  [ -n "$CLI_PID" ] && kill -TERM "$CLI_PID" 2>/dev/null
  release_writer_lock
  [ -f "$EXIT_RECEIPT" ] || write_exit_receipt "signal:$1"
  exit 128
}
runner_refuse() { # reason
  receipt_set "$START_RECEIPT" state refused
  receipt_set "$START_RECEIPT" refused_reason "$1"
  loop_done
  release_writer_lock
  exit 4
}

cmd_run() {
  resolve_contract start
  trap 'runner_signal TERM' TERM
  trap 'runner_signal HUP' HUP
  trap 'runner_signal INT' INT
  receipt_set "$START_RECEIPT" runner_pid "$$"
  receipt_set "$START_RECEIPT" runner_pgid "$(ps -o pgid= -p $$ | tr -d ' ')"
  [ -x "$LOOP_REGISTRY" ] || runner_refuse "loop-registry-missing: $LOOP_REGISTRY"
  local stop_cmd="${LANE_STOP_CMD:-kill $$}"
  LOOP_REGISTRY_FILE="$LANE_SENTINEL_DIR/loops.tsv" "$LOOP_REGISTRY" add \
    "$LANE.$LANE_RUN_ID" lane "$LANE_LOOP_OWNER" "$LANE_EXPECTED_END" "$stop_cmd" "exit_file:$EXIT_RECEIPT" \
    || runner_refuse "loop-registry-refused"

  if [ "$LANE_DELAY_S" -gt 0 ]; then
    receipt_set "$START_RECEIPT" state delayed
    receipt_set "$START_RECEIPT" delayed_until_epoch "$(( $(now_epoch) + LANE_DELAY_S ))"
    sleep "$LANE_DELAY_S"
  fi

  quota_preflight || runner_refuse "quota-canary-stale-or-not-go: $LANE_QUOTA_RECEIPT"
  roster_preflight "$@" || runner_refuse "roster-binding-rejected: $LANE_ROSTER_CHECK"

  # A delayed start must never run beside a commit in the same tree: the
  # wrapper's commit holds this lock (`with-writer-lock`), and so do we.
  acquire_writer_lock || runner_refuse "writer-lock-timeout"
  receipt_set "$START_RECEIPT" writer_lock "$(lock_dir)"

  if [ -n "$LANE_PIN_SHA" ]; then
    local head
    head="$(git -C "$LANE_WORKTREE" rev-parse HEAD 2>/dev/null || printf 'not-a-git-tree')"
    receipt_set "$START_RECEIPT" head_at_start "$head"
    case "$head" in "$LANE_PIN_SHA"*) ;; *) runner_refuse "head-moved: pinned $LANE_PIN_SHA, found $head";; esac
  else
    receipt_set "$START_RECEIPT" head_at_start "$(git -C "$LANE_WORKTREE" rev-parse HEAD 2>/dev/null || printf 'not-a-git-tree')"
  fi

  # argv placeholders
  local brief argv=() a
  brief="$(cat "$LANE_BRIEF")"
  for a in "$@"; do
    a="${a//\{brief_path\}/$LANE_BRIEF}"
    a="${a//\{worktree\}/$LANE_WORKTREE}"
    a="${a//\{lane\}/$LANE}"
    a="${a//\{run_id\}/$LANE_RUN_ID}"
    a="${a//\{result_path\}/$LANE_RESULT_PATH}"
    a="${a//\{brief\}/$brief}"
    argv+=("$a")
  done

  # stdin MUST be closed — an open stdin makes some CLIs wait forever.
  ( cd "$LANE_WORKTREE" && exec "${argv[@]}" ) < /dev/null > "$RUN_LOG" 2>&1 &
  CLI_PID=$!
  local cli_name; cli_name="$(basename "${argv[0]}")"
  receipt_set "$START_RECEIPT" cli_pid "$CLI_PID"
  receipt_set "$START_RECEIPT" started_at "$(now_iso)"
  receipt_set "$START_RECEIPT" started_epoch "$(now_epoch)"
  # identity: the pid we started must present the executable we asked for
  # (a subshell that is still exec-ing is tolerated for a short grace period).
  local tries=0 comm=""
  while [ "$tries" -lt 20 ]; do
    comm="$(basename "$(pid_comm "$CLI_PID")" 2>/dev/null || true)"
    [ "$comm" = "$cli_name" ] && break
    pid_alive "$CLI_PID" || break
    sleep 0.1; tries=$((tries + 1))
  done
  receipt_set "$START_RECEIPT" cli_comm_observed "${comm:-none}"
  receipt_set "$START_RECEIPT" state started

  wait "$CLI_PID"; local code=$?
  CLI_PID=""
  release_writer_lock
  write_exit_receipt "$code"
}

# ------------------------------------------------------------- start

cmd_start() {
  [ "${1:-}" = "--" ] || die "usage: start -- <cli> [args...] (the CLI argv follows --)"
  shift
  [ "$#" -ge 1 ] || die "no CLI argv after --"
  resolve_contract start
  [ -e "$START_RECEIPT" ] && die "run id already used: $START_RECEIPT exists (a run id is single-use)"
  local method; method="$(detach_method)"
  [ "$method" != unavailable ] && [ "$method" != "" ] || die "no detach method available (LANE_DETACH=$LANE_DETACH); install setsid/python3/perl or set LANE_DETACH=none deliberately"

  receipt_set "$START_RECEIPT" run_id "$LANE_RUN_ID"
  receipt_set "$START_RECEIPT" lane "$LANE"
  receipt_set "$START_RECEIPT" worktree "$LANE_WORKTREE"
  receipt_set "$START_RECEIPT" brief "$LANE_BRIEF"
  receipt_set "$START_RECEIPT" brief_sha256 "$(sha256_file "$LANE_BRIEF")"
  receipt_set "$START_RECEIPT" cli_name "$(basename "$1")"
  receipt_set "$START_RECEIPT" cli_argc "$#"
  receipt_set "$START_RECEIPT" mode "$LANE_MODE"
  receipt_set "$START_RECEIPT" delay_s "$LANE_DELAY_S"
  receipt_set "$START_RECEIPT" detach "$method"
  receipt_set "$START_RECEIPT" pin_sha "${LANE_PIN_SHA:-none}"
  receipt_set "$START_RECEIPT" quota_receipt "$LANE_QUOTA_RECEIPT"
  receipt_set "$START_RECEIPT" quota_max_age_min "$LANE_QUOTA_MAX_AGE_MIN"
  receipt_set "$START_RECEIPT" roster_check "$LANE_ROSTER_CHECK"
  receipt_set "$START_RECEIPT" result_path "$LANE_RESULT_PATH"
  receipt_set "$START_RECEIPT" sentinel_dir "$LANE_SENTINEL_DIR"
  receipt_set "$START_RECEIPT" dispatched_at "$(now_iso)"
  receipt_set "$START_RECEIPT" dispatcher_pid "$$"
  receipt_set "$START_RECEIPT" state dispatched

  spawn_detached "$method" "$SELF" _run "$@"

  # Block until the run has checked in: started, delayed, refused, or exited.
  local waited=0 state
  while :; do
    state="$(receipt_get "$START_RECEIPT" state)"
    case "$state" in
      started|delayed) break;;
      refused) say "state=refused"; say "refused_reason=$(receipt_get "$START_RECEIPT" refused_reason)"; say "start_receipt=$START_RECEIPT"; return 4;;
    esac
    [ -f "$EXIT_RECEIPT" ] && break
    if [ "$waited" -ge $((LANE_START_TIMEOUT_S * 10)) ]; then
      say "state=timeout"; say "start_receipt=$START_RECEIPT"; say "runner_log=$RUNNER_LOG"; return 3
    fi
    sleep 0.1; waited=$((waited + 1))
  done
  say "run_id=$LANE_RUN_ID"
  say "state=$(receipt_get "$START_RECEIPT" state)"
  say "runner_pid=$(receipt_get "$START_RECEIPT" runner_pid)"
  say "cli_pid=$(receipt_get "$START_RECEIPT" cli_pid)"
  say "detach=$method"
  say "start_receipt=$START_RECEIPT"
  say "log=$RUN_LOG"
  say "exit_receipt=$EXIT_RECEIPT"
  say "cost_receipt=$COST_RECEIPT"
  say "result_path=$LANE_RESULT_PATH"
  return 0
}

# ------------------------------------------------------------- wait / verdict

cmd_wait() {
  resolve_contract wait
  local timeout="${1:-600}" waited=0 runner
  while [ ! -f "$EXIT_RECEIPT" ]; do
    if [ "$waited" -ge $((timeout * 5)) ]; then say "wait=timeout"; return 1; fi
    runner="$(receipt_get "$START_RECEIPT" runner_pid)"
    if [ -f "$START_RECEIPT" ] && [ -n "$runner" ] && ! pid_alive "$runner"; then
      sleep 0.5; [ -f "$EXIT_RECEIPT" ] && break
      say "wait=vanished"; return 1
    fi
    sleep 0.2; waited=$((waited + 1))
  done
  say "exit_receipt=$EXIT_RECEIPT"
  say "LANE_EXIT=$(receipt_get "$EXIT_RECEIPT" LANE_EXIT)"
  return 0
}

cmd_verdict() {
  resolve_contract verdict
  local state code deliverable status rl cli_pid runner_pid cli_name started verdict rc
  say "run_id=$LANE_RUN_ID"
  say "lane=$LANE"
  if [ ! -f "$START_RECEIPT" ]; then say "verdict=not-started"; say "start_receipt=missing $START_RECEIPT"; return 12; fi
  state="$(receipt_get "$START_RECEIPT" state)"
  if [ "$state" = refused ]; then say "verdict=refused-start"; say "refused_reason=$(receipt_get "$START_RECEIPT" refused_reason)"; return 14; fi
  if [ ! -f "$EXIT_RECEIPT" ]; then
    cli_pid="$(receipt_get "$START_RECEIPT" cli_pid)"; runner_pid="$(receipt_get "$START_RECEIPT" runner_pid)"
    cli_name="$(receipt_get "$START_RECEIPT" cli_name)"
    if [ "$state" = delayed ]; then
      if [ -n "$runner_pid" ] && pid_alive "$runner_pid"; then say "verdict=delayed"; say "delayed_until_epoch=$(receipt_get "$START_RECEIPT" delayed_until_epoch)"; return 11; fi
      say "verdict=vanished"; say "detail=runner $runner_pid died during delay"; return 13
    fi
    if [ -n "$cli_pid" ] && pid_alive "$cli_pid" && [ "$(basename "$(pid_comm "$cli_pid")")" = "$cli_name" ]; then
      say "verdict=running"; say "cli_pid=$cli_pid"; return 10
    fi
    if [ -n "$runner_pid" ] && pid_alive "$runner_pid"; then say "verdict=running"; say "detail=runner $runner_pid alive, CLI exited or not yet started"; return 10; fi
    say "verdict=vanished"; say "detail=no exit receipt and no live process for this run"; return 13
  fi
  code="$(receipt_get "$EXIT_RECEIPT" LANE_EXIT)"
  rl="$(receipt_get "$EXIT_RECEIPT" rate_limited)"
  started="$(receipt_get "$START_RECEIPT" started_epoch)"
  # Re-validate the report NOW against THIS run — the exit receipt's verdict is
  # not trusted blindly, and no other run's report can satisfy this run_id.
  deliverable="$(validate_report "$LANE_RESULT_PATH" "$LANE" "$LANE_RUN_ID" "$started")"
  status="${deliverable#valid }"; [ "$status" = "$deliverable" ] && status=""
  deliverable="${deliverable%% *}"
  say "LANE_EXIT=$code"
  say "deliverable=$deliverable"
  [ -n "$status" ] && say "report_status=$status"
  say "rate_limited=${rl:-no}"
  say "result_path=$LANE_RESULT_PATH"
  say "log=$RUN_LOG"
  [ -n "$(receipt_get "$EXIT_RECEIPT" bank_path)" ] && say "bank_path=$(receipt_get "$EXIT_RECEIPT" bank_path)"
  case "$code" in
    0)
      case "$deliverable" in
        valid) say "verdict=$status"; return 0;;
        missing) say "verdict=no-deliverable"; return 21;;
        unbound|stale) say "verdict=$deliverable-report"; return 22;;
        *) say "verdict=invalid-report"; return 23;;
      esac;;
    *) say "verdict=died"; return 20;;
  esac
}

# ------------------------------------------------------------- running / lock

cmd_running() { # cli-name token
  [ $# -eq 2 ] || die "usage: running <cli-name> <exec-token>"
  local name="$1" tok="$2" pid found=0 line
  # cheap prefilter on args, then the authoritative per-pid identity check
  ps -axww -o pid=,args= | while read -r pid line; do
    case " $line " in *" $tok "*) ;; *) continue;; esac
    [ "$pid" = "$$" ] && continue
    if is_lane_process "$pid" "$name" "$tok"; then printf '%s %s\n' "$pid" "$(pid_comm "$pid")"; fi
  done | sort -u | tee "$LANE_RUN_DIR/.running.$$"
  found="$(wc -l < "$LANE_RUN_DIR/.running.$$" | tr -d ' ')"; rm -f "$LANE_RUN_DIR/.running.$$"
  [ "$found" -gt 0 ]
}

cmd_with_writer_lock() {
  [ "${1:-}" = "--" ] || die "usage: with-writer-lock -- <cmd...>"
  shift; [ $# -ge 1 ] || die "no command after --"
  resolve_contract lock
  acquire_writer_lock || die "writer lock timeout for $LANE_WORKTREE"
  trap 'release_writer_lock' EXIT
  "$@"; local rc=$?
  release_writer_lock; trap - EXIT
  return $rc
}

# ------------------------------------------------------------- dispatch

case "${1:-}" in
  start) shift; cmd_start "$@";;
  _run) shift; cmd_run "$@";;
  wait) shift; cmd_wait "$@";;
  verdict) shift; cmd_verdict "$@";;
  running) shift; LANE="${LANE:-x}"; LANE_RUN_DIR="${LANE_RUN_DIR:-${TMPDIR:-/tmp}}"; cmd_running "$@";;
  with-writer-lock) shift; cmd_with_writer_lock "$@";;
  env) shift; resolve_contract env; print_env;;
  ""|-h|--help) sed -n '2,40p' "$SELF"; exit 0;;
  *) die "unknown subcommand '$1' (start|wait|verdict|running|with-writer-lock|env)";;
esac
