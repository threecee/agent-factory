"""Software-composition-analysis gate (G3 SECURITY batch, ADR-0072).

Advisory by design — its own `make check-sca` target, not a `make verify`
prerequisite (can run nightly). Scans `uv.lock` with osv-scanner against a
committed baseline (`.sca-baseline.json`) of the known-existing advisories, and
reports NEW ones. A NEW CRITICAL advisory affecting a RUNTIME dependency (the
pyproject `[project] dependencies` set — not the dev/serve/eval extras) is called
out prominently and makes the gate exit non-zero under `--strict`.

Air-gap: osv-scanner needs a vulnerability database. On the connected dev box it
fetches online; on the air-gapped box run `osv-scanner --offline` against a
mirrored `osv-scanner` DB provisioned before the box is sealed (see ADR-0072).

    python -m scripts.check_sca            # advisory: print + exit 0
    python -m scripts.check_sca --strict   # exit 1 on NEW CRITICAL runtime advisory
    python -m scripts.check_sca --update    # (re)generate the baseline

Refs: ADR-0072
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

LOCKFILE = "uv.lock"
BASELINE = pathlib.Path(".sca-baseline.json")

RUNTIME_DEPS = frozenset(
    {
        "pydantic",
        "anthropic",
        "httpx",
        "fastapi",
        "uvicorn",
        "jinja2",
        "sqlalchemy",
        "alembic",
        "argon2-cffi",
        "argon2_cffi",
        "itsdangerous",
        "python-multipart",
        "python_multipart",
        "pyyaml",
        "defusedxml",
    }
)


def _osv_bin() -> str | None:
    return shutil.which("osv-scanner")


def _severity(vuln: dict) -> str:
    """Best-effort CRITICAL/HIGH/... from an OSV record."""
    db = vuln.get("database_specific", {}) or {}
    if isinstance(db.get("severity"), str):
        return db["severity"].upper()
    best = 0.0
    for sev in vuln.get("severity", []) or []:
        score = str(sev.get("score", ""))
        try:
            best = max(best, float(score))
        except ValueError:
            continue
    if best >= 9.0:
        return "CRITICAL"
    if best >= 7.0:
        return "HIGH"
    return "UNKNOWN" if best == 0.0 else "MODERATE"


def scan(repo_root: pathlib.Path | None = None) -> list[tuple[str, str, str]]:
    """Return sorted unique (package, vuln_id, severity) for the lockfile."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    with tempfile.TemporaryDirectory() as td:
        out = str(pathlib.Path(td) / "osv.json")
        with open(out, "w", encoding="utf-8") as fh:
            subprocess.run(
                [_osv_bin(), "scan", "source", "--lockfile", LOCKFILE, "--format", "json"],
                stdout=fh,
                stderr=subprocess.DEVNULL,
                cwd=repo_root,
            )
        data = json.loads(pathlib.Path(out).read_text(encoding="utf-8") or "{}")
    found: set[tuple[str, str, str]] = set()
    for result in data.get("results", []):
        for pkg in result.get("packages", []):
            name = pkg.get("package", {}).get("name", "")
            for vuln in pkg.get("vulnerabilities", []):
                found.add((name, vuln.get("id", ""), _severity(vuln)))
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = pathlib.Path.cwd()

    if not (repo_root / LOCKFILE).exists():
        print(f"[ADVISORY] no {LOCKFILE} present — SCA needs the lockfile; skipping (advisory).")
        return 0
    if _osv_bin() is None:
        print(
            "[ADVISORY] osv-scanner not installed — SCA skipped (advisory).\n"
            "      Install: brew install osv-scanner. Air-gap: mirror the DB, use --offline."
        )
        return 0

    current = scan(repo_root)

    if "--update" in argv:
        (repo_root / BASELINE).write_text(
            json.dumps([list(a) for a in current], indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {BASELINE} ({len(current)} advisory/ies baselined)")
        return 0

    baseline = set()
    if (repo_root / BASELINE).exists():
        baseline = {
            tuple(a) for a in json.loads((repo_root / BASELINE).read_text(encoding="utf-8"))
        }

    baseline_ids = {(p, i) for p, i, _ in baseline}
    new = [a for a in current if (a[0], a[1]) not in baseline_ids]

    crit_runtime = [
        a
        for a in new
        if a[2] == "CRITICAL"
        and a[0].lower().replace("_", "-") in {d.replace("_", "-") for d in RUNTIME_DEPS}
    ]
    for pkg, vid, sev in new:
        print(f"[NEW] {sev:8} {pkg}: {vid}")
    if crit_runtime:
        print(f"\n*** {len(crit_runtime)} NEW CRITICAL advisory/ies in a RUNTIME dependency:")
        for pkg, vid, _ in crit_runtime:
            print(f"    {pkg}: {vid}")
    print(
        f"\nSCA (advisory): {len(current)} total, {len(new)} new vs baseline, "
        f"{len(crit_runtime)} new-critical-runtime."
    )
    if "--strict" in argv and crit_runtime:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
