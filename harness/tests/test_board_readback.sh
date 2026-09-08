#!/usr/bin/env bash
# Falsifies M-9 board read-back with a file-backed gh runner; no network is used.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
READBACK="$HERE/../board_readback.sh"
T="$(mktemp -d "${TMPDIR:-/tmp}/board readback test.XXXXXX")"
trap 'rm -rf "$T"' EXIT

mkdir -p "$T/bin"
cat > "$T/bin/gh-runner" <<'SH'
#!/usr/bin/env bash
printf '%s %s %s\n' "$1" "$2" "${3:-}" >> "$FAKE_GH_LOG"
case "$1:$2" in
  project:item-list) response="$FAKE_GH_ITEM_LIST_RESPONSE"; operation=item-list ;;
  api:graphql) response="$FAKE_GH_GRAPHQL_RESPONSE"; operation=graphql ;;
  *) echo "unsupported fake gh call: $*" >&2; exit 2 ;;
esac
[ "${FAKE_GH_FAIL_ON:-}" = "$operation" ] && exit 1
cat "$response"
SH
chmod +x "$T/bin/gh-runner"

run_readback() {
  BOARD_OWNER=acme BOARD_PROJECT_NUMBER=7 BOARD_REPOSITORY=acme/widget \
    GH_RUNNER="$T/bin/gh-runner" FAKE_GH_LOG="$T/gh.log" \
    FAKE_GH_ITEM_LIST_RESPONSE="$T/items.json" \
    FAKE_GH_GRAPHQL_RESPONSE="$T/transition.json" "$READBACK" "$@"
}

cat > "$T/items.json" <<'JSON'
{"items":[
  {"id":"PVTI_other","title":"Other repository issue","status":"Done","content":{"type":"Issue","number":42,"repository":"acme/other","state":"CLOSED","url":"https://github.example/acme/other/issues/42"}},
  {"id":"PVTI_pr","title":"Pull request with the same number","status":"Done","content":{"type":"PullRequest","number":42,"repository":"acme/widget","state":"MERGED","url":"https://github.example/acme/widget/pull/42"}},
  {"id":"PVTI_target","title":"Ship read-back","status":"In flight","content":{"type":"Issue","number":42,"repository":"acme/widget","state":"OPEN","url":"https://github.example/acme/widget/issues/42"}}
],"totalCount":3}
JSON
cat > "$T/transition.json" <<'JSON'
{"data":{"node":{"status":{"name":"In flight","updatedAt":"2026-09-08T09:30:00Z"}}}}
JSON

out="$(run_readback 42)" || { echo 'not ok - matching item was rejected'; exit 1; }
[ "$out" = 'issue #42: project status="In flight"; last transition="2026-09-08T09:30:00Z"' ] || { echo "not ok - read-back output: $out"; exit 1; }
[ "$(sed -n '1p' "$T/gh.log")" = 'project item-list 7' ] && [ "$(sed -n '2p' "$T/gh.log")" = 'api graphql -f' ] || { echo 'not ok - item-list and transition invocations'; cat "$T/gh.log"; exit 1; }

set +e
BOARD_LIMIT=3 run_readback 42 >"$T/truncated.out" 2>"$T/truncated.err"; rc=$?
set -e
if [ "$rc" -eq 0 ] || ! grep -q 'item-list was truncated' "$T/truncated.err"; then
  echo 'not ok - a full page was accepted as a complete board'
  exit 1
fi

set +e
out="$(run_readback 42 Done 2>"$T/wrong.err")"; rc=$?
set -e
if [ "$rc" -eq 0 ] || [ "$out" != 'issue #42: project status="In flight"; last transition="2026-09-08T09:30:00Z"' ] || ! grep -q 'expected project status="Done"' "$T/wrong.err"; then
  echo 'not ok - wrong state did not fail with the observed read-back'
  exit 1
fi

cat > "$T/items.json" <<'JSON'
{"items":[{"id":"PVTI_other","title":"Different item","status":"In flight","content":{"type":"Issue","number":41,"repository":"acme/widget","state":"OPEN","url":"https://github.example/acme/widget/issues/41"}}],"totalCount":1}
JSON
set +e
run_readback 42 >"$T/missing.out" 2>"$T/missing.err"; rc=$?
set -e
if [ "$rc" -eq 0 ] || ! grep -q 'issue #42 is missing' "$T/missing.err"; then
  echo 'not ok - missing item did not fail'
  exit 1
fi

cat > "$T/items.json" <<'JSON'
{"items":[{"id":"PVTI_target","title":"Ship read-back","status":"In flight","content":{"type":"Issue","number":42,"repository":"acme/widget","state":"OPEN","url":"https://github.example/acme/widget/issues/42"}}],"totalCount":1}
JSON
cat > "$T/transition.json" <<'JSON'
{"data":{"node":{"status":null}}}
JSON
run_readback 42 >"$T/no-transition.out" 2>"$T/no-transition.err" && { echo 'not ok - absent transition timestamp was accepted'; exit 1; }
grep -q 'board not verified (offline:' "$T/no-transition.err" || { echo 'not ok - unavailable transition did not name offline verification'; exit 1; }

FAKE_GH_FAIL_ON=item-list run_readback 42 >"$T/offline.out" 2>"$T/offline.err" && { echo 'not ok - gh failure was accepted'; exit 1; }
grep -q 'board not verified (offline:' "$T/offline.err" || { echo 'not ok - gh failure did not name unavailable verification'; exit 1; }

echo 'board-readback: matching repository, status-field transition, missing/wrong states and gh failure ok'
