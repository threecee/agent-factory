"""Machine-checkable ADR<->code traceability gate (software-factory NOW phase).

Parses each ADR's YAML front-matter (the forward link), greps src/ + tests/ for
ADR-NNNN back-refs (the reverse link), and reports drift. See
docs/specs/2026-07-11-software-factory-roadmap.md.
"""

from __future__ import annotations

import pathlib
import re

import yaml

ADR_DIR = pathlib.Path("docs/decisions")
_NON_ADR = {"_TEMPLATE.md", "0000-index.md", "CONSTITUTION.md", "NUMBERS.md", "README.md"}
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

FRONTMATTER_INVALID = object()


def iter_adr_paths(adr_dir: pathlib.Path = ADR_DIR) -> list[pathlib.Path]:
    """All ADR markdown files, excluding template/index/constitution/readme."""
    return sorted(p for p in adr_dir.glob("*.md") if p.name not in _NON_ADR)


def parse_adr_frontmatter(path: pathlib.Path):
    """Return the ADR's YAML front-matter dict, None if there is no `---` block,
    or FRONTMATTER_INVALID if a block is present but not a valid YAML mapping."""
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return FRONTMATTER_INVALID
    return data if isinstance(data, dict) else FRONTMATTER_INVALID


import sys
from typing import NamedTuple

_VALID_STATUS = {"Proposed", "Accepted", "Superseded", "Rejected"}
_BACKREF_RE = re.compile(r"ADR-(\d{3,4})")


class Violation(NamedTuple):
    kind: str
    adr: str
    detail: str
    hard: bool


def _symbol_present(path: pathlib.Path, symbol: str) -> bool:
    """True if `symbol` is defined at module scope: a def/class/async def, OR a
    module-level assignment / annotation (`NAME =` / `NAME:`) — the latter so an
    ADR can anchor a constant or enum member, not only a function/class."""
    sym = re.escape(symbol)
    pat = re.compile(
        rf"^\s*(?:async\s+def|def|class)\s+{sym}\b|^\s*{sym}\s*[:=]",
        re.MULTILINE,
    )
    try:
        return bool(pat.search(path.read_text(encoding="utf-8", errors="ignore")))
    except OSError:
        return False


def anchor_problem(repo_root: pathlib.Path, entry: object) -> tuple[str, str] | None:
    """Validate ONE `path[::symbol]` anchor. Returns (kind, detail), or None if it resolves.

    This is the single definition of what an anchor means in this repo. ADR front-matter
    `code:`/`tests:` entries go through it (check_all, below) and so do docs/BACKLOG.md row
    anchors (scripts/check_backlog.py) — deliberately the same function, not a second parser
    that could drift from this one.
    """
    rel, _, symbol = str(entry).partition("::")
    target = repo_root / rel
    if not target.exists():
        return ("path_missing", f"{entry} (path gone)")
    if symbol and not _symbol_present(target, symbol):
        return ("symbol_missing", f"{entry} (symbol gone)")
    return None


def iter_code_backrefs(
    repo_root: pathlib.Path, bases: tuple[str, ...] = ("src", "tests")
) -> dict[str, list[str]]:
    """Map ADR id -> sorted list of files (in `bases`) citing it."""
    refs: dict[str, set[str]] = {}
    for base in bases:
        root = repo_root / base
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for num in _BACKREF_RE.findall(text):
                adr_id = f"ADR-{int(num):04d}"
                refs.setdefault(adr_id, set()).add(str(py.relative_to(repo_root)))
    return {k: sorted(v) for k, v in refs.items()}


def check_all(repo_root: pathlib.Path | None = None) -> list[Violation]:
    repo_root = repo_root or pathlib.Path.cwd()
    adr_dir = repo_root / "docs/decisions"
    out: list[Violation] = []
    known_ids: set[str] = set()
    seen_ids: dict[str, str] = {}
    fms: dict[str, dict] = {}

    for path in iter_adr_paths(adr_dir):
        fm = parse_adr_frontmatter(path)
        if fm is None:
            out.append(Violation("frontmatter_missing", path.name, "no YAML front-matter", True))
            continue
        if fm is FRONTMATTER_INVALID:
            out.append(
                Violation(
                    "frontmatter_invalid",
                    path.name,
                    "front-matter present but not a valid YAML mapping",
                    True,
                )
            )
            continue
        adr_id = fm.get("id", path.name)

        m_num = re.match(r"(\d{3,4})", path.name)
        if m_num:
            expected = f"ADR-{int(m_num.group(1)):04d}"
            if adr_id != expected:
                out.append(
                    Violation(
                        "id_mismatch",
                        str(adr_id),
                        f"{path.name} declares id={adr_id!r}, expected {expected}",
                        True,
                    )
                )
        if adr_id in seen_ids:
            out.append(
                Violation(
                    "duplicate_id",
                    str(adr_id),
                    f"{path.name} shares id with {seen_ids[adr_id]}",
                    True,
                )
            )
        seen_ids[adr_id] = path.name
        known_ids.add(adr_id)
        fms[adr_id] = fm

        status = fm.get("status")
        if status not in _VALID_STATUS:
            out.append(Violation("status_invalid", adr_id, f"status={status!r}", True))
        if status == "Superseded":
            sb = fm.get("superseded_by")
            if not (isinstance(sb, str) and re.fullmatch(r"ADR-\d{3,4}", sb)):
                out.append(
                    Violation(
                        "superseded_bad_link",
                        adr_id,
                        f"Superseded superseded_by must be an ADR id, got {sb!r}",
                        True,
                    )
                )

        code = fm.get("code") or []
        tests = fm.get("tests") or []
        for entry in [*code, *tests]:
            problem = anchor_problem(repo_root, entry)
            if problem is not None:
                kind, detail = problem
                out.append(Violation(kind, adr_id, detail, True))

        reason = fm.get("no_code_reason")
        reason_ok = bool(reason) and "TODO" not in str(reason).upper()
        if status == "Accepted" and not code and not reason_ok:
            out.append(
                Violation(
                    "incomplete_accepted",
                    adr_id,
                    "Accepted with empty code and no valid no_code_reason "
                    "(empty or a TODO sentinel)",
                    True,
                )
            )

    for adr_id, fm in fms.items():
        if fm.get("status") == "Superseded":
            sb = fm.get("superseded_by")
            if isinstance(sb, str) and re.fullmatch(r"ADR-\d{3,4}", sb) and sb not in known_ids:
                out.append(
                    Violation(
                        "superseded_bad_link", adr_id, f"superseded_by {sb} does not exist", True
                    )
                )

    for adr_id, files in iter_code_backrefs(repo_root, bases=("src",)).items():
        if adr_id not in known_ids:
            out.append(
                Violation(
                    "backref_dangling",
                    adr_id,
                    f"cited by {files[0]} (+{len(files) - 1}) — no such ADR",
                    True,
                )
            )
        elif fms.get(adr_id, {}).get("status") == "Superseded":
            out.append(
                Violation(
                    "backref_superseded",
                    adr_id,
                    f"cited by {files[0]} but ADR is Superseded",
                    False,
                )
            )
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    report_only = "--report" in argv
    violations = check_all()
    hard = [v for v in violations if v.hard]
    for v in violations:
        flag = "HARD" if v.hard else "warn"
        print(f"[{flag}] {v.kind}: {v.adr}: {v.detail}")
    print(f"\n{len(hard)} hard / {len(violations) - len(hard)} warn violation(s).")
    return 0 if report_only else (1 if hard else 0)


_TRAILER_RE = re.compile(r"^Refs:\s*(.+)$", re.MULTILINE)


def refs_trailers(commit_message: str) -> list[str]:
    ids: list[str] = []
    for line in _TRAILER_RE.findall(commit_message):
        ids.extend(re.findall(r"ADR-\d{3,4}", line))
    return ids


def warn_missing_trailers(repo_root: pathlib.Path | None = None, base_ref: str = "main") -> int:
    """Print a warning for each commit in base_ref..HEAD that touches src/ but
    carries no `Refs: ADR-xxxx` trailer. Non-failing — returns the warn count."""
    import subprocess

    repo_root = repo_root or pathlib.Path.cwd()

    def _run(*args: str):
        return subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True)

    rv = _run("rev-list", f"{base_ref}..HEAD")
    if rv.returncode != 0:
        print(f"[warn] could not resolve base ref {base_ref!r} — trailer scan skipped")
        return 0

    missing = 0
    for sha in rv.stdout.split():
        files = _run("diff-tree", "--no-commit-id", "--name-only", "-r", sha).stdout
        if not any(line.startswith("src/") for line in files.splitlines()):
            continue
        if not refs_trailers(_run("log", "-1", "--format=%B", sha).stdout):
            print(f"[warn] {sha[:8]} touches src/ but has no 'Refs: ADR-xxxx' trailer")
            missing += 1
    return missing


def _main_trailers() -> int:
    warn_missing_trailers()
    return 0


if __name__ == "__main__":
    sys.exit(_main_trailers() if "--trailers" in sys.argv[1:] else main())
