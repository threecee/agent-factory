#!/bin/zsh
# Provisions the factory's GitHub Projects board (the planning source of truth).
# Usage: ./bootstrap_board.sh <owner> "<board name>"
# Requires gh with the project scope (gh auth refresh -s project).
set -e
OWNER="$1"; NAME="${2:-Workboard}"
gh project create --owner "$OWNER" --title "$NAME" > /dev/null
NUM=$(gh project list --owner "$OWNER" --format json | python3 -c "import json,sys; ps=json.load(sys.stdin)['projects']; print([p['number'] for p in ps if p['title']=='$NAME'][0])")
PID=$(gh project view "$NUM" --owner "$OWNER" --format json --jq .id)
FID=$(gh project field-list "$NUM" --owner "$OWNER" --format json --jq '.fields[] | select(.name=="Status") | .id')
# ONE mutation with the full desired option set (the API REPLACES the set —
# per-option calls would leave only the last one).
gh api graphql -f query='
mutation($f: ID!) {
  updateProjectV2Field(input: {fieldId: $f, singleSelectOptions: [
    {name: "Planned", color: BLUE, description: "Approved spec, dispatch-ready"},
    {name: "In flight", color: YELLOW, description: "A lane is working it"},
    {name: "Deferred", color: GRAY, description: "Valid intention, named gate"},
    {name: "Decision needed", color: ORANGE, description: "Owner must rule"},
    {name: "Blocked–external", color: RED, description: "Gate outside our control"},
    {name: "Done", color: GREEN, description: "Landed and swept"},
    {name: "Dropped", color: PURPLE, description: "Rejected or obsolete — body says why"}
  ]}) { projectV2Field { ... on ProjectV2SingleSelectField { id options { id name } } } }
}' -f f="$FID" --jq '.data.updateProjectV2Field.projectV2Field.options[] | "\(.name)=\(.id)"'
echo "Board #$NUM ($PID) provisioned; Status field $FID. Write these IDs into the repo CLAUDE.md anchor."
