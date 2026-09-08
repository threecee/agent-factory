#!/usr/bin/env bash
# Falsifies the guard event-log report against every named pattern and its loop detector.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
REPORT="$HERE/../guard_report.py"
T="$(mktemp -d "${TMPDIR:-/tmp}/guard report test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
LOG="$T/events.log"

row() { printf '%s\t%s\tPreToolUse\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" >> "$LOG"; }
row 2026-09-08T10:00:00Z wanted deny verdict 'GUARD verdict: gate output piped to tail'
row 2026-09-08T10:01:00Z wanted deny verdict 'GUARD verdict: gate then git push'
# forbidden form fixture
row 2026-09-08T10:02:00Z wanted deny identity 'GUARD identity: pgrep -f selects itself before kill'
row 2026-09-08T10:03:00Z wanted deny quota 'GUARD quota: quota canary is stale'
row 2026-09-08T10:04:00Z wanted deny ritual 'GUARD ritual: raw codex exec outside launch_lane'
row 2026-09-08T10:05:00Z wanted deny dispatch 'GUARD dispatch: missing justification'
row 2026-09-08T10:06:00Z wanted deny idle 'GUARD idle: machine is not idle'
row 2026-09-08T10:07:00Z wanted deny built-bundle 'GUARD built-bundle: stale build'
row 2026-09-08T10:08:00Z wanted deny board 'GUARD board: board item unverified'
row 2026-09-08T10:09:00Z wanted deny bulk-read 'GUARD bulk-read: unbounded read'
row 2026-09-08T10:10:00Z wanted allow-switch verdict 'prefix:FACTORY_GUARD_ALLOW=verdict'
row 2026-09-08T10:11:00Z wanted deny closeout 'GUARD closeout: repeated unchanged refusal'
row 2026-09-08T10:15:00Z wanted deny closeout 'GUARD closeout: repeated unchanged refusal'
row 2026-09-08T10:19:00Z wanted deny closeout 'GUARD closeout: repeated unchanged refusal'
row 2026-09-08T10:19:30Z other deny verdict 'GUARD verdict: gate output piped to tail'

out="$(python3 "$REPORT" --session wanted --log "$LOG")" || exit $?
names='verdict-pipe gate-plus-push self-matching-kill stale-canary raw-cli-outside-launcher no-justification idle-violation stale-build board-unverified unbounded-read looping-denial'
for name in $names; do
  [ "$(printf '%s\n' "$out" | grep -c "^| $name |")" -eq 1 ] || { echo "not ok - $name not rendered exactly once"; exit 1; }
done
printf '%s\n' "$out" | grep -q '^| closeout | 3 |' || { echo 'not ok - denials grouped by rule'; exit 1; }
printf '%s\n' "$out" | grep -q 'prefix:FACTORY_GUARD_ALLOW=verdict' || { echo 'not ok - switch trace missing'; exit 1; }

json="$(python3 "$REPORT" --session wanted --log "$LOG" --json)" || exit $?
python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["session"]=="wanted"; assert d["denials"]["closeout"]["count"]==3; assert d["anti_patterns"]["looping-denial"]["count"]==1; assert len(d["switches"])==1' <<< "$json" || { echo 'not ok - JSON contract'; exit 1; }
python3 "$REPORT" --since 2026-09-08T10:04:00Z --log "$LOG" --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert all(v["first"] >= "2026-09-08T10:04:00Z" for v in d["denials"].values())' || { echo 'not ok - since filter'; exit 1; }

# Mutation check: deleting one regex must make this same fixture red.
cp "$REPORT" "$T/guard_report.py"
sed '/"verdict-pipe"/d' "$T/guard_report.py" > "$T/mutated.py"
mutated="$(python3 "$T/mutated.py" --session wanted --log "$LOG")" || exit $?
[ "$(printf '%s\n' "$mutated" | grep -c '^| verdict-pipe |')" -eq 0 ] || { echo 'not ok - regex deletion did not falsify'; exit 1; }

echo 'guard-report: 14 fixture rows, 11 named patterns, JSON/filtering and regex-deletion falsification ok'
