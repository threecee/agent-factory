"""Static type-judge gate - the mypy two-tier ratchet (ADR-0085, Engine Shop gap 1).

mypy is the repo's first static type checker. It is introduced the same way ruff
was (ADR-0072): as a RATCHET, not a big-bang annotation campaign. The configured
run already produces findings on the untyped tree, so this gate records a committed
per-``(module, error-code)`` baseline (`.mypy-baseline.json`) and fails only when a
code's count INCREASES over baseline for a module (or a new module::code appears).
Per-(module,code) buckets (not one total) mean removing an unrelated error cannot
mask a new one, exactly like the ruff ratchet's per-rule baseline.

Two tiers, one config (`pyproject.toml [tool.mypy]`):

* LENIENT GLOBAL - the whole tree, ratcheted here against the baseline.
* STRICT SEAMS - the load-bearing modules listed under the strict-flag override
  (individual flags, not ``strict = true``, which would leak to the global config).
  Those are held to ZERO mypy errors and are NOT ratcheted: any error
  in a strict seam fails immediately (`--strict-seams`, and a belt check in the
  ratchet run). They are genuinely clean, never baseline-frozen - `--update`
  refuses to write a baseline while any seam has an error.

Redaction / determinism (same spirit as check_ruff_ratchet): the baseline stores
ONLY dotted module names, error codes, and counts - never a source line, an error
message, a file path, or a column. Keys are sorted; the output is stable.

    python -m scripts.check_mypy                 # ratchet + seam belt; exit 1 on regression
    python -m scripts.check_mypy --strict-seams  # strict seams only; exit 1 on ANY seam error
    python -m scripts.check_mypy --report        # print both, exit 0
    python -m scripts.check_mypy --update        # rewrite baseline (refuses if a seam is dirty)

Refs: ADR-0085
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import tempfile
import tomllib
from collections import Counter

TARGETS = ("src/kripos",)
BASELINE = pathlib.Path(".mypy-baseline.json")

_ERROR_RE = re.compile(
    r"^(?P<path>[^:]+\.py):\d+:(?:\d+:)?\s*error:\s.*\[(?P<code>[a-z][a-z0-9-]*)\]\s*$"
)


def _mypy_bin() -> str:
    """Prefer the mypy installed alongside the running interpreter (the venv)."""
    cand = pathlib.Path(sys.executable).parent / "mypy"
    return str(cand) if cand.exists() else "mypy"


def strict_seam_modules(repo_root: pathlib.Path | None = None) -> frozenset[str]:
    """The strict-seam module list - read straight from pyproject `[tool.mypy]`
    overrides so the script and the config can never drift. A module is a strict
    seam iff it appears in an override that enables ``disallow_untyped_defs`` (the
    defining strict flag; we use the individual flags, not ``strict = true``,
    because a per-module ``strict`` leaks to the global config in mypy)."""
    repo_root = repo_root or pathlib.Path.cwd()
    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    overrides = data.get("tool", {}).get("mypy", {}).get("overrides", [])
    seams: set[str] = set()
    for ov in overrides:
        if ov.get("disallow_untyped_defs") is True:
            mod = ov.get("module", [])
            seams.update([mod] if isinstance(mod, str) else mod)
    return frozenset(seams)


def _module_of(path: str) -> str:
    """`src/kripos/signal/trace.py` -> `kripos.signal.trace` (drop a trailing
    `.__init__` so a package's __init__ buckets under the package)."""
    rel = re.sub(r"^(?:\./)?src/", "", path)
    mod = rel.removesuffix(".py").replace("/", ".")
    return mod.removesuffix(".__init__")


def _run_mypy(repo_root: pathlib.Path, targets: tuple[str, ...]) -> str:
    """Run mypy over *targets* with the pyproject config. Deterministic: no
    incremental cache is read or written into the tree (a throwaway cache dir),
    no color/pretty formatting to keep one error per line."""
    with tempfile.TemporaryDirectory(prefix="kripos-mypy-cache-") as cache_dir:
        proc = subprocess.run(
            [
                _mypy_bin(),
                "--no-incremental",
                "--cache-dir",
                cache_dir,
                "--no-color-output",
                "--no-pretty",
                "--no-error-summary",
                "--show-error-codes",
                *targets,
            ],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
    if proc.returncode not in (0, 1):
        raise RuntimeError(
            f"mypy failed (exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()[:500]}"
        )
    return proc.stdout


def _bucket(output: str) -> Counter[str]:
    """Count errors keyed by `module::code` (no messages, no lines - redacted)."""
    counts: Counter[str] = Counter()
    for line in output.splitlines():
        m = _ERROR_RE.match(line)
        if m:
            counts[f"{_module_of(m.group('path'))}::{m.group('code')}"] += 1
    return counts


def collect(
    repo_root: pathlib.Path | None = None,
) -> tuple[dict[str, int], dict[str, int]]:
    """One whole-tree run, partitioned into (strict-seam errors, ratchet errors).

    Seam errors should always be empty (the seams are clean); they are returned
    separately so the caller can hard-fail on them rather than ratchet them."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    seams = strict_seam_modules(repo_root)
    output = _run_mypy(repo_root, tuple(t for t in TARGETS if (repo_root / t).exists()))
    seam_counts: Counter[str] = Counter()
    ratchet_counts: Counter[str] = Counter()
    for key, n in _bucket(output).items():
        module = key.split("::", 1)[0]
        (seam_counts if module in seams else ratchet_counts)[key] += n
    return dict(sorted(seam_counts.items())), dict(sorted(ratchet_counts.items()))


def strict_seam_errors(repo_root: pathlib.Path | None = None) -> dict[str, int]:
    """Independent strict proof: run mypy over ONLY the strict-seam files. With
    `follow_imports = silent`, only the seams' own errors are reported, so a clean
    result is a genuine zero (not a follow-imports artifact). Empty == all clean."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    seams = strict_seam_modules(repo_root)
    files = tuple(
        f"src/{mod.replace('.', '/')}.py"
        for mod in sorted(seams)
        if (repo_root / f"src/{mod.replace('.', '/')}.py").exists()
    )
    if not files:
        return {}
    return dict(sorted(_bucket(_run_mypy(repo_root, files)).items()))


def load_baseline(repo_root: pathlib.Path | None = None) -> dict[str, int]:
    path = (repo_root or pathlib.Path.cwd()) / BASELINE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def regressions(current: dict[str, int], baseline: dict[str, int]) -> list[tuple[str, int, int]]:
    """`module::code` keys whose count rose above baseline: (key, baseline, current)."""
    out = []
    for key, n in sorted(current.items()):
        base = baseline.get(key, 0)
        if n > base:
            out.append((key, base, n))
    return out


def _write_baseline(repo_root: pathlib.Path, ratchet_counts: dict[str, int]) -> None:
    (repo_root / BASELINE).write_text(
        json.dumps(ratchet_counts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _print_seam_errors(seam_counts: dict[str, int]) -> None:
    for key, n in seam_counts.items():
        print(f"[STRICT SEAM] {key}: {n} error(s) - a strict seam must have ZERO. Fix them.")


def _run_strict_seams(repo_root: pathlib.Path, report: bool) -> int:
    seam_errs = strict_seam_errors(repo_root)
    _print_seam_errors(seam_errs)
    print(
        f"\nmypy strict seams: {sum(seam_errs.values())} error(s) "
        f"across {len(seam_errs)} bucket(s)."
    )
    return 0 if report else (1 if seam_errs else 0)


def _run_update(
    repo_root: pathlib.Path, seam_counts: dict[str, int], ratchet: dict[str, int]
) -> int:
    if seam_counts:
        _print_seam_errors(seam_counts)
        print("\nstrict seam(s) not clean; fix them before --update (never freeze-pretend-clean).")
        return 1
    _write_baseline(repo_root, ratchet)
    print(
        f"wrote {BASELINE} ({len(ratchet)} module::code buckets, "
        f"{sum(ratchet.values())} ratchet findings; strict seams clean)"
    )
    return 0


def _run_ratchet(
    repo_root: pathlib.Path, seam_counts: dict[str, int], ratchet: dict[str, int], report: bool
) -> int:
    regs = regressions(ratchet, load_baseline(repo_root))
    _print_seam_errors(seam_counts)
    for key, base, n in regs:
        print(
            f"[RATCHET] {key}: {base} -> {n} (+{n - base}) - annotate the change or fix the type."
        )
    print(
        f"\nmypy ratchet: {sum(ratchet.values())} findings across {len(ratchet)} buckets; "
        f"{len(regs)} regression(s) vs baseline; {sum(seam_counts.values())} strict-seam "
        f"error(s) (must be 0)."
    )
    return 0 if report else (1 if (regs or seam_counts) else 0)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = pathlib.Path.cwd()
    report = "--report" in argv

    if "--strict-seams" in argv:
        return _run_strict_seams(repo_root, report)

    seam_counts, ratchet_counts = collect(repo_root)
    if "--update" in argv:
        return _run_update(repo_root, seam_counts, ratchet_counts)
    return _run_ratchet(repo_root, seam_counts, ratchet_counts, report)


if __name__ == "__main__":
    sys.exit(main())
