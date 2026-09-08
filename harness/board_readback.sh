#!/usr/bin/env bash
# Read one issue's authoritative GitHub Project status without changing the board.
set -u

usage() {
  echo 'usage: BOARD_OWNER=<owner> BOARD_PROJECT_NUMBER=<number> BOARD_REPOSITORY=<owner/name> harness/board_readback.sh <issue-number> [expected-status]' >&2
  exit 64
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
ISSUE_NUMBER="$1"
case "$ISSUE_NUMBER" in ''|*[!0-9]*) usage ;; esac
[ "$ISSUE_NUMBER" -gt 0 ] || usage

BOARD_OWNER="${BOARD_OWNER:-}"
BOARD_PROJECT_NUMBER="${BOARD_PROJECT_NUMBER:-}"
BOARD_REPOSITORY="${BOARD_REPOSITORY:-}"
EXPECTED_STATUS="${2:-${BOARD_EXPECTED_STATUS:-In flight}}"
GH_RUNNER="${GH_RUNNER:-gh}"
LIMIT="${BOARD_LIMIT:-200}"

[ -n "$BOARD_OWNER" ] && [ -n "$BOARD_PROJECT_NUMBER" ] && [ -n "$BOARD_REPOSITORY" ] && [ -n "$EXPECTED_STATUS" ] || usage
case "$BOARD_PROJECT_NUMBER" in *[!0-9]*|'') usage ;; esac
case "$LIMIT" in *[!0-9]*|'') usage ;; esac
[ "$BOARD_PROJECT_NUMBER" -gt 0 ] && [ "$LIMIT" -gt 0 ] || usage

if ! BOARD_JSON="$("$GH_RUNNER" project item-list "$BOARD_PROJECT_NUMBER" --owner "$BOARD_OWNER" --limit "$LIMIT" --format json)"; then
  echo "board read-back: issue #$ISSUE_NUMBER board not verified (offline: gh project item-list failed)" >&2
  exit 69
fi

ITEM_DATA="$(printf '%s\n' "$BOARD_JSON" | python3 -c '
import json
import sys

issue = int(sys.argv[1])
repository = sys.argv[2].lower()
limit = int(sys.argv[3])

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, UnicodeDecodeError) as error:
    print(f"board read-back: issue #{issue} board not verified (invalid JSON: {error})", file=sys.stderr)
    raise SystemExit(69)

items = data.get("items") if isinstance(data, dict) else None
if not isinstance(items, list):
    print(f"board read-back: issue #{issue} board not verified (response has no items list)", file=sys.stderr)
    raise SystemExit(69)
if len(items) >= limit or isinstance(data.get("totalCount"), int) and data["totalCount"] > len(items):
    print(f"board read-back: issue #{issue} board not verified (item-list was truncated; raise --limit)", file=sys.stderr)
    raise SystemExit(69)

def repository_name(content):
    value = content.get("repository")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("nameWithOwner") or value.get("name_with_owner")
    return None

matches = []
for item in items:
    if not isinstance(item, dict):
        continue
    content = item.get("content")
    if not isinstance(content, dict) or content.get("type") != "Issue" or content.get("number") != issue:
        continue
    found_repository = repository_name(content)
    if isinstance(found_repository, str) and found_repository.lower() == repository:
        matches.append(item)

if not matches:
    print(f"board read-back: issue #{issue} is missing from project {sys.argv[4]}", file=sys.stderr)
    raise SystemExit(2)
if len(matches) != 1:
    print(f"board read-back: issue #{issue} is ambiguous in project {sys.argv[4]}", file=sys.stderr)
    raise SystemExit(2)

item = matches[0]
item_id = item.get("id")
status = item.get("status")
if not isinstance(item_id, str) or not item_id or not isinstance(status, str) or not status:
    print(f"board read-back: issue #{issue} board not verified (item has no id or status)", file=sys.stderr)
    raise SystemExit(69)
print(item_id)
print(status)
' "$ISSUE_NUMBER" "$BOARD_REPOSITORY" "$LIMIT" "$BOARD_PROJECT_NUMBER")"
PARSE_STATUS=$?
[ "$PARSE_STATUS" -eq 0 ] || exit "$PARSE_STATUS"

ITEM_ID="$(printf '%s\n' "$ITEM_DATA" | sed -n '1p')"
STATUS="$(printf '%s\n' "$ITEM_DATA" | sed -n '2p')"
# GraphQL variables use a literal dollar sign; shell expansion is unwanted.
# shellcheck disable=SC2016
STATUS_QUERY='query($item: ID!) {
  node(id: $item) {
    ... on ProjectV2Item {
      status: fieldValueByName(name: "Status") {
        ... on ProjectV2ItemFieldSingleSelectValue { name updatedAt }
      }
    }
  }
}'

if ! TRANSITION_JSON="$("$GH_RUNNER" api graphql -f query="$STATUS_QUERY" -f item="$ITEM_ID")"; then
  echo "board read-back: issue #$ISSUE_NUMBER board not verified (offline: status transition query failed)" >&2
  exit 69
fi

LAST_TRANSITION="$(printf '%s\n' "$TRANSITION_JSON" | python3 -c '
import json
import sys

issue = sys.argv[1]
observed = sys.argv[2]
try:
    data = json.load(sys.stdin)
    status = data["data"]["node"]["status"]
    name = status["name"]
    updated_at = status["updatedAt"]
except (json.JSONDecodeError, KeyError, TypeError):
    print(f"board read-back: issue #{issue} board not verified (offline: current status transition is unavailable)", file=sys.stderr)
    raise SystemExit(69)
if name != observed:
    print(f"board read-back: issue #{issue} changed during read-back (item-list=\"{observed}\", transition=\"{name}\")", file=sys.stderr)
    raise SystemExit(1)
print(updated_at)
' "$ISSUE_NUMBER" "$STATUS")"
PARSE_STATUS=$?
[ "$PARSE_STATUS" -eq 0 ] || exit "$PARSE_STATUS"

printf 'issue #%s: project status="%s"; last transition="%s"\n' "$ISSUE_NUMBER" "$STATUS" "$LAST_TRANSITION"
if [ "$STATUS" != "$EXPECTED_STATUS" ]; then
  printf 'board read-back: issue #%s expected project status="%s", observed="%s"\n' "$ISSUE_NUMBER" "$EXPECTED_STATUS" "$STATUS" >&2
  exit 1
fi
