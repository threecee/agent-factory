#!/bin/sh
# Falsification of skills/verify_skills_lock.py on a throwaway COPY of the
# skill set (the package tree is never touched). Expected shape:
#   1 green on an untouched copy
#   2 red   when one byte is appended to one SKILL.md   (drift)
#   3 red   when an unlocked skill directory is added   (extra)
#   3b red  when one retired skill is restored without a lock row (extra)
#   4 red   when a locked skill directory is removed    (missing)
#   5 green again after restore
#   6 --update on an adapted copy makes it green and changes exactly one entry
#   7 the coreutils recipe from the docstring reproduces one locked digest
# Run:  sh skills/tests/test_skills_lock.sh     (exit 0 = all seven hold)
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
VERIFY="$HERE/verify_skills_lock.py"
T="$(mktemp -d "${TMPDIR:-/tmp}/skills-lock-test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
cp -R "$HERE" "$T/skills"
rm -rf "$T/skills/tests"
fail=0
check() { # label expected actual
  if [ "$2" = "$3" ]; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s (expected %s, got %s)\n' "$1" "$2" "$3"; fail=1; fi
}
run() { python3 "$VERIFY" --check --root "$T/skills" >/dev/null 2>&1; echo $?; }
first="$(ls "$T/skills" | while read -r d; do [ -f "$T/skills/$d/SKILL.md" ] && echo "$d" && break; done)"

check "1 untouched copy is green" 0 "$(run)"
printf '\n' >> "$T/skills/$first/SKILL.md"
check "2 one appended byte is red" 1 "$(run)"
python3 "$VERIFY" --check --root "$T/skills" 2>&1 | grep -q "drift: $first" && echo "ok   2b message names the drifted skill" || { echo "FAIL 2b message"; fail=1; }
cp -R "$HERE/$first" "$T/skills/$first.restore" && rm -rf "$T/skills/$first" && mv "$T/skills/$first.restore" "$T/skills/$first"
check "2c restore is green" 0 "$(run)"
mkdir -p "$T/skills/zz-extra" && printf 'x\n' > "$T/skills/zz-extra/SKILL.md"
check "3 unlocked extra skill is red" 1 "$(run)"
rm -rf "$T/skills/zz-extra"
git -C "$HERE/.." archive origin/main skills/executing-plans | tar -x -C "$T"
check "3b restored retired skill without a lock row is red" 1 "$(run)"
rm -rf "$T/skills/executing-plans"
mv "$T/skills/$first" "$T/$first.away"
check "4 missing locked skill is red" 1 "$(run)"
mv "$T/$first.away" "$T/skills/$first"
check "5 restored copy is green" 0 "$(run)"
printf '\n' >> "$T/skills/$first/SKILL.md"
python3 "$VERIFY" --update --root "$T/skills" >/dev/null 2>&1
check "6 --update on the adapted copy is green" 0 "$(run)"
changed="$(python3 - "$HERE/skills-lock.json" "$T/skills/skills-lock.json" <<'EOF'
import json,sys
a=json.load(open(sys.argv[1]))["skills"]; b=json.load(open(sys.argv[2]))["skills"]
print(sum(1 for k in a if a[k]["tree_sha256"]!=b[k]["tree_sha256"]))
EOF
)"
check "6b exactly one entry changed" 1 "$changed"
recomputed="$(cd "$HERE/$first" && find . -type f ! -path '*/__pycache__/*' ! -name .DS_Store | sed 's|^\./||' | LC_ALL=C sort | while read -r f; do printf '%s\t%s\n' "$f" "$(shasum -a 256 "$f" | cut -d' ' -f1)"; done | shasum -a 256 | cut -d' ' -f1)"
locked="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['skills'][sys.argv[2]]['tree_sha256'])" "$HERE/skills-lock.json" "$first")"
check "7 coreutils recipe reproduces the locked digest of $first" "$locked" "$recomputed"
exit $fail
