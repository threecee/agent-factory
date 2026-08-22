"""G1 consistency-sync gate (software-factory NOW batch, ADR-0073 + ADR-0079).

A product diff must move its PAIRED ARTIFACTS with it: the demo script
(demo/script.md), the uxeval CUJ goals
(tests/scenarios/uxeval/personas.py), the in-app help (the `#sek-*` sections in
docs_routes.py that the React /hjelp surface renders, tour steps in
TourContext.tsx), the synthetic demo seed
(src/kripos/demo/seed.py), and, per ADR-0079, entrypoint docs (repo-relative
paths in a feature's ``docs`` leg, e.g. docs/ARCHITECTURE.md for the
model-provider wiring). The pairing lives in docs/feature-map.yaml: each
feature = {code_globs, demo_beats, cuj_goals, help_anchors, seed_functions,
docs}.

For every feature whose code_globs match a file changed in the diff range, the
gate requires that at least one paired artifact file ALSO changed in the range,
or that docs/feature-map.yaml itself was tended, or that a commit in the range
carries the audited waiver trailer:

    Consistency: n/a - <reason>

ADVISORY by default while the map matures (findings print, exit 0); flip to
HARD with --hard or CHECK_CONSISTENCY_HARD=1 (ADR-0073 records the plan).
The map itself is validated on every run (and by the anti-drift test in
tests/test_consistency_gates.py): a referenced beat id, goal id, help anchor or
seed function that no longer exists is a config error (exit 2), so the map
cannot rot silently.

Diff range: first positional arg or CHECK_CONSISTENCY_RANGE, default
origin/main...HEAD. On main/master with no explicit range the gate checks the
HEAD commit against its parent, or exits 0 with a note on a rootless/shallow
tree.

    python -m scripts.check_consistency                 # advisory, exit 0
    python -m scripts.check_consistency --hard          # exit 1 on findings
    python -m scripts.check_consistency main...HEAD     # explicit range
"""

from __future__ import annotations

import ast
import fnmatch
import os
import pathlib
import re
import subprocess
import sys
from typing import NamedTuple

import yaml

FEATURE_MAP = pathlib.Path("docs/feature-map.yaml")
DEMO_DIR = pathlib.Path("demo")
PERSONAS_FILE = pathlib.Path("tests/scenarios/uxeval/personas.py")
# The LIVE source of the `#sek-*` in-app help sections. HELPNAV retired the
# server-rendered `/docs-ui` Jinja page to a 303 -> the React `/hjelp` surface, which
# renders the sections `help_sections` composes from `INTRO_SECTIONS` here. The
# `docs_ui.html#` prefix in feature-map.yaml is kept as the (historically named)
# in-app-help SCHEME, but it must resolve against the source actually rendered:
# validating against the now-unrendered template let a renamed live anchor pass.
HELP_SOURCE_FILE = pathlib.Path("src/kripos/web/docs_routes.py")
TOUR_FILE = pathlib.Path("frontend/src/shell/TourContext.tsx")
SEED_FILE = pathlib.Path("src/kripos/demo/seed.py")

DEFAULT_RANGE = "origin/main...HEAD"
RANGE_ENV = "CHECK_CONSISTENCY_RANGE"
HARD_ENV = "CHECK_CONSISTENCY_HARD"

_WAIVER_RE = re.compile(r"^Consistency:\s*n/a\s*[-–—]\s*\S.*$", re.MULTILINE)

_GOAL_ID_RE = re.compile(r"Goal\(\s*id=\"([A-Za-z0-9-]+)\"")


class ConsistencyFinding(NamedTuple):
    feature: str
    matched_glob: str
    changed_file: str
    missing: list[str]


def load_feature_map(repo_root: pathlib.Path) -> list[dict]:
    doc = yaml.safe_load((repo_root / FEATURE_MAP).read_text(encoding="utf-8"))
    features = doc.get("features") if isinstance(doc, dict) else None
    if not isinstance(features, list) or not features:
        raise ValueError(f"{FEATURE_MAP}: expected a non-empty top-level 'features' list")
    return features


def _seed_function_names(repo_root: pathlib.Path) -> set[str]:
    tree = ast.parse((repo_root / SEED_FILE).read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _goal_ids(repo_root: pathlib.Path) -> set[str]:
    return set(_GOAL_ID_RE.findall((repo_root / PERSONAS_FILE).read_text(encoding="utf-8")))


def _is_intro_sections(node: ast.stmt) -> bool:
    target: ast.expr | None = node.target if isinstance(node, ast.AnnAssign) else None
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
    return isinstance(target, ast.Name) and target.id == "INTRO_SECTIONS"


def _anchor_of(section: ast.Dict) -> str | None:
    """The ``"anchor"`` string of one section-dict literal, if it has one."""
    for key, val in zip(section.keys, section.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == "anchor":
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                return val.value
    return None


def _help_anchor_ids(repo_root: pathlib.Path) -> set[str]:
    """The `#sek-*` anchors of the LIVE help intro sections: the ``INTRO_SECTIONS``
    list literal in HELP_SOURCE_FILE, which ``help_sections`` serves to the React
    `/hjelp` surface. Parsed, not imported, so the gate stays import-free."""
    tree = ast.parse((repo_root / HELP_SOURCE_FILE).read_text(encoding="utf-8"))
    node = next((n for n in tree.body if _is_intro_sections(n)), None)
    value = getattr(node, "value", None)
    if value is None:
        return set()
    found = {_anchor_of(d) for d in ast.walk(value) if isinstance(d, ast.Dict)}
    return {a for a in found if a}


def _validate_globs(repo_root: pathlib.Path, fid: str, feat: dict) -> list[str]:
    globs = feat.get("code_globs") or []
    problems = [] if globs else [f"{fid}: no code_globs"]
    for g in globs:
        if not _glob_matches_anything(repo_root, g):
            problems.append(f"{fid}: code_glob {g!r} matches no file in the tree")
    return problems


def _validate_beats(repo_root: pathlib.Path, fid: str, feat: dict) -> list[str]:
    problems: list[str] = []
    for beat in feat.get("demo_beats") or []:
        script, _, beat_id = str(beat).partition("#")
        path = repo_root / DEMO_DIR / script
        if not beat_id or not path.is_file():
            problems.append(f"{fid}: demo beat {beat!r} has no script file demo/{script}")
            continue
        text = path.read_text(encoding="utf-8")
        if not re.search(rf"^## {re.escape(beat_id)} ·", text, re.MULTILINE):
            problems.append(f"{fid}: beat {beat_id!r} not found in demo/{script}")
    return problems


def _validate_docs(repo_root: pathlib.Path, fid: str, feat: dict) -> list[str]:
    """Every paired doc must be a real repo file (anti-drift, mirrors the other
    legs): a renamed/removed entrypoint doc is a config error, never a silent
    no-op pairing."""
    return [
        f"{fid}: paired doc {doc!r} is not a file in the tree"
        for doc in feat.get("docs") or []
        if not (repo_root / str(doc)).is_file()
    ]


def _validate_anchors(repo_root: pathlib.Path, fid: str, feat: dict) -> list[str]:
    help_anchors = _help_anchor_ids(repo_root)
    tour = (repo_root / TOUR_FILE).read_text(encoding="utf-8")
    problems: list[str] = []
    for anchor in feat.get("help_anchors") or []:
        anchor = str(anchor)
        if anchor.startswith("docs_ui.html#"):
            sek = anchor.split("#", 1)[1]
            if sek not in help_anchors:
                problems.append(f"{fid}: help anchor {sek!r} not in {HELP_SOURCE_FILE}")
        elif anchor.startswith("tour:"):
            tittel = anchor.split(":", 1)[1]
            if f'tittel: "{tittel}"' not in tour:
                problems.append(f"{fid}: tour step {tittel!r} not in {TOUR_FILE}")
        else:
            problems.append(
                f"{fid}: help anchor {anchor!r} must start with 'docs_ui.html#' or 'tour:'"
            )
    return problems


def validate_feature_map(repo_root: pathlib.Path | None = None) -> list[str]:
    """Anti-drift check for the map itself: every referenced artifact id must
    exist in its target file. Returns human-readable problems (empty = valid)."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    problems: list[str] = []
    try:
        features = load_feature_map(repo_root)
    except Exception as exc:  # noqa: BLE001 - surfaced as a config problem
        return [f"feature map unreadable: {exc}"]

    goal_ids = _goal_ids(repo_root)
    seed_names = _seed_function_names(repo_root)

    seen_ids: set[str] = set()
    for feat in features:
        fid = feat.get("id")
        if not fid:
            problems.append("feature without an 'id'")
            continue
        if fid in seen_ids:
            problems.append(f"{fid}: duplicate feature id")
        seen_ids.add(fid)

        problems += _validate_globs(repo_root, fid, feat)
        problems += _validate_beats(repo_root, fid, feat)
        problems += _validate_docs(repo_root, fid, feat)
        problems += [
            f"{fid}: cuj goal {goal!r} not in {PERSONAS_FILE}"
            for goal in feat.get("cuj_goals") or []
            if goal not in goal_ids
        ]
        problems += _validate_anchors(repo_root, fid, feat)
        problems += [
            f"{fid}: seed function {fn!r} not defined in {SEED_FILE}"
            for fn in feat.get("seed_functions") or []
            if fn not in seed_names
        ]

    return problems


def _glob_matches_anything(repo_root: pathlib.Path, glob: str) -> bool:
    if any(ch in glob for ch in "*?["):
        return any(repo_root.glob(glob))
    return (repo_root / glob).exists()


def _anchor_paired_file(anchor: str) -> str | None:
    """The artifact file a help anchor pairs to (None for a malformed anchor;
    validate_feature_map reports those separately)."""
    if anchor.startswith("docs_ui.html#"):
        return HELP_SOURCE_FILE.as_posix()
    if anchor.startswith("tour:"):
        return TOUR_FILE.as_posix()
    return None


def _leg(feature: dict, key: str) -> list:
    return feature.get(key) or []


def paired_artifact_files(feature: dict) -> set[str]:
    """Repo-relative files whose change satisfies the pairing for this feature.
    Tending the map itself always counts (an honest 'this feature has no demo
    beat yet' edit is a legitimate pairing action)."""
    paired: set[str] = {FEATURE_MAP.as_posix()}
    for beat in _leg(feature, "demo_beats"):
        script = str(beat).partition("#")[0]
        paired.add((DEMO_DIR / script).as_posix())
    if feature.get("cuj_goals"):
        paired.add(PERSONAS_FILE.as_posix())
    anchor_files = (_anchor_paired_file(str(a)) for a in _leg(feature, "help_anchors"))
    paired.update(f for f in anchor_files if f)
    if feature.get("seed_functions"):
        paired.add(SEED_FILE.as_posix())
    paired.update(pathlib.PurePosixPath(str(doc)).as_posix() for doc in _leg(feature, "docs"))
    return paired


def find_unpaired(
    features: list[dict], changed: set[str], waived: bool
) -> list[ConsistencyFinding]:
    """The core classification: features whose code changed with no paired
    artifact change. A range-level waiver clears everything (it is audited in
    the commit message, which is the point)."""
    if waived:
        return []
    findings: list[ConsistencyFinding] = []
    for feat in features:
        fid = feat.get("id", "?")
        matched_glob = matched_file = None
        for g in feat.get("code_globs") or []:
            for f in sorted(changed):
                if fnmatch.fnmatch(f, g):
                    matched_glob, matched_file = g, f
                    break
            if matched_glob:
                break
        if not matched_glob:
            continue
        paired = paired_artifact_files(feat)
        if paired & changed:
            continue
        findings.append(ConsistencyFinding(fid, matched_glob, str(matched_file), sorted(paired)))
    return findings


def has_waiver(commit_messages: str) -> bool:
    return bool(_WAIVER_RE.search(commit_messages))


def exit_code(findings: list[ConsistencyFinding], hard: bool) -> int:
    """Advisory semantics: findings print but pass; --hard flips to blocking."""
    return 1 if (hard and findings) else 0


def _git(repo_root: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True)


def resolve_range(repo_root: pathlib.Path, explicit: str | None) -> str | None:
    """The diff range to check; None means 'nothing to check, exit 0 with a
    note' (rootless HEAD, missing origin/main and no parent)."""
    if explicit:
        return explicit
    env = os.environ.get(RANGE_ENV)
    if env:
        return env
    branch = _git(repo_root, "branch", "--show-current").stdout.strip()
    if branch in ("main", "master"):
        if _git(repo_root, "rev-parse", "--verify", "HEAD~1").returncode == 0:
            return "HEAD~1...HEAD"
        return None
    if _git(repo_root, "rev-parse", "--verify", "origin/main").returncode == 0:
        return DEFAULT_RANGE
    if _git(repo_root, "rev-parse", "--verify", "HEAD~1").returncode == 0:
        return "HEAD~1...HEAD"
    return None


def changed_files(repo_root: pathlib.Path, range_spec: str) -> set[str]:
    proc = _git(repo_root, "diff", "--name-only", range_spec)
    if proc.returncode != 0:
        raise RuntimeError(f"git diff {range_spec} failed: {proc.stderr.strip()[:300]}")
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


def range_commit_messages(repo_root: pathlib.Path, range_spec: str) -> str:
    log_spec = range_spec.replace("...", "..") if "..." in range_spec else range_spec
    proc = _git(repo_root, "log", "--format=%B", log_spec)
    return proc.stdout if proc.returncode == 0 else ""


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = pathlib.Path.cwd()
    hard = "--hard" in argv or os.environ.get(HARD_ENV, "") not in ("", "0")
    positional = [a for a in argv if not a.startswith("-")]
    explicit = positional[0] if positional else None

    problems = validate_feature_map(repo_root)
    if problems:
        for p in problems:
            print(f"[MAP] {p}")
        print(f"\n{len(problems)} feature-map problem(s): fix docs/feature-map.yaml.")
        return 2

    range_spec = resolve_range(repo_root, explicit)
    if range_spec is None:
        print("consistency: no usable diff range (no origin/main, no parent commit); skipping.")
        return 0

    try:
        changed = changed_files(repo_root, range_spec)
    except RuntimeError as exc:
        print(f"[MAP] {exc}")
        return 2

    features = load_feature_map(repo_root)
    waived = has_waiver(range_commit_messages(repo_root, range_spec))
    findings = find_unpaired(features, changed, waived)

    label = "HARD" if hard else "ADVISORY"
    for f in findings:
        print(
            f"[{label}] consistency: feature {f.feature!r} changed "
            f"(matched glob {f.matched_glob!r} via {f.changed_file}) but none of its "
            f"paired artifacts did. Update one of: {', '.join(f.missing)} "
            f"or add a commit trailer 'Consistency: n/a - <reason>'."
        )
    if waived:
        print("consistency: range carries a 'Consistency: n/a' waiver trailer (audited).")
    print(
        f"\nconsistency ({range_spec}): {len(changed)} changed file(s), "
        f"{len(findings)} unpaired feature(s). Mode: {'hard' if hard else 'advisory'}."
    )
    return exit_code(findings, hard)


if __name__ == "__main__":
    sys.exit(main())
