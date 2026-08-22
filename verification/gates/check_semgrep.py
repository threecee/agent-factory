"""Semgrep SAST gate with local forensic rules (G3 SECURITY batch, ADR-0072).

Runs the repo-local offline rules in `.semgrep/` over `src/`. Two tiers:

  * HARD families — any finding fails the gate immediately and is never baselined.
    A rule is HARD when its id contains one of `HARD_MARKERS`:
      - parser-safety (`.semgrep/parser-safety.yml`) — untrusted XML must be parsed
        through `kripos.ingest.xml_safe` (defusedxml), never a raw stdlib/lxml parse
        sink (XXE / entity-expansion). Closes design-note hull D.
      - subprocess-timeout (`.semgrep/subprocess-timeout.yml`) — every blocking
        subprocess call in src/ must pass an explicit `timeout=` so a wedged child
        cannot hang the worker forever (the media-timeout hang class, register
        F14/F16). Both are HARD because the tree is already clean; a HARD rule with
        a genuine per-line exception uses `# nosemgrep: <rule-id>`.
  * everything else (e.g. `.semgrep/egress.yml`) — RATCHET. Existing findings are
    fingerprinted into `.semgrep-baseline.json`; the gate fails on a NEW finding.

Offline by construction: local rules only, `--metrics=off`, `--disable-version-check`.

    python -m scripts.check_semgrep            # exit 1 on HARD or NEW ratchet finding
    python -m scripts.check_semgrep --report   # print, exit 0
    python -m scripts.check_semgrep --update    # rewrite the ratchet baseline

Refs: ADR-0072
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

RULES_DIR = ".semgrep"
TARGET = "src"
BASELINE = pathlib.Path(".semgrep-baseline.json")
# A rule id containing any of these markers is HARD (fails immediately, never
# baselined). Keep in sync with the HARD rule files in `.semgrep/`.
HARD_MARKERS = ("parser-safety", "subprocess-timeout")


def _semgrep_bin() -> str:
    cand = pathlib.Path(sys.executable).parent / "semgrep"
    return str(cand) if cand.exists() else "semgrep"


def _fingerprint(result: dict) -> str:
    """Stable id for a finding: rule + file + semgrep's syntactic fingerprint."""
    extra = result.get("extra", {})
    fp = extra.get("fingerprint") or f"{result.get('start', {}).get('line')}"
    return f"{result.get('check_id')}::{result.get('path')}::{fp}"


def _is_hard(result: dict) -> bool:
    check_id = str(result.get("check_id", ""))
    return any(marker in check_id for marker in HARD_MARKERS)


def _isolation_env(repo_root: pathlib.Path) -> dict[str, str]:
    """Build per-worktree Semgrep user dirs so concurrent gate runs never share state.

    SEMGREP_SETTINGS_FILE, SEMGREP_LOG_FILE, and SEMGREP_VERSION_CACHE_PATH isolate
    settings.yml, semgrep.log, and the version cache from the shared ~/.semgrep race
    that forced `make verify` serialization. Operator and CI overrides win, making
    concurrent verifies collision-free by construction.
    """
    repo_root = repo_root.resolve()
    digest = hashlib.sha256(str(repo_root).encode("utf-8")).hexdigest()[:12]
    isolation_dir = pathlib.Path(tempfile.gettempdir()) / f"semgrep-gate-{digest}"
    isolation_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("SEMGREP_SETTINGS_FILE", str(isolation_dir / "settings.yml"))
    env.setdefault("SEMGREP_LOG_FILE", str(isolation_dir / "semgrep.log"))
    env.setdefault("SEMGREP_VERSION_CACHE_PATH", str(isolation_dir / "version"))
    return env


def scan(repo_root: pathlib.Path | None = None) -> list[dict]:
    """All semgrep findings for the local rules over TARGET."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    with tempfile.TemporaryDirectory() as td:
        out = str(pathlib.Path(td) / "semgrep.json")
        proc = subprocess.run(
            [
                _semgrep_bin(),
                "scan",
                "--config",
                RULES_DIR,
                "--metrics=off",
                "--disable-version-check",
                "--json",
                "--output",
                out,
                TARGET,
            ],
            capture_output=True,
            text=True,
            cwd=repo_root,
            env=_isolation_env(repo_root),
        )
        if proc.returncode not in (0, 1):
            err = proc.stderr.strip()[:300]
            raise RuntimeError(f"semgrep failed (exit {proc.returncode}): {err}")
        out_path = pathlib.Path(out)
        if not out_path.exists():
            err = proc.stderr.strip()[:300]
            raise RuntimeError(f"semgrep exited {proc.returncode} but wrote no output file: {err}")
        data = json.loads(out_path.read_text(encoding="utf-8"))
        errors = data.get("errors", [])
        rule_errors = [e for e in errors if e.get("type") == "Rule parse error"]
        if rule_errors:
            msg = str(rule_errors[0].get("message", ""))[:300]
            raise RuntimeError(f"semgrep rule parse error(s): {msg}")
    return data.get("results", [])


def load_baseline(repo_root: pathlib.Path | None = None) -> set[str]:
    path = (repo_root or pathlib.Path.cwd()) / BASELINE
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")))


def classify(results: list[dict], baseline: set[str]) -> tuple[list[dict], list[dict]]:
    """Return (hard_findings, new_ratchet_findings)."""
    hard = [r for r in results if _is_hard(r)]
    new_ratchet = [r for r in results if not _is_hard(r) and _fingerprint(r) not in baseline]
    return hard, new_ratchet


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = pathlib.Path.cwd()
    results = scan(repo_root)

    if "--update" in argv:
        fps = sorted({_fingerprint(r) for r in results if not _is_hard(r)})
        (repo_root / BASELINE).write_text(json.dumps(fps, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {BASELINE} ({len(fps)} ratchet finding(s) baselined)")
        return 0

    hard, new_ratchet = classify(results, load_baseline(repo_root))
    for r in hard:
        loc = f"{r.get('path')}:{r.get('start', {}).get('line')}"
        print(f"[HARD] {r.get('check_id')}: {loc}")
    for r in new_ratchet:
        loc = f"{r.get('path')}:{r.get('start', {}).get('line')}"
        print(f"[RATCHET-NEW] {r.get('check_id')}: {loc}")
    if hard:
        print(
            f"\n*** {len(hard)} HARD finding(s) (parser-safety / subprocess-timeout) — "
            "fix at the source per each message above; never baselined. ***"
        )
    print(f"\nsemgrep: {len(hard)} hard + {len(new_ratchet)} new-ratchet finding(s).")
    return 0 if "--report" in argv else (1 if (hard or new_ratchet) else 0)


if __name__ == "__main__":
    sys.exit(main())
