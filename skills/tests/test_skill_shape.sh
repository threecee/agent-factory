#!/bin/sh
# Falsify skills/check_skill_shape.py on a throwaway copy. The package tree is
# never mutated. Run: sh skills/tests/test_skill_shape.sh (exit 0 = all hold).
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
CHECK="$HERE/check_skill_shape.py"
T="$(mktemp -d "${TMPDIR:-/tmp}/skill-shape-test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
cp -R "$HERE" "$T/skills"
rm -rf "$T/skills/tests"
fail=0
check() { # label expected actual
  if [ "$2" = "$3" ]; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s (expected %s, got %s)\n' "$1" "$2" "$3"; fail=1; fi
}
run() { python3 "$CHECK" --root "$T/skills" >/dev/null 2>&1; echo $?; }

check "1 untouched split skills are green" 0 "$(run)"
ref="$T/skills/test-driven-development/references/full-guide.md"
sed '$d' "$ref" > "$ref.short" && mv "$ref.short" "$ref"
check "2 shortening one reference by a line is red" 1 "$(run)"
python3 "$CHECK" --root "$T/skills" 2>&1 | grep -q 'test-driven-development.*baseline line' && echo "ok   2b message names the lost baseline line" || { echo "FAIL 2b message"; fail=1; }
cp "$HERE/test-driven-development/references/full-guide.md" "$ref"
printf '\nunlinked\n' > "$T/skills/test-driven-development/references/unlinked.md"
check "3 an unreferenced Markdown reference is red" 1 "$(run)"
rm "$T/skills/test-driven-development/references/unlinked.md"
check "4 restored copy is green" 0 "$(run)"
exit $fail
