"""Test-estate health scoreboard (software-factory advisory).

Measures the current test-coverage dimensions by composing the repository's
existing gate logic with deterministic static source counts. This is a REPORT,
not a gate: findings never fail the build, and only an internal analysis error
returns non-zero.

    python -m scripts.check_test_health
    python -m scripts.check_test_health --json
    python -m scripts.check_test_health --out path/to/scoreboard.json
    python -m scripts.check_test_health --report

Refs: ADR-0089, ADR-0063.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from collections.abc import Sequence
from typing import Any

from scripts import check_module_coverage, check_story_coverage, check_traceability

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in environments without PyYAML
    yaml = None

SCHEMA = "kripos-test-health/v1"
DIMENSIONS = [
    "spec",
    "functional",
    "ux",
    "semantic_quality",
    "disposability",
    "security",
    "performance",
    "discipline",
]
BASE_NOTES = [
    "Advisory / report-only: never fails the build (RÅD contract). Exit 2 only on internal error.",
    "Existence-based coverage: a link/marker proves a citing test EXISTS, not that it "
    "semantically asserts the behavior.",
    "Static source counts; the executed test count is higher than "
    "backend_test_functions because of parametrization.",
]
SECURITY_SCRIPTS = [
    "check_gitleaks.py",
    "check_semgrep.py",
    "check_bandit.py",
    "check_sca.py",
    "check_egress.py",
]
INSTRUMENT_NAMES = (
    "instruction-ablation",
    "recalibration",
    "definition-dominance",
    "step5",
)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
TEST_FUNCTION_RE = re.compile(r"^\s*(?:async\s+)?def test_", re.MULTILINE)
FRONTEND_CASE_RE = re.compile(r"\b(?:it|test)\s*\(")
GOAL_RE = re.compile(r"=\s*Goal\(")
PERSONA_ID_RE = re.compile(r"persona_id=([A-Z_]+)")
PERSONA_FALLBACK_RE = re.compile(r"=\s*Persona\(")


def _record(
    metric_id: str,
    value: int | str | None | dict[str, int],
    means: str,
    blind_spot: str,
) -> dict[str, Any]:
    """Build one report-only scoreboard record."""
    return {
        "metric_id": metric_id,
        "dimension": metric_id.split(".", maxsplit=1)[0],
        "value": value,
        "mode": "report_only",
        "means": means,
        "blind_spot": blind_spot,
    }


def _base_commit(repo_root: pathlib.Path) -> str:
    """Return the checked-out commit without making git availability mandatory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _python_test_files(repo_root: pathlib.Path) -> list[pathlib.Path]:
    tests = repo_root / "tests"
    if not tests.exists():
        return []
    return sorted(path for path in tests.rglob("test_*.py") if path.is_file())


def _frontend_test_files(repo_root: pathlib.Path) -> list[pathlib.Path]:
    root = repo_root / "frontend/src"
    if not root.exists():
        return []
    candidates = [*root.rglob("*.test.ts"), *root.rglob("*.test.tsx")]
    return sorted(
        path for path in candidates if path.is_file() and "node_modules" not in path.parts
    )


def _count_matches(paths: Sequence[pathlib.Path], pattern: re.Pattern[str]) -> int:
    return sum(
        len(pattern.findall(path.read_text(encoding="utf-8", errors="ignore")))
        for path in sorted(paths)
    )


def _gate_names(repo_root: pathlib.Path) -> frozenset[str]:
    """Gate stems from scripts/check_*.py (e.g. 'backlog', 'reachability')."""
    scripts = repo_root / "scripts"
    if not scripts.exists():
        return frozenset()
    return frozenset(path.stem[len("check_") :] for path in sorted(scripts.glob("check_*.py")))


def _teeth_stem_candidates(gate: str) -> frozenset[str]:
    """The test-file stems that count as a teeth test for gate ``gate``.

    Gate self-tests are named by several conventions in this repo (test_check_X,
    test_X, test_X_gate, ...), so a single naming rule would badly undercount.
    """
    return frozenset(
        {
            f"test_check_{gate}",
            f"test_{gate}",
            f"test_{gate}_gate",
            f"test_{gate}s",
            f"test_{gate}_check",
        }
    )


def _teeth_stems(gate_names: frozenset[str]) -> frozenset[str]:
    """Every test stem that maps to some gate (used to bucket gate-teeth files)."""
    stems: set[str] = set()
    for gate in gate_names:
        stems |= _teeth_stem_candidates(gate)
    return frozenset(stems)


def _gates_with_teeth(gate_names: frozenset[str], backend_stems: frozenset[str]) -> int:
    """How many gate scripts have at least one conventionally-named teeth test."""
    return sum(1 for gate in gate_names if _teeth_stem_candidates(gate) & backend_stems)


def _backend_bucket(
    path: pathlib.Path, repo_root: pathlib.Path, teeth_stems: frozenset[str]
) -> str:
    relative = path.relative_to(repo_root).as_posix()
    name = path.name
    stem = path.stem
    if "tests/scenarios/uxeval/" in relative:
        return "persona-uxeval"
    if "tests/scenarios/" in relative:
        return "journey-scenario"
    if re.fullmatch(r"test_check_.*\.py", name) or stem in teeth_stems:
        return "gate-teeth"
    eval_patterns = (
        r"test_semantic_.*",
        r"test_instruction_ablation.*",
        r"test_definition_dominance.*",
        r"test_concept_leakage.*",
        r"test_incident_partition.*",
        r"test_label_validity.*",
        r"test_embed_.*",
        r"test_calibration.*",
    )
    if any(re.fullmatch(pattern, stem) for pattern in eval_patterns):
        return "eval-instrument"
    if (
        re.fullmatch(r"test_api_.*\.py", name)
        or re.fullmatch(r"test_.*_api\.py", name)
        or "_api_v1" in name
    ):
        return "route-api"
    return "unit"


def _backend_buckets(
    paths: Sequence[pathlib.Path], repo_root: pathlib.Path, teeth_stems: frozenset[str]
) -> dict[str, int]:
    bucket_names = [
        "persona-uxeval",
        "journey-scenario",
        "gate-teeth",
        "eval-instrument",
        "route-api",
        "unit",
    ]
    counts = {name: 0 for name in bucket_names}
    for path in sorted(paths):
        counts[_backend_bucket(path, repo_root, teeth_stems)] += 1
    return counts


def _accepted_adr_counts(repo_root: pathlib.Path) -> tuple[int, int]:
    with_code = 0
    with_tests = 0
    adr_dir = repo_root / "docs/decisions"
    for path in check_traceability.iter_adr_paths(adr_dir):
        frontmatter = check_traceability.parse_adr_frontmatter(path)
        if not isinstance(frontmatter, dict) or frontmatter.get("status") != "Accepted":
            continue
        with_code += int(bool(frontmatter.get("code")))
        with_tests += int(bool(frontmatter.get("tests")))
    return with_code, with_tests


def _persona_counts(repo_root: pathlib.Path) -> tuple[int, int]:
    path = repo_root / "tests/scenarios/uxeval/personas.py"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    persona_ids = sorted(set(PERSONA_ID_RE.findall(text)))
    personas = len(persona_ids) if persona_ids else len(PERSONA_FALLBACK_RE.findall(text))
    return personas, len(GOAL_RE.findall(text))


def _feature_map_goal_count(repo_root: pathlib.Path, notes: list[str]) -> int | None:
    if yaml is None:
        notes.append("docs/feature-map.yaml was not measured because PyYAML is unavailable.")
        return None
    path = repo_root / "docs/feature-map.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    features = data.get("features", []) if isinstance(data, dict) else []
    goals = {
        str(goal)
        for feature in features
        if isinstance(feature, dict)
        for goal in (feature.get("cuj_goals") or [])
    }
    return len(sorted(goals))


def _newest_named_date(root: pathlib.Path, required_fragments: Sequence[str]) -> str | None:
    if not root.exists():
        return None
    dates: list[str] = []
    for path in sorted(item for item in root.iterdir() if item.is_dir()):
        if not any(fragment in path.name for fragment in required_fragments):
            continue
        dates.extend(DATE_RE.findall(path.name))
    return max(sorted(dates), default=None)


def _eval_instrument_dirs(repo_root: pathlib.Path) -> int:
    root = repo_root / "eval"
    if not root.exists():
        return 0
    directories = [
        path
        for path in sorted(item for item in root.iterdir() if item.is_dir())
        if any(candidate.is_file() for candidate in sorted(path.glob("run_*.py")))
    ]
    return len(directories)


def _undriven_baseline(repo_root: pathlib.Path, notes: list[str]) -> int | None:
    path = repo_root / "reachability-baseline.json"
    if not path.exists():
        notes.append(
            "reachability-baseline.json is missing; undriven producer coverage is unmeasured."
        )
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    producers = data.get("undriven_producers", [])
    return len(sorted(producers))


def _security_scripts_present(repo_root: pathlib.Path) -> list[str]:
    """Security gate scripts that actually exist under scripts/, sorted."""
    return sorted(name for name in SECURITY_SCRIPTS if (repo_root / "scripts" / name).exists())


def _threaded_covered(threaded: Sequence[str], refs: dict[str, list[str]]) -> int:
    """Threaded CUJs that carry at least one Story marker."""
    return sum(1 for cuj in threaded if cuj in refs)


def _dangling_story_count(story_violations: Sequence[Any]) -> int:
    """Story markers that cite no canonical CUJ."""
    return sum(1 for violation in story_violations if violation.kind == "story_dangling")


def _gated_module_count(module_rows: Sequence[Any]) -> int:
    """Modules with ADR or feature-map intent coverage."""
    return sum(1 for row in module_rows if row.gated)


def build_scoreboard(repo_root: pathlib.Path | None = None) -> dict[str, Any]:
    """Collect the advisory scoreboard for ``repo_root``."""
    root = (repo_root or pathlib.Path.cwd()).resolve()
    notes = list(BASE_NOTES)
    backend_files = _python_test_files(root)
    frontend_files = _frontend_test_files(root)
    backend_stems = frozenset(path.stem for path in backend_files)
    gate_names = _gate_names(root)
    teeth_stems = _teeth_stems(gate_names)
    buckets = _backend_buckets(backend_files, root, teeth_stems)
    gate_teeth = buckets["gate-teeth"]
    gates_with_teeth = _gates_with_teeth(gate_names, backend_stems)
    adr_code, adr_tests = _accepted_adr_counts(root)
    traceability_violations = sorted(check_traceability.check_all(root))
    canonical = sorted(check_story_coverage.canonical_cujs(root))
    refs = check_story_coverage.story_refs(root)
    story_violations = sorted(check_story_coverage.check_story_coverage(root))
    threaded = sorted(check_story_coverage.THREADED_CUJS)
    module_rows = sorted(check_module_coverage.coverage(root), key=lambda row: row.path)
    ungated_rows = sorted(check_module_coverage.ungated(module_rows), key=lambda row: row.path)
    personas, persona_goals = _persona_counts(root)
    present_security = _security_scripts_present(root)
    records = [
        _record(
            "spec.adr_traceability_violations",
            len(traceability_violations),
            "Violations reported by the shared forward-and-reverse ADR traceability gate.",
            "Resolved references can still point at tests that do not meaningfully assert the ADR.",
        ),
        _record(
            "spec.adrs_with_code_frontmatter",
            adr_code,
            "Accepted ADRs carrying a non-empty code frontmatter list.",
            "A code anchor proves declared linkage, not that the implementation conforms.",
        ),
        _record(
            "spec.adrs_with_tests_frontmatter",
            adr_tests,
            "Accepted ADRs carrying a non-empty tests frontmatter list.",
            "A test anchor proves a test exists, not that its assertions are sufficient.",
        ),
        _record(
            "spec.cuj_threaded_total",
            len(threaded),
            "CUJs currently included in the shared threaded-CUJ coverage set.",
            "The total excludes canonical CUJs that have not yet joined the coverage ratchet.",
        ),
        _record(
            "spec.cuj_threaded_covered",
            _threaded_covered(threaded, refs),
            "Threaded CUJs with at least one Story marker in the shared story-reference index.",
            "A Story marker cannot show whether the cited test genuinely completes the journey.",
        ),
        _record(
            "spec.cuj_dangling",
            _dangling_story_count(story_violations),
            "Story markers that cite no canonical CUJ according to the shared coverage gate.",
            "This does not identify canonical CUJs that remain intentionally unthreaded.",
        ),
        _record(
            "spec.cuj_canonical_total",
            len(canonical),
            "Canonical CUJ identifiers parsed by the shared story-coverage logic.",
            "A documented CUJ can still be ambiguous, incomplete, or obsolete.",
        ),
        _record(
            "functional.backend_test_files",
            len(backend_files),
            "Static count of tests/**/*.py files named test_*.py.",
            "File count does not measure executed cases, assertion quality, or parametrization.",
        ),
        _record(
            "functional.backend_test_functions",
            _count_matches(backend_files, TEST_FUNCTION_RE),
            "Static count of backend source lines defining test_ functions.",
            "Parametrized cases and dynamically generated tests are not expanded.",
        ),
        _record(
            "functional.frontend_test_files",
            len(frontend_files),
            "Static count of frontend .test.ts and .test.tsx files outside node_modules.",
            "This does not show whether the frontend tests execute successfully.",
        ),
        _record(
            "functional.frontend_test_cases",
            _count_matches(frontend_files, FRONTEND_CASE_RE),
            "Static count of it(...) and test(...) occurrences in frontend test sources.",
            "Textual matches can include skipped, nested, or non-executed declarations.",
        ),
        _record(
            "functional.backend_by_bucket",
            buckets,
            "Every backend test file classified once by the ordered test-estate taxonomy.",
            "Path-based buckets describe intent heuristically and cannot inspect test semantics.",
        ),
        _record(
            "functional.gate_teeth_files",
            gate_teeth,
            "Backend test files that map to a scripts/check_*.py gate by naming convention.",
            "The naming heuristic misses gate tests under unconventional names, "
            "and does not check assertions.",
        ),
        _record(
            "ux.personas",
            personas,
            "Distinct persona_id tokens referenced by goals, with Persona declarations "
            "as fallback.",
            "Static persona presence does not show that each persona has been run or evaluated.",
        ),
        _record(
            "ux.persona_goals",
            persona_goals,
            "Static count of Goal(...) assignments in the UX-evaluation personas source.",
            "Goal count does not measure goal quality, execution, or successful completion.",
        ),
        _record(
            "ux.persona_goals_registered_in_feature_map",
            _feature_map_goal_count(root, notes),
            "Unique cuj_goals entries registered across docs/feature-map.yaml features.",
            "Registration does not prove a feature actually supports or has exercised the goal.",
        ),
        _record(
            "ux.persona_eval_last_run",
            _newest_named_date(root / "docs/research", ("uxeval",)),
            "Newest ISO date encoded in a docs/research directory name containing uxeval.",
            "A dated directory name does not prove the run completed or its findings "
            "were adjudicated.",
        ),
        _record(
            "semantic_quality.eval_instrument_dirs",
            _eval_instrument_dirs(root),
            "Immediate eval subdirectories containing at least one run_*.py instrument.",
            "Instrument presence does not prove recent execution, valid receipts, or "
            "useful sensitivity.",
        ),
        _record(
            "semantic_quality.last_receipt",
            _newest_named_date(root / "docs/research", INSTRUMENT_NAMES),
            "Newest ISO date encoded in a research directory named for a semantic instrument run.",
            "Name-derived recency cannot validate receipt contents or reproduce the result.",
        ),
        _record(
            "disposability.modules_total",
            len(module_rows),
            "Python modules classified by the shared module-intent coverage report.",
            "Module enumeration does not say whether module boundaries are well designed.",
        ),
        _record(
            "disposability.modules_gated",
            _gated_module_count(module_rows),
            "Modules linked to intent through an ADR or feature-map path by shared coverage logic.",
            "An intent link does not prove the module is safe to replace or delete.",
        ),
        _record(
            "disposability.modules_ungated",
            len(ungated_rows),
            "Modules lacking ADR or feature-map intent coverage according to shared logic.",
            "Ungated status cannot distinguish undocumented intent from deliberately "
            "disposable code.",
        ),
        _record(
            "disposability.undriven_producers_baseline",
            _undriven_baseline(root, notes),
            "Undriven module::symbol entries recorded in the reachability baseline.",
            "The syntactic baseline cannot resolve dynamic dispatch, registries, or "
            "framework entrypoints.",
        ),
        _record(
            "security.gate_legs",
            len(present_security),
            f"Existing security gate scripts: {', '.join(present_security) or 'none'}.",
            "Script presence does not prove current execution, configuration quality, or "
            "finding coverage.",
        ),
        _record(
            "performance.systematic_load_tests",
            0,
            "No systematic load/latency/throughput regression testing exists in this repo.",
            "Performance is entirely unmeasured; this is the estate's largest coverage gap.",
        ),
        _record(
            "discipline.gate_scripts_total",
            len(gate_names),
            "Gate scripts under scripts/check_*.py — the population that should have teeth tests.",
            "The count treats every check_* script as a gate, including advisory/report-only ones.",
        ),
        _record(
            "discipline.gate_scripts_with_teeth_test",
            gates_with_teeth,
            "Gate scripts with a conventionally-named backend teeth test (falsification coverage).",
            "Name-matching cannot see a teeth test under an unconventional name, "
            "nor judge its assertions.",
        ),
        _record(
            "discipline.gate_teeth_files",
            gate_teeth,
            "Backend test files bucketed as gate-teeth (map to a scripts/check_*.py gate).",
            "A mapped file is not proof every failure branch of the gate "
            "is asserted with a message.",
        ),
    ]
    return {
        "schema": SCHEMA,
        "base_commit": _base_commit(root),
        "advisory": True,
        "dimensions": DIMENSIONS,
        "records": records,
        "notes": notes,
    }


def render_summary(scoreboard: dict[str, Any]) -> str:
    """Render the human-readable scoreboard grouped in declared dimension order."""
    lines = ["TEST HEALTH SCOREBOARD (RÅD / REPORT-ONLY)"]
    records = scoreboard["records"]
    for dimension in scoreboard["dimensions"]:
        lines.append(f"\n{dimension.upper()}")
        for record in records:
            if record["dimension"] != dimension:
                continue
            value = record["value"]
            rendered = (
                json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                if isinstance(value, dict)
                else json.dumps(value, ensure_ascii=False)
            )
            lines.append(f"  {record['metric_id']} = {rendered}")
    lines.append("\nBLIND SPOTS")
    blind_spots = sorted({record["blind_spot"] for record in records})
    lines.extend(f"  - {blind_spot}" for blind_spot in blind_spots)
    lines.append(
        "\nPERFORMANCE: no systematic load/latency testing exists "
        "(systematic_load_tests=0) — the largest coverage gap."
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print scoreboard JSON")
    parser.add_argument("--out", type=pathlib.Path, help="also write scoreboard JSON")
    parser.add_argument("--report", action="store_true", help="force advisory exit 0")
    parser.add_argument("--repo-root", type=pathlib.Path, default=pathlib.Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the advisory CLI; return 2 only for an unexpected analysis error."""
    try:
        args = _parser().parse_args(argv)
        scoreboard = build_scoreboard(args.repo_root)
        encoded = json.dumps(scoreboard, indent=2, sort_keys=False, ensure_ascii=False)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(f"{encoded}\n", encoding="utf-8")
        print(encoded if args.json else render_summary(scoreboard))
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
