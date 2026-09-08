#!/usr/bin/env bash
# Every kit ADR binds its decision to existing implementation and executable proof.
set -u

HERE="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="${TEST_ADR_ANCHORS_ROOT:-$HERE/../..}"
ROOT="$(cd "$ROOT" && pwd -P)"

python3 - "$ROOT" <<'PY'
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
decision_dir = root / "decisions"
files = sorted(decision_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))
findings: list[str] = []

expected = {
    "0001-guards-fail-open.md": "# ADR-0001: Guards fail open on apparatus failure",
    "0002-switches-precede-guards-and-leave-a-trace.md": "# ADR-0002: Switches precede guards and leave a trace",
    "0003-hub-pointers-with-one-sentence-glosses.md": "# ADR-0003: Hubs use pointers with one-sentence glosses",
    "0004-pr-default-with-owner-signed-direct-push.md": "# ADR-0004: Pull requests default, with owner-signed direct push",
    "0005-child-processes-drop-hook-repository-pins.md": "# ADR-0005: Child processes drop hook repository pins",
    "0006-three-durable-artifacts.md": "# ADR-0006: Three durable artifacts answer three questions",
}

actual_names = {path.name for path in files}
for name in sorted(set(expected) - actual_names):
    findings.append(f"decisions: missing required ADR {name}")
for name in sorted(actual_names - set(expected)):
    findings.append(f"decisions: unexpected numbered ADR {name}")

registry = decision_dir / "NUMBERS.md"
if not registry.is_file():
    findings.append("decisions/NUMBERS.md: missing")
else:
    registry_text = registry.read_text(encoding="utf-8")
    active_rows = re.findall(
        r"(?m)^\|\s*ADR\s*\|\s*([0-9]{4})\s*\|.*\|\s*(claimed|landed)\s*\|",
        registry_text,
    )
    active_numbers = [number for number, _state in active_rows]
    expected_numbers = [f"{number:04d}" for number in range(1, 7)]
    for number in expected_numbers:
        count = active_numbers.count(number)
        if count != 1:
            findings.append(f"decisions/NUMBERS.md: ADR {number} has {count} active rows, expected 1")
    for number in sorted(set(active_numbers) - set(expected_numbers)):
        findings.append(f"decisions/NUMBERS.md: unexpected active ADR row {number}")

def frontmatter(text: str, path: pathlib.Path) -> dict[str, object]:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        findings.append(f"{path.relative_to(root)}: missing YAML frontmatter")
        return {}
    block = text[4:].split("\n---\n", 1)[0]
    data: dict[str, object] = {}
    active: str | None = None
    for line in block.splitlines():
        item = re.match(r"^  -\s+(.+?)\s*$", line)
        if item and active:
            value = item.group(1).strip("'\"")
            cast = data.setdefault(active, [])
            if isinstance(cast, list):
                cast.append(value)
            continue
        field = re.match(r"^([a-z]+):(?:\s*(.*))?$", line)
        if field:
            active = field.group(1)
            value = (field.group(2) or "").strip().strip("'\"")
            data[active] = value if value else []
    return data

def check_anchor(owner: pathlib.Path, anchor: str, kind: str) -> None:
    path_text, separator, case_id = anchor.partition(" ")
    target = root / path_text
    if not target.is_file():
        findings.append(f"{owner.relative_to(root)}: {kind} anchor path does not exist: {path_text}")
        return
    if not separator:
        return
    if kind != "tests":
        findings.append(f"{owner.relative_to(root)}: only test anchors may carry a case id: {anchor}")
        return
    content = target.read_text(encoding="utf-8")
    token = re.compile(rf"(?<![A-Za-z0-9]){re.escape(case_id)}(?![A-Za-z0-9])")
    if not token.search(content):
        findings.append(f"{owner.relative_to(root)}: test case id does not resolve: {anchor}")

for path in files:
    text = path.read_text(encoding="utf-8")
    data = frontmatter(text, path)
    number = path.name[:4]
    wanted_title = expected.get(path.name)
    if wanted_title is not None and wanted_title not in text.splitlines():
        findings.append(f"{path.relative_to(root)}: required title is missing: {wanted_title}")
    if data.get("id") != f"ADR-{number}":
        findings.append(f"{path.relative_to(root)}: id must be ADR-{number}")
    if data.get("status") != "Accepted":
        findings.append(f"{path.relative_to(root)}: status must be Accepted")
    for kind in ("code", "tests"):
        anchors = data.get(kind)
        if not isinstance(anchors, list) or not anchors:
            findings.append(f"{path.relative_to(root)}: {kind} must be a non-empty list")
            continue
        for anchor in anchors:
            check_anchor(path, anchor, kind)

if findings:
    for finding in findings:
        print(f"adr-anchors: {finding}", file=sys.stderr)
    raise SystemExit(1)

print(f"adr-anchors: {len(files)} ADRs and all code/test anchors resolve")
PY
