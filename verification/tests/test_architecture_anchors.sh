#!/usr/bin/env bash
# Root architecture and pattern documents point only at components that exist.
set -u

HERE="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="${TEST_ARCHITECTURE_ANCHORS_ROOT:-$HERE/../..}"
ROOT="$(cd "$ROOT" && pwd -P)"

python3 - "$ROOT" <<'PY'
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
findings: list[str] = []

def anchors(
    name: str,
    expected: dict[str, str],
    heading_pattern: str,
    limit: int | None = None,
) -> None:
    path = root / name
    if not path.is_file():
        findings.append(f"{name}: missing")
        return
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if limit is not None and len(lines) > limit:
        findings.append(f"{name}: {len(lines)} lines exceeds {limit}")
    found = re.findall(r"(?m)^code:\s+`([^`]+)`\s*$", text)
    if len(found) != len(expected):
        findings.append(f"{name}: expected {len(expected)} code anchors, found {len(found)}")
    for value in found:
        target = root / value.rstrip("/")
        if not target.exists():
            findings.append(f"{name}: code anchor does not exist: {value}")
    actual_headings = set(re.findall(heading_pattern, text, flags=re.MULTILINE))
    for heading in sorted(set(expected) - actual_headings):
        findings.append(f"{name}: missing required heading: {heading}")
    for heading in sorted(actual_headings - set(expected)):
        findings.append(f"{name}: unexpected numbered heading: {heading}")
    for heading, value in expected.items():
        pair = re.compile(
            rf"(?m)^{re.escape(heading)}\n\ncode:\s+`{re.escape(value)}`\s*$"
        )
        if not pair.search(text):
            findings.append(f"{name}: required heading/anchor pair is missing: {heading} -> {value}")

anchors(
    "ARCHITECTURE.md",
    expected={
        "### 3.1 Planning pillar": "planning/",
        "### 3.2 Verification pillar": "verification/",
        "### 3.3 Interpretation pillar": "interpretation/",
        "### 3.4 Harness": "harness/",
    },
    heading_pattern=r"^### 3\.[0-9]+ .+$",
    limit=200,
)
anchors(
    "PATTERNS.md",
    expected={
        "## 1. Guard rule module shape": "harness/guards/rules/no_verify.py",
        "## 2. Falsification by planting": "harness/tests/test_guards.sh",
        "## 3. Run-bound receipts": "harness/launch_lane.sh",
        "## 4. Sentinels": "verification/gates/lane_sentinel.py",
        "## 5. Wrappers": "harness/worktree-ritual.md",
        "## 6. Ratchets": "verification/gates/check_ruff_ratchet.py",
        "## 7. Hub pointers": "verification/tests/test_hub_pointers.sh",
        "## 8. Portable and stack-specific gates": "verification/gates/README.md",
    },
    heading_pattern=r"^## [0-9]+\. .+$",
)

if findings:
    for finding in findings:
        print(f"architecture-anchors: {finding}", file=sys.stderr)
    raise SystemExit(1)

print("architecture-anchors: 4 components and 8 patterns resolve")
PY
