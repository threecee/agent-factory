"""Ungated-module coverage report (software-factory NEXT-tier gap 2, ADR-0089).

Engine Shop's disposability test: if deleting a module silently erases undocumented
intent, the implementation was never disposable. Today intent survives above the code
in exactly two registers: an ADR's `code:` front-matter (scripts/check_traceability.py)
and a feature's `code_globs` pairing (docs/feature-map.yaml, scripts/check_consistency.py).
A module in NEITHER register is UNGATED: its shape is the only place its intent lives,
so deleting it deletes design nobody wrote down anywhere else.

This is a REPORT, not a gate: it never fails the build. It gives the worklist and lets
the ratchet be tracked down over unforced waves (ADR-0089 records wave 1 + the measured
remaining counts). A module is GATED if EITHER register covers it:

  - some ACCEPTED ADR's `code:` front-matter lists the file (reuses
    check_traceability.iter_adr_paths + parse_adr_frontmatter, the same forward
    ADR->code parse check_all validates);
  - some docs/feature-map.yaml feature's `code_globs` matches the file (reuses
    check_consistency.load_feature_map + the same fnmatch matching find_unpaired uses).

Findings are grouped into priority tiers so welfare/egress/custody-critical modules
surface FIRST: the ones where an undocumented deletion would be worst, not just the
alphabetically-first ones.

    python -m scripts.check_module_coverage            # print the grouped report, exit 0
    python -m scripts.check_module_coverage --report    # identical (kept for CLI parity
                                                         # with the other check_* scripts)

Refs: ADR-0089
"""

from __future__ import annotations

import fnmatch
import pathlib
import sys
from typing import NamedTuple

from scripts import check_consistency, check_traceability

SRC_ROOT = "src/kripos"

_PRIORITY_TIERS: tuple[tuple[str, str], ...] = (
    ("welfare (guarded media)", "src/kripos/media/"),
    ("data-hygiene gate (plane4)", "src/kripos/plane4/"),
    ("custody (audit/access log)", "src/kripos/audit/"),
    ("custody (delivery/evidence)", "src/kripos/evidence/"),
    ("custody (ingest intake)", "src/kripos/ingest/"),
    ("custody (case-building)", "src/kripos/event/"),
    ("signal read-model (LEADS)", "src/kripos/signal/"),
    ("egress seam (llm provider)", "src/kripos/llm/"),
    ("egress seam (vision provider)", "src/kripos/vision/"),
    ("egress seam (vlm provider)", "src/kripos/vlm/"),
)
_OTHER_TIER = "other"


class ModuleCoverage(NamedTuple):
    path: str
    gated: bool
    via: tuple[str, ...]


def iter_modules(repo_root: pathlib.Path | None = None, src_root: str = SRC_ROOT) -> list[str]:
    """Every `*.py` module under `src_root`, as repo-relative posix paths."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    root = repo_root / src_root
    if not root.exists():
        return []
    return sorted(p.relative_to(repo_root).as_posix() for p in root.rglob("*.py"))


def adr_gated_files(repo_root: pathlib.Path) -> set[str]:
    """Repo-relative files cited in some ACCEPTED ADR's `code:` front-matter: the
    forward ADR->code pairing (a Superseded/Proposed/Rejected ADR does not gate; only
    a currently-accepted contract counts as live intent above the code)."""
    gated: set[str] = set()
    adr_dir = repo_root / "docs/decisions"
    for path in check_traceability.iter_adr_paths(adr_dir):
        fm = check_traceability.parse_adr_frontmatter(path)
        if not isinstance(fm, dict) or fm.get("status") != "Accepted":
            continue
        for entry in fm.get("code") or []:
            rel = str(entry).partition("::")[0]
            gated.add(rel)
    return gated


def feature_map_gated_files(repo_root: pathlib.Path, modules: list[str]) -> set[str]:
    """Modules matched by some feature's `code_globs` (the same fnmatch pairing
    check_consistency.find_unpaired uses to classify a changed file)."""
    features = check_consistency.load_feature_map(repo_root)
    gated: set[str] = set()
    for feat in features:
        for glob in feat.get("code_globs") or []:
            for module in modules:
                if fnmatch.fnmatch(module, glob):
                    gated.add(module)
    return gated


def _tier(path: str) -> str:
    for name, prefix in _PRIORITY_TIERS:
        if path.startswith(prefix):
            return name
    return _OTHER_TIER


def _tier_rank(name: str) -> int:
    for i, (tier_name, _prefix) in enumerate(_PRIORITY_TIERS):
        if tier_name == name:
            return i
    return len(_PRIORITY_TIERS)


def coverage(
    repo_root: pathlib.Path | None = None, src_root: str = SRC_ROOT
) -> list[ModuleCoverage]:
    """Coverage classification for every module under `src_root`."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    modules = iter_modules(repo_root, src_root)
    adr_gated = adr_gated_files(repo_root)
    fm_gated = feature_map_gated_files(repo_root, modules)
    rows: list[ModuleCoverage] = []
    for module in modules:
        via = tuple(
            label
            for label, gated_set in (("adr", adr_gated), ("feature-map", fm_gated))
            if module in gated_set
        )
        rows.append(ModuleCoverage(module, bool(via), via))
    return rows


def ungated(rows: list[ModuleCoverage]) -> list[ModuleCoverage]:
    return [row for row in rows if not row.gated]


def render_report(rows: list[ModuleCoverage]) -> str:
    un = sorted(ungated(rows), key=lambda row: (_tier_rank(_tier(row.path)), row.path))
    lines: list[str] = []
    current_tier = None
    for row in un:
        tier = _tier(row.path)
        if tier != current_tier:
            lines.append(f"\n-- {tier} --")
            current_tier = tier
        lines.append(f"[UNGATED] {row.path}")
    lines.append(
        f"\nmodule coverage: {len(rows)} module(s) under {SRC_ROOT}, "
        f"{len(rows) - len(un)} gated, {len(un)} ungated."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    del argv
    rows = coverage()
    print(render_report(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
