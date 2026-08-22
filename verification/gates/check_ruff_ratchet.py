"""Ruff lint ratchet (software-factory G3 SECURITY batch, ADR-0072).

Ruff is the repo's first linter, introduced as a RATCHET rather than a big-bang
reformat: the configured ruleset (pyproject `[tool.ruff.lint]`) already produces
findings on the existing tree, so this gate records a committed per-rule-code
baseline (`.ruff-baseline.json`) and fails only when a rule's finding count
INCREASES over baseline (or a new rule code appears). It never runs
`ruff format .` across the tree — formatting is on-touch. A per-rule-code baseline
(not a single total) means removing an unrelated finding cannot mask a new one.

    python -m scripts.check_ruff_ratchet            # exit 1 on any regression
    python -m scripts.check_ruff_ratchet --report   # print, exit 0
    python -m scripts.check_ruff_ratchet --update    # rewrite the baseline

Refs: ADR-0072
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from collections import Counter

TARGETS = ("src", "scripts")
BASELINE = pathlib.Path(".ruff-baseline.json")


def _ruff_bin() -> str:
    """Prefer the ruff installed alongside the running interpreter (the venv)."""
    cand = pathlib.Path(sys.executable).parent / "ruff"
    return str(cand) if cand.exists() else "ruff"


def rule_counts(repo_root: pathlib.Path | None = None) -> dict[str, int]:
    """Return {rule_code: count} for the configured ruleset over TARGETS."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    targets = [t for t in TARGETS if (repo_root / t).exists()]
    proc = subprocess.run(
        [_ruff_bin(), "check", "--output-format", "json", "--no-cache", *targets],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"ruff failed (exit {proc.returncode}): {proc.stderr.strip()[:500]}")
    data = json.loads(proc.stdout or "[]")
    return dict(sorted(Counter(d["code"] for d in data if d.get("code")).items()))


def load_baseline(repo_root: pathlib.Path | None = None) -> dict[str, int]:
    path = (repo_root or pathlib.Path.cwd()) / BASELINE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def regressions(current: dict[str, int], baseline: dict[str, int]) -> list[tuple[str, int, int]]:
    """Rule codes whose count rose above baseline: (code, baseline, current)."""
    out = []
    for code, n in sorted(current.items()):
        base = baseline.get(code, 0)
        if n > base:
            out.append((code, base, n))
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = pathlib.Path.cwd()
    current = rule_counts(repo_root)

    if "--update" in argv:
        (repo_root / BASELINE).write_text(
            json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {BASELINE} ({len(current)} rule codes, {sum(current.values())} findings)")
        return 0

    baseline = load_baseline(repo_root)
    regs = regressions(current, baseline)
    for code, base, n in regs:
        print(f"[RATCHET] {code}: {base} -> {n} (+{n - base}) — fix or run 'ruff check --fix'")
    print(
        f"\nruff ratchet: {sum(current.values())} findings across {len(current)} rules; "
        f"{len(regs)} regression(s) vs baseline."
    )
    return 0 if "--report" in argv else (1 if regs else 0)


if __name__ == "__main__":
    sys.exit(main())
