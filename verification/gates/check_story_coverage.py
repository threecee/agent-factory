"""Requirement (CUJ / user-story) -> test coverage gate (software-factory, ADR-0063).

Closes the requirement leg of the traceability object: the canonical Critical User
Journeys live in docs/cuj-architecture/01-cuj-per-persona.md (H3 `### <ID> — title`);
a verifying test declares `Story: <CUJ-ID>` in its module docstring/comment. This
checker joins them and reports:
  - story_dangling: a test cites a `Story:` that is not a real CUJ (hard).
  - threaded_cuj_uncovered: a CUJ in THREADED_CUJS has no verifying test (hard).
Coverage of the not-yet-threaded personas is reported informationally — the corpus is
threaded one persona at a time (extend THREADED_CUJS as each lands).

Scope of the guarantee: coverage is EXISTENCE-based — a `Story:` marker proves a citing
test EXISTS, not that it semantically asserts the CUJ. Whether the test genuinely
verifies the journey is a human/review call (same as any ADR `code:` ref); the gate
catches a missing or dangling link, not a hollow one.

    python scripts/check_story_coverage.py          # report + exit 1 on hard gaps
    python scripts/check_story_coverage.py --report  # report, exit 0
"""

from __future__ import annotations

import pathlib
import re
import sys
from typing import NamedTuple

CUJ_DOC = pathlib.Path("docs/cuj-architecture/01-cuj-per-persona.md")
_CUJ_HEADER_RE = re.compile(r"^###\s+(\S*CUJ\S*)\s+[—–-]", re.MULTILINE)
_STORY_RE = re.compile(r"Story:\s*([A-Za-z0-9](?:[A-Za-z0-9.\-]*[A-Za-z0-9])?)")
_SCAN_EXCLUDE = {"test_story_coverage.py"}

THREADED_CUJS = {
    "ETT-CUJ-1",
    "ETT-CUJ-2",
    "ETT-CUJ-3",
    "CUJ-SAKSEIER-1",
    "CUJ-SAKSEIER-2",
    "CUJ-SAKSEIER-3",
    "CUJ-INTEL-1",
    "CUJ-INTEL-2",
    "CUJ-INTEL-3",
    "ADM-CUJ-1",
    "ADM-CUJ-2",
    "ADM-CUJ-3",
    "CUJ-JUR-1",
    "CUJ-JUR-2",
    "CUJ-JUR-3",
}


class StoryViolation(NamedTuple):
    kind: str
    cuj: str
    detail: str
    hard: bool


def canonical_cujs(repo_root: pathlib.Path) -> set[str]:
    """The CUJ ids declared as H3 headers in the CUJ-per-persona doc."""
    return set(_CUJ_HEADER_RE.findall((repo_root / CUJ_DOC).read_text(encoding="utf-8")))


def story_refs(repo_root: pathlib.Path) -> dict[str, list[str]]:
    """CUJ id -> sorted test files that declare `Story: <id>`."""
    refs: dict[str, set[str]] = {}
    tests_dir = repo_root / "tests"
    if not tests_dir.exists():
        return {}
    for py in tests_dir.rglob("*.py"):
        if py.name in _SCAN_EXCLUDE:
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for cid in _STORY_RE.findall(text):
            refs.setdefault(cid, set()).add(str(py.relative_to(repo_root)))
    return {k: sorted(v) for k, v in refs.items()}


def check_story_coverage(repo_root: pathlib.Path | None = None) -> list[StoryViolation]:
    repo_root = repo_root or pathlib.Path.cwd()
    cujs = canonical_cujs(repo_root)
    refs = story_refs(repo_root)
    out: list[StoryViolation] = []

    for cid, files in sorted(refs.items()):
        if cid not in cujs:
            out.append(
                StoryViolation("story_dangling", cid, f"cited by {files[0]} — no such CUJ", True)
            )
    for cid in sorted(THREADED_CUJS):
        if cid not in cujs:
            out.append(
                StoryViolation(
                    "threaded_cuj_unknown", cid, "in THREADED_CUJS but not in the CUJ doc", True
                )
            )
        elif cid not in refs:
            out.append(
                StoryViolation(
                    "threaded_cuj_uncovered", cid, "threaded but no test declares Story:", True
                )
            )
    return out


def coverage_report(repo_root: pathlib.Path | None = None) -> str:
    repo_root = repo_root or pathlib.Path.cwd()
    cujs = sorted(canonical_cujs(repo_root))
    refs = story_refs(repo_root)
    lines = [f"CUJ story coverage ({sum(1 for c in cujs if c in refs)}/{len(cujs)} covered):"]
    for c in cujs:
        mark = "✓" if c in refs else ("·" if c not in THREADED_CUJS else "✗")
        n = len(refs.get(c, []))
        lines.append(f"  {mark} {c} ({n} test{'s' if n != 1 else ''})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    print(coverage_report())
    violations = check_story_coverage()
    hard = [v for v in violations if v.hard]
    for v in violations:
        print(f"[{'HARD' if v.hard else 'warn'}] {v.kind}: {v.cuj}: {v.detail}")
    print(f"\n{len(hard)} hard violation(s).")
    return 0 if "--report" in argv else (1 if hard else 0)


if __name__ == "__main__":
    sys.exit(main())
