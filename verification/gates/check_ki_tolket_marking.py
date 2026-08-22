"""Hard gate for visible marking of declared model-derived frontend content.

Every model-derived render container declares a stable ``data-model-derived`` id
and binds its visible label with ``data-ki-tolket-mark="KI-tolket"``.  The
checked-in inventory makes removal and undeclared additions fail closed; the
container check makes marking local to the content instead of accepting an
unrelated label elsewhere in the file.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter

INVENTORY = pathlib.Path("config/ki-tolket-surfaces.json")
FRONTEND = pathlib.Path("frontend/src")
_DECLARATION_RE = re.compile(r"\bdata-model-derived\s*=\s*([\"'])(?P<surface>[a-z0-9][a-z0-9-]*)\1")
_BOUND_MARK_RE = re.compile(r"\bdata-ki-tolket-mark\s*=\s*([\"'])KI-tolket\1")
_VISIBLE_MARK_RE = re.compile(
    r"(?:^|>)\s*[^<{]*\bKI-tolket\b|"
    r"[\"'][^\"']*\bKI-tolket\b[^\"']*[\"']|"
    r"\{\s*(?:ASSISTIVE|MODEL)_MARK\s*\}"
)
_COMMENT_RE = re.compile(r"/\*.*?\*/|\{\s*/\*.*?\*/\s*\}", re.DOTALL)


def _load_inventory(repo_root: pathlib.Path) -> tuple[set[str], int, list[str]]:
    path = repo_root / INVENTORY
    if not path.exists():
        return set(), 0, []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return set(), 0, [f"{INVENTORY}: cannot read marking inventory: {exc}"]
    return _parse_inventory(raw)


def _parse_inventory(raw: object) -> tuple[set[str], int, list[str]]:
    error = _inventory_schema_error(raw)
    if error is not None:
        return set(), 0, [error]
    assert isinstance(raw, dict)
    surfaces = raw["surfaces"]
    minimum = raw.get("minimum_surface_count", 0)
    duplicates = sorted(name for name, count in Counter(surfaces).items() if count > 1)
    if duplicates:
        return (
            set(surfaces),
            minimum,
            [f"{INVENTORY}: duplicate model-derived surface id(s): {', '.join(duplicates)}"],
        )
    return set(surfaces), minimum, []


def _inventory_schema_error(raw: object) -> str | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("surfaces"), list):
        return f"{INVENTORY}: expected an object with a 'surfaces' list"
    minimum = raw.get("minimum_surface_count", 0)
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 0:
        return f"{INVENTORY}: 'minimum_surface_count' must be a non-negative integer"
    if any(not isinstance(value, str) for value in raw["surfaces"]):
        return f"{INVENTORY}: every surface id must be a string"
    return None


def _opening_tag(text: str, declaration: re.Match[str]) -> tuple[str, int, str] | None:
    start = text.rfind("<", 0, declaration.start())
    if start < 0:
        return None
    end = text.find(">", declaration.end())
    if end < 0:
        return None
    opening = text[start : end + 1]
    tag = re.match(r"<\s*([A-Za-z][A-Za-z0-9_.:-]*)\b", opening)
    return (opening, end + 1, tag.group(1)) if tag else None


def _container_region(text: str, declaration: re.Match[str]) -> tuple[str, str] | None:
    opened = _opening_tag(text, declaration)
    if opened is None:
        return None
    opening, body_start, tag = opened
    if opening.rstrip().endswith("/>"):
        return opening, ""
    tag_re = re.compile(rf"<\s*(?P<close>/)?\s*{re.escape(tag)}\b[^>]*>")
    depth = 1
    for match in tag_re.finditer(text, body_start):
        token = match.group(0)
        if match.group("close"):
            depth -= 1
            if depth == 0:
                return opening, text[body_start : match.start()]
        elif not token.rstrip().endswith("/>"):
            depth += 1
    return None


def _declaration_findings(
    relative: pathlib.Path,
    text: str,
    declaration: re.Match[str],
    expected: set[str],
) -> tuple[str, list[str]]:
    surface = declaration.group("surface")
    findings: list[str] = []
    if surface not in expected:
        findings.append(
            f"{relative}: model-derived surface {surface!r} is not registered in {INVENTORY}"
        )
    region = _container_region(text, declaration)
    if region is None:
        findings.append(
            f"{relative}: model-derived surface {surface!r} has no parseable JSX container"
        )
        return surface, findings
    opening, body = region
    if not _BOUND_MARK_RE.search(opening):
        findings.append(
            f"{relative}: model-derived surface {surface!r} is not visibly marked "
            "KI-tolket (missing data-ki-tolket-mark binding)"
        )
        return surface, findings
    visible_body = _COMMENT_RE.sub("", body)
    if not _VISIBLE_MARK_RE.search(visible_body):
        findings.append(
            f"{relative}: model-derived surface {surface!r} is not visibly marked "
            "KI-tolket inside its container"
        )
    return surface, findings


def _scan_frontend(
    repo_root: pathlib.Path,
    expected: set[str],
) -> tuple[dict[str, list[pathlib.Path]], list[str]]:
    source_root = repo_root / FRONTEND
    declarations: dict[str, list[pathlib.Path]] = {}
    findings: list[str] = []
    if not source_root.is_dir():
        return declarations, findings
    for path in sorted(source_root.rglob("*.tsx")):
        if path.name.endswith((".test.tsx", ".stories.tsx")):
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(repo_root)
        for declaration in _DECLARATION_RE.finditer(text):
            surface, problems = _declaration_findings(relative, text, declaration, expected)
            declarations.setdefault(surface, []).append(relative)
            findings.extend(problems)
    return declarations, findings


def check_marking(
    repo_root: pathlib.Path,
) -> list[str]:
    expected, minimum, findings = _load_inventory(repo_root)
    if len(expected) < minimum:
        findings.append(
            f"{INVENTORY}: surface inventory is below minimum_surface_count "
            f"({len(expected)} < {minimum}); restore the removed model-derived surface"
        )
    declarations, scan_findings = _scan_frontend(repo_root, expected)
    findings.extend(scan_findings)

    for surface in sorted(expected):
        paths = declarations.get(surface, [])
        if not paths:
            findings.append(
                f"{INVENTORY}: registered model-derived surface {surface!r} is missing "
                f"from {FRONTEND}"
            )
        elif len(paths) > 1:
            rendered = ", ".join(str(path) for path in paths)
            findings.append(
                f"{INVENTORY}: model-derived surface {surface!r} is declared more than "
                f"once: {rendered}"
            )

    if not expected:
        findings.append(
            f"{INVENTORY}: no model-derived surfaces are registered; the KI-tolket gate "
            "would protect nothing"
        )
    return findings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    findings = check_marking(args.root.resolve())
    for finding in findings:
        print(f"[ki-tolket] {finding}")
    print(f"\n{len(findings)} KI-tolket marking finding(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
