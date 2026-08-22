#!/bin/zsh
# Provisions the factory's GitHub Projects board (the planning source of truth).
# Usage: ./bootstrap_board.sh <owner> "<board name>"
# Requires gh with the project scope (gh auth refresh -s project).
set -e
OWNER="$1"; NAVN="${2:-Arbeidsflate}"
gh project create --owner "$OWNER" --title "$NAVN"
NUM=$(gh project list --owner "$OWNER" --format json | python3 -c "import json,sys; ps=json.load(sys.stdin)['projects']; print([p['number'] for p in ps if p['title']=='$NAVN'][0])")
PID=$(gh project view "$NUM" --owner "$OWNER" --format json --jq .id)
# The Status field with the factory's states (see planning/board-protocol.md)
FID=$(gh project field-list "$NUM" --owner "$OWNER" --format json --jq '.fields[] | select(.name=="Status") | .id')
for opt in "Planned" "In flight" "Deferred" "Decision needed" "Blocked–external" "Dropped"; do
  gh api graphql -f query='mutation($p: ID!, $f: ID!, $n: String!) {
    updateProjectV2Field(input: {fieldId: $f, singleSelectOptions: [{name: $n, color: GRAY, description: ""}]}) { projectV2Field { ... on ProjectV2SingleSelectField { id } } } }' \
    -f p="$PID" -f f="$FID" -f n="$opt" 2>/dev/null || true
done
echo "Board #$NUM ($PID) provisioned. NB: bulk option setup via GraphQL may need manual touch-up in the UI — verify all states exist (+ built-in Done)."
echo "Write the project ID + field IDs into the repo CLAUDE.md anchor (see planning/CLAUDE.md.example)."
