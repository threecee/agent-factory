#!/bin/zsh
# launch_lane.sh <lane> <driver primary|openrouter> <effort> <delay-s>
# Launches one lane via a coding CLI (codex shown; adapt for your driver).
# 'openrouter' uses a provider override for an alternate/free model tier;
# stagger starts (delay-s) to avoid free-tier 429 storms. stdin MUST be
# closed (< /dev/null) — an open stdin makes some CLIs wait forever.
LANE="$1"; DRIVER="$2"; EFFORT="$3"; DELAY="${4:-0}"
S="/private/tmp/claude-501/-Users-carl-Projects-kripos-chatanalyse/d582d864-193e-48ee-8734-a1b6f462ec2d/scratchpad"
WT="/Users/carl/Projects/kripos-wt/$LANE"
[ "$DELAY" -gt 0 ] && sleep "$DELAY"
if [ "$DRIVER" = "openrouter" ]; then
  export OPENROUTER_API_KEY="$(grep -m1 '^OPENROUTER_API_KEY=' /Users/carl/Projects/kripos-chatanalyse/.env | cut -d= -f2-)"
  codex exec \
    -c 'model_providers.openrouter.name="OpenRouter"' \
    -c 'model_providers.openrouter.base_url="https://openrouter.ai/api/v1"' \
    -c 'model_providers.openrouter.env_key="OPENROUTER_API_KEY"' \
    -c 'model_provider="openrouter"' -c 'model="stealth/ox-alpha"' \
    --sandbox workspace-write --cd "$WT" \
    "$(cat "$S/$LANE-brief.md")" < /dev/null > "$S/$LANE-codex.log" 2>&1
else
  codex exec -c "model_reasoning_effort=\"$EFFORT\"" \
    --sandbox workspace-write --cd "$WT" \
    "$(cat "$S/$LANE-brief.md")" < /dev/null > "$S/$LANE-codex.log" 2>&1
fi
echo "exit=$?" > "$S/$LANE-codex.exit"
