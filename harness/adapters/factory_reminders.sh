#!/bin/sh
# factory_reminders.sh — text-only reminders, no network, silent unless matched.
#
# This script owns exactly the two legs whose PLAIN STDOUT reaches the model
# (harness/guards.md §2): SessionStart — including the `compact` matcher, which fires
# right after a compaction — and UserPromptSubmit. Every other reminder lives in the
# dispatcher (harness/guards/guard_dispatch.py) as hookSpecificOutput.additionalContext,
# because plain stdout on PostToolUse, Stop and PreCompact never reaches the model (§10).
#
#   factory_reminders.sh session-start | compact | prompt
#
# Parameters (guards.md §8), all optional: FACTORY_GUARD_STATE_DIR, FACTORY_GUARD_DIR,
# FACTORY_GUARD_CLI, FACTORY_GUARD_CLI_TOKEN, FACTORY_GUARD_CLI_DIR_FLAG,
# FACTORY_GUARD_DATA_VOLUME, FACTORY_GUARD_PORT_RANGE, FACTORY_GUARD_DISK_FLOOR_GB.

INPUT=$(cat 2>/dev/null || true)
HERE=$(cd "$(dirname "$0")" && pwd -P)
GUARDS_DIR="${FACTORY_GUARD_DIR:-$HERE/../guards}"

# The state directory is ONE place per repository: .factory-guard/ in the PRIMARY checkout
# (the parent of `git rev-parse --git-common-dir`) — derived exactly as the dispatcher's
# state_dir_from does, so a session started in a linked worktree, the hooks and the git
# hooks read the same allow file and the same landing state.
factory_primary() {
  root="${CLAUDE_PROJECT_DIR:-.}"
  common=$(git -C "$root" rev-parse --git-common-dir 2>/dev/null)
  case "$common" in
    "") printf '%s\n' "$root" ;;
    /*) dirname "$common" ;;
    *) (cd "$root/$(dirname "$common")" 2>/dev/null && pwd -P) || printf '%s\n' "$root" ;;
  esac
}
STATE_DIR="${FACTORY_GUARD_STATE_DIR:-$(factory_primary)/.factory-guard}"

# The mounted rules: every rule module in the package (file stem, `_` → `-`).
mounted_rules() {
  for f in "$GUARDS_DIR"/rules/*.py; do
    [ -f "$f" ] || continue
    name=$(basename "$f" .py)
    case "$name" in _*) continue ;; esac
    printf '%s ' "$name" | tr '_' '-'
  done
}

# Live lanes by process IDENTITY (harness/run-lifecycle.md §6), the launcher's own method:
# a cheap prefilter of `ps -axww -o pid=,args=` on the exact $FACTORY_GUARD_CLI_TOKEN, then
# the authoritative per-pid `ps -o comm= -p <pid>` (a multi-column comm is truncated on
# macOS) whose basename must equal $FACTORY_GUARD_CLI — never a full-command text match,
# which also selects the inspecting shell. The lane name is the basename of the
# $FACTORY_GUARD_CLI_DIR_FLAG operand. Empty when the CLI variables are unbound. ps joins
# argv with spaces: an operand containing a space is read up to its first space (§13).
live_lanes() {
  [ -n "${FACTORY_GUARD_CLI:-}" ] && [ -n "${FACTORY_GUARD_CLI_TOKEN:-}" ] || return 0
  ps -axww -o pid=,args= 2>/dev/null | while read -r pid line; do
    case " $line " in *" $FACTORY_GUARD_CLI_TOKEN "*) ;; *) continue ;; esac
    [ "$pid" = "$$" ] && continue
    comm=$(ps -o comm= -p "$pid" 2>/dev/null | sed 's/^[[:space:]]*//')
    [ "$(basename "$comm")" = "$FACTORY_GUARD_CLI" ] || continue
    printf '%s\n' "$line" | awk -v tok="$FACTORY_GUARD_CLI_TOKEN" -v flag="${FACTORY_GUARD_CLI_DIR_FLAG:-}" '
      {
        hit = 0; for (i = 2; i <= NF; i++) if ($i == tok) { hit = 1; break }
        if (!hit || flag == "") exit
        for (i = 2; i <= NF; i++) {
          if ($i == flag && i < NF) { print $(i + 1); exit }
          if (index($i, flag "=") == 1) { print substr($i, length(flag) + 2); exit }
        }
      }'
  done | while IFS= read -r dir; do basename "$dir"; done | sort -u | tr '\n' ' '
}

# One line of footprint at session start: free space on the data volume and the listeners
# in the project's port range. Printed only when both parameters are bound.
disk_line() {
  [ -n "${FACTORY_GUARD_DATA_VOLUME:-}" ] && [ -n "${FACTORY_GUARD_PORT_RANGE:-}" ] || return 0
  VOL="$FACTORY_GUARD_DATA_VOLUME"
  [ -d "$VOL" ] || VOL="${CLAUDE_PROJECT_DIR:-.}"
  FREE=$(df -k "$VOL" 2>/dev/null | awk 'NR==2 { printf "%.1f", $4 / 1048576 }')
  LISTENERS=$(lsof -nP -iTCP:"$FACTORY_GUARD_PORT_RANGE" -sTCP:LISTEN 2>/dev/null | awk 'NR > 1' | wc -l | tr -d ' ')
  FLOOR="${FACTORY_GUARD_DISK_FLOOR_GB:+ (floor $FACTORY_GUARD_DISK_FLOOR_GB GB, disk guard)}"
  [ -n "$FREE" ] && printf 'DISK: %s GB free on %s%s · %s listener(s) in TCP %s (tear down by port: lsof -ti :<port>)\n' "$FREE" "$VOL" "$FLOOR" "${LISTENERS:-0}" "$FACTORY_GUARD_PORT_RANGE"
}

case "${1:-}" in
  session-start)
    printf 'FACTORY GUARDS (harness/guards.md): rules %smounted through harness/adapters/factory_guard.py. Switch per rule: prefix the command with FACTORY_GUARD_ALLOW=<id> (logged; ledgered as an O-entry); FACTORY_GUARD_DISABLED=1 only while the apparatus is down.\n' "$(mounted_rules)"
    # The §8 bindings as the hook process sees them — an unbound parameter is visible here,
    # never silent (guards.md §8 names how a binding reaches the hook process).
    printf 'GUARD BINDINGS: cli=%s token=%s dir-flag=%s gates=%s port-range=%s (unbound = the identity refusal prints placeholders, the live-lane legs list nothing, verdict gates only its default table)\n' \
      "${FACTORY_GUARD_CLI:-unbound}" "${FACTORY_GUARD_CLI_TOKEN:-unbound}" "${FACTORY_GUARD_CLI_DIR_FLAG:-unbound}" "${FACTORY_GUARD_GATES:-unbound}" "${FACTORY_GUARD_PORT_RANGE:-unbound}"
    [ "${FACTORY_GUARD_DISABLED:-0}" = "1" ] && printf '%s\n' "WARNING: FACTORY_GUARD_DISABLED=1 — every factory guard is off in this session."
    PROTECTIONS="${FACTORY_PROTECTIONS_DIR:-$HERE/../../verification/protections}"
    # The git hooks (verification/protections.md §1, M-10) exist only once core.hooksPath points
    # at the tracked shims — one command in the primary, every worktree.
    HOOKS_PATH=$(git -C "${CLAUDE_PROJECT_DIR:-.}" config --get core.hooksPath 2>/dev/null)
    [ -n "$HOOKS_PATH" ] || printf 'GIT HOOKS: core.hooksPath is not set — run python3 %s/git_hooks.py install once in the primary (verification/protections.md §1; the identity, trailer and landing checks then hold in every session and terminal).\n' "$PROTECTIONS"
    if [ -f "$STATE_DIR/landing-in-progress.json" ]; then
      TRAIN=$(sed -nE 's/.*"train": *"([^"]+)".*/\1/p' "$STATE_DIR/landing-in-progress.json" | head -1)
      MODE=$(sed -nE 's/.*"mode": *"([^"]+)".*/\1/p' "$STATE_DIR/landing-in-progress.json" | head -1)
      printf 'LANDING IN PROGRESS: train %s is registered on the default branch (%s mode) — lander duties are open (verification/lander-duties.md §8; python3 -m scripts.check_landing_closeout --state %s prints them). Delete %s when they are closed.\n' "${TRAIN:-?}" "${MODE:-?}" "$STATE_DIR/landing-in-progress.json" "$STATE_DIR/landing-in-progress.json"
    fi
    disk_line
    # CI signal (guards.md §9, CI row; verification/protections.md §4): the protections chapter
    # ships ci_signal.sh; this script calls it when executable, absent = silent.
    [ -x "$PROTECTIONS/ci_signal.sh" ] && "$PROTECTIONS/ci_signal.sh"
    ;;

  compact)
    # SessionStart with matcher `compact`: what must survive a compaction.
    LANES=$(live_lanes)
    printf '%s\n' \
      "AFTER COMPACTION, KEEP: (1) the board transaction points (planning/board-protocol.md); (2) the open lander duties (verification/lander-duties.md §1); (3) briefs are dispatched from the standing template, never re-authored by hand; (4) live lanes: ${LANES:-none}; (5) every guard denial and every switch use in this session goes into the train's choices ledger (O-entries)."
    ;;

  prompt)
    # One quiet line of live running-state; silent when nothing runs.
    LANES=$(live_lanes)
    [ -n "$LANES" ] && printf 'LIVE LANES: %s— read the verdict before touching a handback (harness/run-lifecycle.md §5).\n' "$LANES"
    ;;
esac
exit 0
