"""Gitleaks secret-scanning gate (software-factory G3 SECURITY batch, ADR-0072).

HARD gate with TWO legs, scanned against two committed, redacted baselines:

* **committed history** (`gitleaks git .`, baseline `.gitleaks-baseline.json`) — the
  authoritative leg. It scans the whole COMMITTED object store, so a hit here is a
  literal that is *already in a commit*: the fix is to amend/rewrite the offending
  commit(s), not just edit the file.
* **working tree** (`gitleaks dir` over the commit-eligible file set, baseline
  `.gitleaks-worktree-baseline.json`) — a pre-commit convenience leg. It scans the
  files a commit *would* carry (tracked + untracked-not-ignored, per `git ls-files`)
  BEFORE they become commits, so a lane catches a literal it is about to commit while
  the fix is still just editing the file — no history rewrite. This closes the gap
  that let three password/api-key literals ship green (the whole suite runs on an
  UNCOMMITTED tree, which the history leg cannot see) and then force an amend cycle.

Both legs use the same `.gitleaks.toml` and the same new-findings-vs-baseline
discipline; only the scan target and the baseline differ. The working-tree leg scans
a materialized shadow tree of just the commit-eligible files rather than
`gitleaks dir .` over the checkout, because the directory walk reads `.git`, `.venv`,
`node_modules`, build output and untracked local tooling (~300 MB, ~20-30 s) even when
a config allowlist would drop their findings — an allowlist filters findings, it does
not prune the walk. Restricting to `git ls-files` output keeps the scan to a few MB
and a few seconds, and makes it exactly "what is about to be committed".

SECRET SAFETY: both scans run with `--redact=100`, so no secret value is ever written
to a report, a baseline, the logs, or this gate's output — only rule id + file:line.
The repo-root `.env` (holding a live key) is gitignored and never committed, so the
history scan cannot reach it; `.gitleaks.toml` also allowlists `.env`/`.env.*`, and
the working-tree leg drops gitignored files by construction (they are not
commit-eligible).

Fail-closed: if the gitleaks binary is absent this gate ERRORS (exit 2) — it never
soft-passes. Install with `brew install gitleaks` (or a provisioned binary).

    python -m scripts.check_gitleaks            # exit 1 on NEW finding (either leg), 2 if no binary
    python -m scripts.check_gitleaks --report   # print both legs, exit 0 (still 2 if no binary)
    python -m scripts.check_gitleaks --update    # (re)generate BOTH redacted baselines

Refs: ADR-0072
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

CONFIG = ".gitleaks.toml"
BASELINE = pathlib.Path(".gitleaks-baseline.json")
WORKTREE_BASELINE = pathlib.Path(".gitleaks-worktree-baseline.json")

# Distinguishable surface labels so a lane knows instantly which fix applies:
# a history hit needs an amend/rewrite; a working-tree hit is just an edit.
HISTORY_SURFACE = "committed history"
WORKTREE_SURFACE = "working tree"


def _gitleaks_bin() -> str | None:
    return shutil.which("gitleaks")


def _ensure_scan_ok(proc: subprocess.CompletedProcess, report_path: str) -> None:
    """Fail CLOSED on a gitleaks error — never soft-pass a crashed scan as 'no findings'.

    gitleaks is ambiguous by exit code: it uses **1 for BOTH 'leaks found' (normal) AND
    fatal errors** (bad config, unreadable path, panic). But on a fatal error it logs
    `FTL` and writes NO report file, whereas any successful scan (leaks or clean) always
    writes one. So a MISSING report is the reliable crash signal; the exit-code check
    additionally catches panics/signals (exit not in {0,1}). Either way we raise with the
    real stderr rather than let the caller read an absent/partial report as an empty list
    (the fail-open hole: an errored gate would otherwise report the tree secret-free).
    """
    err = proc.stderr.strip()[:300] if proc.stderr else ""
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"gitleaks failed (exit {proc.returncode}): {err}")
    if not pathlib.Path(report_path).exists():
        raise RuntimeError(
            f"gitleaks wrote no report (exit {proc.returncode}) — a fatal error, not a "
            f"clean scan; failing closed: {err}"
        )


def _scan(repo_root: pathlib.Path, report_path: str, use_baseline: bool) -> None:
    """Committed-history leg: scan the git object store."""
    exe = _gitleaks_bin()
    cmd = [
        exe,
        "git",
        ".",
        "--no-banner",
        "--redact=100",
        "--config",
        CONFIG,
        "--report-format",
        "json",
        "--report-path",
        report_path,
    ]
    if use_baseline:
        cmd += ["--baseline-path", str(BASELINE)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
    _ensure_scan_ok(proc, report_path)


def _commit_eligible_files(repo_root: pathlib.Path) -> list[str]:
    """Repo-relative paths a commit would include: tracked + untracked-not-ignored.

    This is exactly `git`'s own view, so gitignored trees (.venv, node_modules, dist,
    .env, nested-gitignored tooling) are excluded by construction — the same set a
    lane is about to commit.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        cwd=repo_root,
        check=True,
    )
    return [f for f in out.stdout.decode("utf-8", "surrogateescape").split("\0") if f]


def _materialize_worktree(repo_root: pathlib.Path, dest: pathlib.Path) -> None:
    """Link (or copy) the commit-eligible files into `dest`, preserving relative paths.

    Hardlinks are near-instant and share inodes; a cross-filesystem temp dir falls
    back to a copy (still cheap — these are source files, not build output). Symlinks
    are skipped, matching `gitleaks dir`'s own default of not following them.
    """
    for rel in _commit_eligible_files(repo_root):
        src = repo_root / rel
        if src.is_symlink() or not src.is_file():
            continue
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copyfile(src, dst)


def _scan_worktree(repo_root: pathlib.Path, report_path: str, use_baseline: bool) -> None:
    """Working-tree leg: scan a shadow tree of the commit-eligible files.

    Runs gitleaks with cwd = the shadow tree and path ".", so finding paths (and hence
    fingerprints) are repo-relative and stable across machines/checkouts — which also
    lets the shared `.gitleaks.toml` path-allowlist match (the baseline JSONs, .env).
    The report is written to an absolute path OUTSIDE the shadow tree so it is neither
    scanned nor lost when the temp dir is cleaned up.
    """
    exe = _gitleaks_bin()
    config_path = repo_root / CONFIG
    report_abs = str(pathlib.Path(report_path).resolve())
    with tempfile.TemporaryDirectory(prefix="gitleaks-worktree-") as td:
        tree = pathlib.Path(td)
        _materialize_worktree(repo_root, tree)
        cmd = [
            exe,
            "dir",
            ".",
            "--no-banner",
            "--redact=100",
            "--report-format",
            "json",
            "--report-path",
            report_abs,
        ]
        if config_path.exists():
            cmd += ["--config", str(config_path.resolve())]
        if use_baseline:
            cmd += ["--baseline-path", str((repo_root / WORKTREE_BASELINE).resolve())]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=tree)
        _ensure_scan_ok(proc, report_abs)


def _new_findings(repo_root: pathlib.Path, baseline: pathlib.Path, scan_fn) -> list[dict]:
    """Redacted findings not covered by `baseline`, produced by `scan_fn`."""
    if not (repo_root / baseline).exists():
        raise SystemExit(
            f"[HARD] {baseline} missing — generate it with "
            "`python -m scripts.check_gitleaks --update` (do NOT skip)."
        )
    with tempfile.TemporaryDirectory() as td:
        report = str(pathlib.Path(td) / "gl.json")
        scan_fn(repo_root, report, True)
        return json.loads(pathlib.Path(report).read_text(encoding="utf-8"))


def new_findings(repo_root: pathlib.Path | None = None) -> list[dict]:
    """Committed-history findings not covered by the committed baseline."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    return _new_findings(repo_root, BASELINE, _scan)


def new_worktree_findings(repo_root: pathlib.Path | None = None) -> list[dict]:
    """Working-tree findings (about-to-be-committed) not covered by the wt baseline."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    return _new_findings(repo_root, WORKTREE_BASELINE, _scan_worktree)


def _render(findings: list[dict], surface: str) -> list[str]:
    """One readable, surface-labelled line per finding (values already redacted)."""
    return [
        f"[HARD][{surface}] {f.get('RuleID')}: {f.get('File')}:{f.get('StartLine')}"
        for f in findings
    ]


def _regenerate_baseline(repo_root: pathlib.Path, baseline: pathlib.Path, scan_fn) -> int:
    with tempfile.TemporaryDirectory() as td:
        report = str(pathlib.Path(td) / "gl.json")
        scan_fn(repo_root, report, False)
        findings = json.loads(pathlib.Path(report).read_text(encoding="utf-8"))
    (repo_root / baseline).write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
    return len(findings)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = pathlib.Path.cwd()

    if _gitleaks_bin() is None:
        print(
            "[HARD] gitleaks binary not found on PATH. This gate does NOT soft-pass.\n"
            "       Install: brew install gitleaks (or drop a provisioned binary on PATH).",
            file=sys.stderr,
        )
        return 2

    if "--update" in argv:
        n_hist = _regenerate_baseline(repo_root, BASELINE, _scan)
        n_wt = _regenerate_baseline(repo_root, WORKTREE_BASELINE, _scan_worktree)
        print(
            f"wrote {BASELINE} ({n_hist} redacted, triaged finding(s)) and "
            f"{WORKTREE_BASELINE} ({n_wt} redacted, triaged finding(s))"
        )
        return 0

    history = new_findings(repo_root)
    worktree = new_worktree_findings(repo_root)
    for line in _render(history, HISTORY_SURFACE):
        print(line)
    for line in _render(worktree, WORKTREE_SURFACE):
        print(line)
    print(
        f"\ngitleaks ({HISTORY_SURFACE}): {len(history)} NEW finding(s) vs baseline "
        "(values redacted) — a hit here is ALREADY COMMITTED; amend/rewrite the commit(s)."
    )
    print(
        f"gitleaks ({WORKTREE_SURFACE}): {len(worktree)} NEW finding(s) vs baseline "
        "(values redacted) — a hit here is UNCOMMITTED; just edit the file before committing."
    )
    total = len(history) + len(worktree)
    return 0 if "--report" in argv else (1 if total else 0)


if __name__ == "__main__":
    sys.exit(main())
