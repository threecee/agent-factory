# fakecli body: invoked by the launcher as  fakecli <this file> exec --cd <wt> <brief_path>
# A scripted stand-in for a coding CLI. It reads ONLY the launcher's environment
# names (never a retyped path), implements the smoke feature, keeps the sentinel
# fresh, runs the brief's pregate, and writes the report at $LANE_RESULT_PATH.
# It never commits and never pushes: the wrapper does (worktree-ritual).
set -eu
cd "$LANE_WORKTREE"
BRIEF="$4"
SENT="python3 scripts/lane_sentinel.py update --lane $LANE --dir $LANE_SENTINEL_DIR"
$SENT --status working --leg "read brief" --branch "$(git rev-parse --abbrev-ref HEAD)" >/dev/null
TASK="$(sed -n 's/^- Task: `\([^`]*\)`.*/\1/p' "$BRIEF")"
ROUND="$(sed -n 's/^- Round: `\([12]\) of 2`.*/\1/p' "$BRIEF")"
# --- author the feature (greet takes an optional name) and its test
cat > src/hello.js <<'EOF'
'use strict';
function greet(name) {
  const who = typeof name === 'string' && name.trim() !== '' ? name.trim() : 'world';
  return `hello, ${who}`;
}
if (require.main === module) {
  if (process.argv.includes('--where')) {
    console.log(__filename);
  } else {
    console.log(greet(process.argv[2]));
  }
}
module.exports = { greet };
EOF
cat > test/hello.test.js <<'EOF'
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { greet } = require('../src/hello.js');
test('greet returns the plain greeting without a name', () => {
  assert.equal(greet(), 'hello, world');
});
test('greet uses the name when one is given', () => {
  assert.equal(greet('Ada'), 'hello, Ada');
});
test('greet treats an empty or blank name as absent', () => {
  assert.equal(greet(''), 'hello, world');
  assert.equal(greet('   '), 'hello, world');
});
EOF
$SENT --status working --leg "pregate" >/dev/null
node scripts/check_lint_ratchet.mjs > "$LANE_RUN_DIR/$LANE.$LANE_RUN_ID.pregate.log" 2>&1; g1=$?
node --test >> "$LANE_RUN_DIR/$LANE.$LANE_RUN_ID.pregate.log" 2>&1; g2=$?
passed="$(grep -E '^ℹ pass' "$LANE_RUN_DIR/$LANE.$LANE_RUN_ID.pregate.log" | awk '{print $3}')"
status=built; [ "$g1" = 0 ] && [ "$g2" = 0 ] || status=failed
cat > "$LANE_RESULT_PATH" <<EOF
---
lane: $LANE
run_id: $LANE_RUN_ID
task: $TASK
round: $ROUND
status: $status
branch: $(git rev-parse --abbrev-ref HEAD)
head_sha: $(git rev-parse HEAD)
files_touched:
  - src/hello.js
  - test/hello.test.js
gates:
  - 'lint-ratchet $( [ "$g1" = 0 ] && echo ok || echo red ) no-console 2/2 baseline'
  - 'node --test $( [ "$g2" = 0 ] && echo ok || echo red ) $passed passed/0 failed'
pregate_clean: $( [ "$status" = built ] && echo true || echo false )
measurements:
  - artifact: test count in test/hello.test.js
    observed: before 1; after 3
choices:
  - {headline: Blank name treated as absent, verdict: sound, confidence: M, gap: Spec says "optional name" and is silent on whitespace.}
choices_sidecar: $LANE_RUN_DIR/$LANE-choices.md
proof:
  - 'red-green: test "greet uses the name when one is given" fails on the pre-change src/hello.js, passes after'
report: |-
  greet(name) returns "hello, <name>"; default kept for undefined, empty and blank names.
  No dependency, ADR or number added; ADR-0001 was pre-claimed by the orchestrator.
  Pregate log: $LANE_RUN_DIR/$LANE.$LANE_RUN_ID.pregate.log
---
EOF
cat > "$LANE_RUN_DIR/$LANE-choices.md" <<'EOF'
## Blank name treated as absent
Scenario: the CLI is called as `node src/hello.js "   "`. Reading: a user who
pressed space by mistake gets `hello, world`, not `hello,    `. Alternative:
return the blank verbatim (faithful to input, ugly output). Chosen: trim and
fall back, because the spec's word "optional" describes intent, not bytes.
Reversible: yes — one predicate. Evidence: the third test pins it.
EOF
$SENT --status "$( [ "$status" = built ] && echo done || echo failed )" --leg "report written" --last-artifact "$LANE_RESULT_PATH" >/dev/null
[ "$status" = built ]
