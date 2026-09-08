#!/usr/bin/env bash
# Proves parser-provided usage and the explicit unavailable fallback in lane cost receipts.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
LAUNCHER="$HERE/../launch_lane.sh"
PARSER="$HERE/../adapters/codex_usage.py"
T="$(mktemp -d "${TMPDIR:-/tmp}/cost receipt test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/run" "$T/wt" "$T/bin"
ln -s /bin/sh "$T/bin/fakecli"
printf 'brief\n' > "$T/brief.md"
printf 'checked_epoch=%s\nverdict=go\n' "$(date +%s)" > "$T/quota.receipt"
printf '%s\n' '#!/bin/sh' 'exit 0' > "$T/roster-check.sh"
chmod +x "$T/roster-check.sh"

printf '%s\n' '#!/bin/sh' 'printf "lane: %s\nrun_id: %s\nstatus: built\n" "$LANE" "$LANE_RUN_ID" > "$LANE_RESULT_PATH"' > "$T/body.sh"
printf '%s\n' '#!/bin/sh' 'printf "%s\n" "tokens_in=120" "tokens_out=30" "cached_tokens=40" "requests=2" "model=test-model" "effort=high" "wall_s=7" "source=test-adapter"' > "$T/usage parser.sh"
chmod +x "$T/usage parser.sh"

run_lane() {
  if [ -n "$2" ]; then
    env LANE=cost LANE_RUN_ID="$1" LANE_WORKTREE="$T/wt" LANE_RUN_DIR="$T/run" LANE_BRIEF="$T/brief.md" LANE_DETACH=none LANE_SENTINEL_DIR="$T/run" LANE_RESULT_PATH="$T/run/cost.$1.result.md" LANE_QUOTA_RECEIPT="$T/quota.receipt" LANE_ROSTER_CHECK="$T/roster-check.sh" LANE_USAGE_PARSER="$2" \
      "$LAUNCHER" start -- "$T/bin/fakecli" "$T/body.sh" exec >/dev/null
  else
    env LANE=cost LANE_RUN_ID="$1" LANE_WORKTREE="$T/wt" LANE_RUN_DIR="$T/run" LANE_BRIEF="$T/brief.md" LANE_DETACH=none LANE_SENTINEL_DIR="$T/run" LANE_RESULT_PATH="$T/run/cost.$1.result.md" LANE_QUOTA_RECEIPT="$T/quota.receipt" LANE_ROSTER_CHECK="$T/roster-check.sh" \
      "$LAUNCHER" start -- "$T/bin/fakecli" "$T/body.sh" exec >/dev/null
  fi
  LANE=cost LANE_RUN_ID="$1" LANE_RUN_DIR="$T/run" LANE_SENTINEL_DIR="$T/run" LANE_RESULT_PATH="$T/run/cost.$1.result.md" "$LAUNCHER" wait 10 >/dev/null
}
rget() { grep "^$2=" "$1" | tail -n 1 | cut -d= -f2-; }

run_lane parsed "$T/usage parser.sh"
C="$T/run/cost.parsed.cost"
[ "$(rget "$C" tokens_in)" = 120 ] && [ "$(rget "$C" tokens_out)" = 30 ] && [ "$(rget "$C" cached_tokens)" = 40 ] && [ "$(rget "$C" requests)" = 2 ] && [ "$(rget "$C" source)" = test-adapter ] || { echo 'not ok - parser values'; cat "$C"; exit 1; }

run_lane unavailable ''
C="$T/run/cost.unavailable.cost"
[ "$(rget "$C" source)" = unavailable ] || { echo 'not ok - unavailable source absent'; cat "$C"; exit 1; }
for key in tokens_in tokens_out cached_tokens requests model effort wall_s source; do grep -q "^$key=" "$C" || { echo "not ok - missing $key"; exit 1; }; done
[ "$(rget "$C" tokens_in)" = unknown ] || { echo 'not ok - unknown was collapsed to zero'; exit 1; }
case "$(rget "$C" wall_s)" in ''|*[!0-9]*) echo 'not ok - launcher wall time is not numeric'; exit 1;; esac
grep -q $'^cost.parsed\t.*\tfinished$' "$T/run/loops.tsv" && grep -q $'^cost.unavailable\t.*\tfinished$' "$T/run/loops.tsv" || { echo 'not ok - launcher did not register and finish both lane loops'; cat "$T/run/loops.tsv"; exit 1; }

printf '%s\n' '{"type":"thread.started","thread_id":"t1"}' '{"type":"turn.completed","usage":{"input_tokens":100,"cached_input_tokens":25,"output_tokens":10},"model":"codex-model","effort":"high"}' '{"type":"turn.completed","usage":{"input_tokens":20,"cached_input_tokens":5,"output_tokens":2}}' > "$T/codex.jsonl"
parsed="$(python3 "$PARSER" "$T/codex.jsonl")"
printf '%s\n' "$parsed" | grep -q '^tokens_in=120$' && printf '%s\n' "$parsed" | grep -q '^tokens_out=12$' && printf '%s\n' "$parsed" | grep -q '^cached_tokens=30$' && printf '%s\n' "$parsed" | grep -q '^requests=2$' || { echo 'not ok - codex JSON aggregation'; echo "$parsed"; exit 1; }
printf 'tokens used\n1,234\n' > "$T/codex.txt"
plain="$(python3 "$PARSER" "$T/codex.txt")"
printf '%s\n' "$plain" | grep -q '^requests=1$' && printf '%s\n' "$plain" | grep -q '^source=codex_usage.py$' || { echo 'not ok - Codex plain tokens-used fallback'; echo "$plain"; exit 1; }

echo 'cost-receipt: parser numbers, unavailable/unknown distinction, Codex JSON/plain fallback and lane loop completion ok'
