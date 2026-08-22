"""Bandit Python SAST gate (software-factory G3 SECURITY batch, ADR-0072).

Runs bandit over `src/` (config in pyproject `[tool.bandit]`) against a committed
baseline (`.bandit-baseline.json`). The baseline holds the existing, triaged
findings (see ADR-0072 — the HIGH-severity set is all md5 content-addressing for
the forensic hashset / media identity, not security hashing); the gate fails only
on NEW findings, and calls out any NEW HIGH-severity finding prominently.

    python -m scripts.check_bandit            # exit 1 on any NEW finding
    python -m scripts.check_bandit --report   # print, exit 0
    python -m scripts.check_bandit --update    # (re)generate the baseline

Refs: ADR-0072
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

TARGET = "src"
CONFIG = "pyproject.toml"
BASELINE = pathlib.Path(".bandit-baseline.json")


def _bandit_bin() -> str:
    cand = pathlib.Path(sys.executable).parent / "bandit"
    return str(cand) if cand.exists() else "bandit"


def _run_bandit(repo_root: pathlib.Path, out_path: str, baseline: str | None) -> int:
    cmd = [
        _bandit_bin(),
        "-r",
        TARGET,
        "-c",
        CONFIG,
        "-q",
        "-f",
        "json",
        "-o",
        out_path,
    ]
    if baseline:
        cmd += ["-b", baseline]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
    if proc.returncode == 2:
        raise RuntimeError(f"bandit usage error: {proc.stderr.strip()[:500]}")
    return proc.returncode


def new_findings(repo_root: pathlib.Path | None = None) -> list[dict]:
    """Findings not present in the committed baseline (bandit `-b`)."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    base = repo_root / BASELINE
    if not base.exists():
        raise SystemExit(
            f"[HARD] {BASELINE} missing — generate it with "
            "`python -m scripts.check_bandit --update` (do NOT skip)."
        )
    with tempfile.TemporaryDirectory() as td:
        out = str(pathlib.Path(td) / "bandit.json")
        _run_bandit(repo_root, out, str(base))
        data = json.loads(pathlib.Path(out).read_text(encoding="utf-8"))
    return data.get("results", [])


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = pathlib.Path.cwd()

    if "--update" in argv:
        _run_bandit(repo_root, str(repo_root / BASELINE), None)
        data = json.loads((repo_root / BASELINE).read_text(encoding="utf-8"))
        print(f"wrote {BASELINE} ({len(data.get('results', []))} baselined finding(s))")
        return 0

    results = new_findings(repo_root)
    highs = [r for r in results if r.get("issue_severity") == "HIGH"]
    for r in results:
        loc = f"{r.get('filename')}:{r.get('line_number')}"
        print(f"[{r.get('issue_severity')}] {r.get('test_id')} {r.get('test_name')}: {loc}")
    if highs:
        print(f"\n*** {len(highs)} NEW HIGH-severity finding(s) — review before merge. ***")
    print(f"\nbandit: {len(results)} NEW finding(s) vs baseline.")
    return 0 if "--report" in argv else (1 if results else 0)


if __name__ == "__main__":
    sys.exit(main())
