"""Contract-touch classifier (software-factory NOW phase, ADR-0086 / gap 4 of
docs/design-notes/2026-07-24_fabrikk-gap-remediering.md).

The author-agnostic gate-plus-human-signature control (ADR-0071) is correctly
placed in principle, but it is not calibrated to the CONTRACT boundary: a
reviewer still reads every diff broadly, and that habit degrades into a
rubber-stamp queue as generation volume grows. This script labels each changed
file CONTRACT-LEVEL or within-contract so review effort (and the advisory RÅD
lanes) concentrate where a mechanical gate cannot: at the boundary a change in
meaning crosses, not on every line of an accepted implementation.

A file is CONTRACT-LEVEL when it is any of:
  - an ADR `code:`-frontmatter reference (reuses check_traceability's
    frontmatter parser and ADR graph);
  - a welfare-marked file (`@pytest.mark.welfare` anywhere in the file), a file
    carrying the `GUARD_LABEL` guard constant, or the welfare meta-test itself
    (tests/test_welfare_invariants_meta.py);
  - the egress seam (check_egress's provider prefixes `kripos.llm.` /
    `kripos.vision.` / `kripos.vlm.`, or the `kripos.web` runtime entrypoint
    whose import closure check_egress asserts against);
  - a Pydantic `BaseModel` or `frozen=True` dataclass DEFINITION being changed
    (not merely imported/called), detected by intersecting the diff's changed
    line ranges with the AST line-spans of schema class bodies, on both the old
    and new side of the change;
  - a strict-mypy seam, IF gap 1's `[tool.mypy.overrides]` config exists yet
    (`pyproject.toml`); absent that config this criterion contributes nothing
    (there is nothing to be a seam of yet);
  - an alembic migration file (anything under `migrations/`, the same
    directory check_migration_heads.py resolves against);
  - a `docs/feature-map.yaml`-paired file (a feature's `code_globs` match, or
    one of its registered paired-artifact files), or `docs/feature-map.yaml` /
    an ADR document itself.

Everything else is within-contract: an accepted implementation detail riding on
the mechanical gates. The distinction governs ATTENTION, never AUTHORITY: this
is advisory by default (a label, exit 0) and can never lower a gate; the human
merge-signature and the author-agnostic control plane (ADR-0071) are unchanged.
Unknown/unclassifiable beats safe: if the schema check itself fails (a git or
parse error), the file is failed CONTRACT-LEVEL rather than silently dropped.

Separately, a range-level advisory (never per-file, never exit-code-bearing)
flags CONTRACT-TAMPER when the same resolved range both touches `src/` and
either edits a known ratchet baseline file or nets a drop in the literal
substring ``assert `` across changed `tests/**/*.py` files. That is the
"quietly narrowed version of everything" signal (gap 3 of the eksterne-
fabrikk-kilder design note): the criteria that gate the code moved in the same
diff as the code. Advisory only — `main()`'s exit logic is unchanged.

A second range-level advisory (same posture) flags CRITERIA-DIGEST: the
"read-only spec with a recorded digest" idea from Specter (adoption #1 of the
2026-07-24 eksterne-fabrikk-kilder note, the criteria-side complement of the
baseline/assert tamper leg above). For each ADR, `criteria_digest_findings`
hashes the ADR's criteria BODY (the prose below the front-matter fence, so a
`code:` registration or a status bump is not read as a criteria change) and
fires when the SAME range mutates BOTH (a) that criteria body — the ADR document
is in the changed set AND its body digest actually moved (old != new) — AND (b)
at least one `code:`-governed path of that same ADR (the src/test code those
criteria govern). The traceability graph's `code:` link is how "the criteria a
change cites" is resolved deterministically and offline; a `Refs: ADR-NNNN`
commit trailer, when present, only ENRICHES the finding (records that the author
also cited it), never a firing condition on its own — a stale/missing `code:`
link is check_traceability's gate to catch, not this one's to guess around. A
brand-new ADR (no old side) is new criteria, not a mutation, so it does not
fire; a deleted ADR co-moving with its governed code does. Weakening a criterion
to make a run pass is sometimes legitimate and PO-reviewed — the leg's whole job
is to make that co-movement VISIBLE as a RÅD event, never to gate it. Advisory
only — `main()`'s exit logic is unchanged.

    python -m scripts.check_contract_touch                  # advisory report, exit 0
    python -m scripts.check_contract_touch --report          # same, explicit
    python -m scripts.check_contract_touch --require-review  # exit 1 if any file is contract-level
    python -m scripts.check_contract_touch main...HEAD       # explicit range

Refs: ADR-0086 (mechanisms reused: ADR-0071 egress/welfare/migration gates,
ADR-0073 feature-map consistency gate, ADR-0074 traceability graph).
"""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import pathlib
import re
import subprocess
import sys
import tomllib
from typing import NamedTuple

from scripts.check_consistency import (
    changed_files,
    load_feature_map,
    paired_artifact_files,
    range_commit_messages,
    resolve_range,
)
from scripts.check_egress import _PROVIDER_PREFIXES
from scripts.check_migration_heads import MIGRATIONS_DIR
from scripts.check_traceability import iter_adr_paths, parse_adr_frontmatter

ADR_DIR = pathlib.Path("docs/decisions")
FEATURE_MAP = pathlib.Path("docs/feature-map.yaml")
WELFARE_META_TEST = "tests/test_welfare_invariants_meta.py"

_WELFARE_MARKER = "pytest.mark.welfare"
_GUARD_CONST = "GUARD_LABEL"

# Ratchet baseline files that, when co-edited with src/, are a range-level
# contract-tamper signal (the bar that gates the code moved in the same range).
_RATCHET_BASELINES = frozenset(
    {
        ".ruff-baseline.json",
        ".mypy-baseline.json",
        "complexity-baseline.json",
        ".gitleaks-baseline.json",
        ".gitleaks-worktree-baseline.json",
    }
)

# Literal substring used for assertion-count delta (assert + one trailing space).
_ASSERT_LITERAL = "assert "

# Criteria-digest leg. The front-matter fence, matched exactly as
# check_traceability.parse_adr_frontmatter matches it, so the criteria BODY
# digested below is everything AFTER the same block (a `code:`/status edit inside
# the front-matter is deliberately NOT a criteria-body change).
_ADR_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
# A `Ref(s):` trailer line, and the ADR tokens named on it (enrichment only).
_REFS_TRAILER_RE = re.compile(r"^\s*refs?\s*:", re.IGNORECASE)
_ADR_TOKEN_RE = re.compile(r"ADR-\d{3,4}", re.IGNORECASE)
_ADR_NUM_RE = re.compile(r"(\d{3,4})")


class ContractHit(NamedTuple):
    kind: str
    detail: str


class FileVerdict(NamedTuple):
    path: str
    contract: bool
    hits: tuple[ContractHit, ...]


class ContractTouchReport(NamedTuple):
    range_spec: str
    verdicts: tuple[FileVerdict, ...]
    tamper: ContractHit | None = None
    criteria_digests: tuple[ContractHit, ...] = ()

    @property
    def contract_files(self) -> list[FileVerdict]:
        return [v for v in self.verdicts if v.contract]

    @property
    def within_contract_files(self) -> list[FileVerdict]:
        return [v for v in self.verdicts if not v.contract]


def adr_code_index(repo_root: pathlib.Path | None = None) -> dict[str, list[str]]:
    """repo-relative path -> sorted ADR ids that cite it in `code:` frontmatter."""
    repo_root = repo_root or pathlib.Path.cwd()
    index: dict[str, set[str]] = {}
    for path in iter_adr_paths(repo_root / ADR_DIR):
        fm = parse_adr_frontmatter(path)
        if not isinstance(fm, dict):
            continue
        adr_id = str(fm.get("id", path.stem))
        for entry in fm.get("code") or []:
            rel, _, _symbol = str(entry).partition("::")
            index.setdefault(pathlib.PurePosixPath(rel).as_posix(), set()).add(adr_id)
    return {k: sorted(v) for k, v in index.items()}


def welfare_touch(path: str, text: str | None) -> ContractHit | None:
    """Scoped to Python files: a markdown design note that merely DISCUSSES the
    marker or the guard constant in prose must not read as a welfare touch."""
    if path == WELFARE_META_TEST:
        return ContractHit("welfare-meta-test", "the welfare-invariant meta-test itself")
    if text is None or not path.endswith(".py"):
        return None
    if _WELFARE_MARKER in text:
        return ContractHit("welfare-marker", "@pytest.mark.welfare present in file")
    if _GUARD_CONST in text:
        return ContractHit("guard-label", "GUARD_LABEL guard constant present in file")
    return None


def dotted_module(path: str) -> str | None:
    """repo-relative `src/...` path -> dotted module name; None outside src/."""
    p = pathlib.PurePosixPath(path)
    try:
        rel = p.relative_to("src")
    except ValueError:
        return None
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else None


def egress_touch(path: str) -> ContractHit | None:
    mod = dotted_module(path)
    if mod is None:
        return None
    if mod.startswith(_PROVIDER_PREFIXES):
        return ContractHit("egress-seam", f"{mod} is in the provider seam {_PROVIDER_PREFIXES}")
    if mod == "kripos.web" or mod.startswith("kripos.web."):
        return ContractHit("egress-seam", f"{mod} is the kripos.web runtime-egress entrypoint")
    return None


def migration_touch(path: str) -> ContractHit | None:
    if path == MIGRATIONS_DIR or path.startswith(f"{MIGRATIONS_DIR}/"):
        return ContractHit("migration", f"under {MIGRATIONS_DIR}/ (alembic migration graph)")
    return None


def adr_doc_touch(path: str) -> ContractHit | None:
    if path.startswith(f"{ADR_DIR.as_posix()}/") and path.endswith(".md"):
        return ContractHit("adr-doc", "an ADR document itself")
    return None


def feature_map_touch(repo_root: pathlib.Path, changed: set[str]) -> dict[str, ContractHit]:
    """Files touched by the diff that docs/feature-map.yaml governs: the map
    itself, or a file that is either a feature's code_glob match or one of its
    registered paired artifacts (demo/CUJ/help/seed/docs legs)."""
    hits: dict[str, ContractHit] = {}
    fm_path = FEATURE_MAP.as_posix()
    if fm_path in changed:
        hits[fm_path] = ContractHit("feature-map-doc", "docs/feature-map.yaml itself")
    try:
        features = load_feature_map(repo_root)
    except Exception:  # noqa: BLE001 - an unreadable map is check_consistency's own gate's job
        features = []
    for feat in features:
        fid = feat.get("id", "?")
        paired = paired_artifact_files(feat)
        globs = feat.get("code_globs") or []
        for f in changed:
            if f in hits:
                continue
            if f in paired or any(fnmatch.fnmatch(f, g) for g in globs):
                hits[f] = ContractHit("feature-map-paired", f"paired with feature {fid!r}")
    return hits


def _strict_override_modules(override: dict) -> list[str]:
    """Module glob(s) declared on ONE `[[tool.mypy.overrides]]` table, if it
    sets `strict = true`; empty otherwise (a non-strict override is not a seam)."""
    if not override.get("strict"):
        return []
    module = override.get("module")
    if isinstance(module, list):
        return [str(m) for m in module]
    return [str(module)] if module else []


def mypy_strict_module_globs(repo_root: pathlib.Path | None = None) -> list[str]:
    """Dotted-module glob patterns covered by a `strict = true`
    `[[tool.mypy.overrides]]` entry in pyproject.toml. Empty (never an error)
    until gap 1 (the mypy ratchet + strict-seam config) lands; this criterion
    is dormant, not broken, on a tree without that config yet."""
    repo_root = repo_root or pathlib.Path.cwd()
    try:
        data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    overrides = (data.get("tool") or {}).get("mypy", {}).get("overrides") or []
    globs: list[str] = []
    for override in overrides:
        if isinstance(override, dict):
            globs.extend(_strict_override_modules(override))
    return globs


def strict_mypy_touch(path: str, globs: list[str]) -> ContractHit | None:
    if not globs:
        return None
    mod = dotted_module(path)
    if mod is None:
        return None
    for pattern in globs:
        if fnmatch.fnmatch(mod, pattern):
            return ContractHit(
                "strict-mypy-seam", f"{mod} matches strict mypy override {pattern!r}"
            )
    return None


def _is_basemodel_base(base: ast.expr) -> bool:
    return (isinstance(base, ast.Name) and base.id == "BaseModel") or (
        isinstance(base, ast.Attribute) and base.attr == "BaseModel"
    )


def _is_frozen_dataclass_decorator(decorator: ast.expr) -> bool:
    if not isinstance(decorator, ast.Call):
        return False
    func = decorator.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if name != "dataclass":
        return False
    return any(
        kw.arg == "frozen" and isinstance(kw.value, ast.Constant) and kw.value.value is True
        for kw in decorator.keywords
    )


def schema_class_spans(source: str) -> list[tuple[int, int]]:
    """(lineno, end_lineno) of every BaseModel-subclass or frozen-dataclass
    class definition in `source`. Empty (never an error) on unparsable text."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    spans: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        is_schema = any(_is_basemodel_base(b) for b in node.bases) or any(
            _is_frozen_dataclass_decorator(d) for d in node.decorator_list
        )
        if is_schema:
            spans.append((node.lineno, node.end_lineno or node.lineno))
    return spans


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def hunk_ranges(diff_text: str) -> list[tuple[int, int, int, int]]:
    """(old_start, old_count, new_start, new_count) per hunk of a unified diff
    (a bare count of 1 is omitted by git; restored here)."""
    out: list[tuple[int, int, int, int]] = []
    for line in diff_text.splitlines():
        m = _HUNK_RE.match(line)
        if not m:
            continue
        old_start, old_count, new_start, new_count = m.groups()
        out.append(
            (
                int(old_start),
                int(old_count) if old_count is not None else 1,
                int(new_start),
                int(new_count) if new_count is not None else 1,
            )
        )
    return out


def _overlaps(spans: list[tuple[int, int]], start: int, count: int) -> bool:
    lo, hi = (start, start) if count <= 0 else (start, start + count - 1)
    return any(a <= hi and lo <= b for a, b in spans)


def schema_touch_from_hunks(
    old_source: str | None,
    new_source: str | None,
    hunks: list[tuple[int, int, int, int]],
) -> bool:
    """True iff any hunk's changed lines overlap a schema class span on EITHER
    side of the change: the old side catches a removed/shrunk definition, the
    new side catches an added/grown one. A file that only calls/imports a model
    elsewhere never touches these spans, so plain usage does not trip this."""
    old_spans = schema_class_spans(old_source) if old_source is not None else []
    new_spans = schema_class_spans(new_source) if new_source is not None else []
    if not old_spans and not new_spans:
        return False
    return any(
        _overlaps(old_spans, old_start, old_count) or _overlaps(new_spans, new_start, new_count)
        for old_start, old_count, new_start, new_count in hunks
    )


def _split_range(range_spec: str) -> tuple[str, str, bool]:
    """(left, right, is_triple_dot); right defaults to HEAD if omitted."""
    if "..." in range_spec:
        left, _, right = range_spec.partition("...")
        return left, right or "HEAD", True
    if ".." in range_spec:
        left, _, right = range_spec.partition("..")
        return left, right or "HEAD", False
    return range_spec, "HEAD", False


def resolve_refs(repo_root: pathlib.Path, range_spec: str) -> tuple[str | None, str]:
    """(left_ref, right_ref): left_ref is the merge-base for a `...` range (the
    same semantics `git diff A...B` uses), the literal left side otherwise, or
    None if it cannot be resolved (schema check then fails safe per-file)."""
    left, right, triple = _split_range(range_spec)
    if not triple:
        return (left or None), right
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", left, right],
        capture_output=True,
        text=True,
    )
    return (proc.stdout.strip() or None) if proc.returncode == 0 else None, right


def _read_at_ref(repo_root: pathlib.Path, ref: str | None, path: str) -> str | None:
    if ref is None:
        return None
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        errors="replace",
    )
    return proc.stdout if proc.returncode == 0 else None


def _diff_hunks_for_file(
    repo_root: pathlib.Path, range_spec: str, path: str
) -> list[tuple[int, int, int, int]]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--unified=0", range_spec, "--", path],
        capture_output=True,
        text=True,
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff --unified=0 {range_spec} -- {path}: {proc.stderr.strip()}")
    return hunk_ranges(proc.stdout)


def _content_for_welfare(
    repo_root: pathlib.Path, left_ref: str | None, right_ref: str, path: str
) -> str | None:
    text = _read_at_ref(repo_root, right_ref, path)
    return text if text is not None else _read_at_ref(repo_root, left_ref, path)


def _schema_hit(
    repo_root: pathlib.Path,
    range_spec: str,
    path: str,
    left_ref: str | None,
    right_ref: str,
) -> ContractHit | None:
    """Schema-definition criterion, scoped to src/ Python modules (where a
    type contract lives at runtime). Fails SAFE to contract-level on any error
    computing the check: an unclassifiable diff is never silently dropped."""
    if not (path.endswith(".py") and path.startswith("src/")):
        return None
    try:
        old_text = _read_at_ref(repo_root, left_ref, path)
        new_text = _read_at_ref(repo_root, right_ref, path)
        hunks = _diff_hunks_for_file(repo_root, range_spec, path)
    except Exception as exc:  # noqa: BLE001 - deliberate fail-SAFE, see module docstring
        return ContractHit(
            "unclassifiable", f"schema check failed ({exc}); failing safe to contract-level"
        )
    if schema_touch_from_hunks(old_text, new_text, hunks):
        return ContractHit(
            "schema-contract", "BaseModel/frozen-dataclass definition touched, not just used"
        )
    return None


def count_assert_literals(text: str) -> int:
    """Count occurrences of the literal substring ``assert `` (assert + space)."""
    return text.count(_ASSERT_LITERAL)


def ratchet_baseline_touch(changed: set[str]) -> ContractHit | None:
    """Any of the four known ratchet baseline files appear in the changed set."""
    touched = sorted(p for p in changed if p in _RATCHET_BASELINES)
    if not touched:
        return None
    names = ", ".join(touched)
    return ContractHit(
        "contract-tamper-baseline",
        f"ratchet baseline file(s) changed: {names}",
    )


def assertion_delta_across_tests(
    repo_root: pathlib.Path,
    changed: set[str],
    left_ref: str | None,
    right_ref: str,
) -> tuple[int, list[tuple[str, int, int]]]:
    """Net ``assert `` delta across changed ``tests/**/*.py`` files.

    Returns ``(net_delta, losses)`` where ``losses`` is
    ``[(path, old_count, new_count), ...]`` for every changed test file whose
    literal-assert count dropped (new < old). Added files have old_count 0;
    deleted files have new_count 0. Net decrease means ``net_delta < 0``.
    """
    net = 0
    losses: list[tuple[str, int, int]] = []
    for path in sorted(changed):
        if not (path.startswith("tests/") and path.endswith(".py")):
            continue
        old_text = _read_at_ref(repo_root, left_ref, path)
        new_text = _read_at_ref(repo_root, right_ref, path)
        old_count = count_assert_literals(old_text or "")
        new_count = count_assert_literals(new_text or "")
        net += new_count - old_count
        if new_count < old_count:
            losses.append((path, old_count, new_count))
    return net, losses


def contract_tamper_finding(
    repo_root: pathlib.Path,
    changed: set[str],
    left_ref: str | None,
    right_ref: str,
) -> ContractHit | None:
    """Range-level advisory: src/ change co-occurring with a weakened gate.

    Weakening the criteria in the same diff as the code they gate is the
    reviewer's highest-priority signal — the run that "passed a quietly
    narrowed version of everything" (gap 3, eksterne-fabrikk-kilder). Fires
    only when BOTH (a) at least one changed path starts with ``src/`` and
    (b) either a ratchet baseline file is in the changed set or the net
    count of literal ``assert `` across changed ``tests/**/*.py`` decreases.
    Advisory only: never changes the exit code of ``main()``.
    """
    if not any(p.startswith("src/") for p in changed):
        return None

    parts: list[str] = []
    baseline = ratchet_baseline_touch(changed)
    if baseline is not None:
        parts.append(baseline.detail)

    net, losses = assertion_delta_across_tests(repo_root, changed, left_ref, right_ref)
    if net < 0 and losses:
        file_bits = [f"{path} ({old}→{new}, -{old - new})" for path, old, new in losses]
        parts.append(
            f"net {net} literal {_ASSERT_LITERAL!r} across tests/**/*.py: " + "; ".join(file_bits)
        )

    if not parts:
        return None

    detail = (
        "src/ change co-occurs with gate-weakening signal: "
        + "; ".join(parts)
        + ". Advisory only: never changes exit code."
    )
    return ContractHit("contract-tamper", detail)


# ---------------------------------------------------------------------------
# Criteria-digest advisory (range-level, exit-code-inert). The criteria-side
# complement of the tamper leg above: an ADR's criteria body moved in the same
# range as code that ADR governs (adoption #1, eksterne-fabrikk-kilder note).
# ---------------------------------------------------------------------------


class AdrGovernance(NamedTuple):
    adr_id: str  # as written in front-matter (e.g. "ADR-0086")
    doc_path: str  # repo-relative posix path of the ADR document
    governed: frozenset[str]  # repo-relative posix `code:` paths (::symbol stripped)


def adr_governance(repo_root: pathlib.Path | None = None) -> list[AdrGovernance]:
    """Forward view of the traceability graph: per ADR, its document path and
    the set of code paths its `code:` front-matter governs. Reuses
    check_traceability's ADR enumeration + front-matter parser, so it sees
    exactly the ADRs (and the same `code:` entries) the traceability gate does.
    """
    repo_root = repo_root or pathlib.Path.cwd()
    out: list[AdrGovernance] = []
    for path in iter_adr_paths(repo_root / ADR_DIR):
        fm = parse_adr_frontmatter(path)
        if not isinstance(fm, dict):
            continue
        adr_id = str(fm.get("id", path.stem))
        governed = {
            pathlib.PurePosixPath(str(entry).partition("::")[0]).as_posix()
            for entry in (fm.get("code") or [])
        }
        out.append(
            AdrGovernance(adr_id, path.relative_to(repo_root).as_posix(), frozenset(governed))
        )
    return out


def criteria_body(text: str) -> str:
    """An ADR's criteria content: everything after the YAML front-matter block
    (front-matter stripped with the same fence check_traceability uses). No
    front-matter block -> the whole text is body."""
    return _ADR_FRONTMATTER_RE.sub("", text, count=1)


def criteria_digest(text: str | None) -> str | None:
    """Deterministic, offline SHA-256 over the ADR's criteria body; None for a
    missing side (an ADR that did not exist / was deleted at that ref)."""
    if text is None:
        return None
    return hashlib.sha256(criteria_body(text).encode("utf-8")).hexdigest()


def _canonical_adr_id(raw: str) -> str:
    """Normalise an ADR id or token to ``ADR-NNNN`` for cross-comparison
    (front-matter id, a `Refs:` token, or a bare ``NNNN-slug`` stem)."""
    m = _ADR_NUM_RE.search(raw)
    return f"ADR-{int(m.group(1)):04d}" if m else raw.strip()


def cited_adr_ids(commit_messages: str) -> frozenset[str]:
    """Canonical ADR ids named on a ``Ref(s):`` trailer line across the range's
    commit messages. Enrichment ONLY: it strengthens a criteria-digest finding
    when the author also cited the ADR, but is never a firing condition — a
    citation with no `code:` link is check_traceability's concern, not this leg's.
    """
    ids: set[str] = set()
    for line in commit_messages.splitlines():
        if _REFS_TRAILER_RE.match(line):
            ids.update(_canonical_adr_id(tok) for tok in _ADR_TOKEN_RE.findall(line))
    return frozenset(ids)


def criteria_digest_findings(
    repo_root: pathlib.Path,
    changed: set[str],
    left_ref: str | None,
    right_ref: str,
    *,
    governance: list[AdrGovernance],
    cited: frozenset[str],
) -> tuple[ContractHit, ...]:
    """Range-level advisory, one hit per co-mutated ADR.

    Fires for ADR X when ALL hold:
      (a) X's document is in the changed set AND its criteria BODY digest moved
          (old side existed and old_digest != new_digest — so a brand-new ADR is
          new criteria, not a mutation, and a pure front-matter edit is silent);
      (b) at least one `code:`-governed path of X is ALSO in the changed set (the
          src/test code those criteria govern moved in the same range).
    Advisory only: contributes nothing to per-file verdicts or `main()`'s exit.
    """
    findings: list[ContractHit] = []
    for gov in governance:
        if gov.doc_path not in changed:
            continue
        governed_touched = sorted(gov.governed & changed)
        if not governed_touched:
            continue
        old_text = _read_at_ref(repo_root, left_ref, gov.doc_path)
        if old_text is None:  # newly-added ADR -> new criteria, not a mutation
            continue
        new_text = _read_at_ref(repo_root, right_ref, gov.doc_path)
        old_digest = criteria_digest(old_text)
        new_digest = criteria_digest(new_text)
        if old_digest == new_digest:  # front-matter-only churn: body unchanged
            continue
        old_short = (old_digest or "∅")[:12]
        new_short = "∅(deleted)" if new_digest is None else new_digest[:12]
        also = " (also cited on a Refs: trailer)" if _canonical_adr_id(gov.adr_id) in cited else ""
        detail = (
            f"{gov.adr_id} criteria body changed (digest {old_short}->{new_short}) in the same "
            f"range as code it governs: {', '.join(governed_touched)}{also}. "
            "Advisory only: never changes exit code."
        )
        findings.append(ContractHit("criteria-digest", detail))
    return tuple(findings)


def _classify_one(
    repo_root: pathlib.Path,
    range_spec: str,
    path: str,
    *,
    adr_index: dict[str, list[str]],
    fm_hits: dict[str, ContractHit],
    mypy_globs: list[str],
    left_ref: str | None,
    right_ref: str,
) -> FileVerdict:
    hits: list[ContractHit] = [
        ContractHit("adr-code", f"Code: ref in {adr_id}") for adr_id in adr_index.get(path, ())
    ]
    for maybe in (
        egress_touch(path),
        migration_touch(path),
        adr_doc_touch(path),
        fm_hits.get(path),
        strict_mypy_touch(path, mypy_globs),
    ):
        if maybe is not None:
            hits.append(maybe)
    w = welfare_touch(path, _content_for_welfare(repo_root, left_ref, right_ref, path))
    if w is not None:
        hits.append(w)
    schema_hit = _schema_hit(repo_root, range_spec, path, left_ref, right_ref)
    if schema_hit is not None:
        hits.append(schema_hit)
    return FileVerdict(path, bool(hits), tuple(hits))


def classify_files(
    repo_root: pathlib.Path, range_spec: str, changed: set[str]
) -> ContractTouchReport:
    left_ref, right_ref = resolve_refs(repo_root, range_spec)
    adr_index = adr_code_index(repo_root)
    fm_hits = feature_map_touch(repo_root, changed)
    mypy_globs = mypy_strict_module_globs(repo_root)
    verdicts = tuple(
        _classify_one(
            repo_root,
            range_spec,
            path,
            adr_index=adr_index,
            fm_hits=fm_hits,
            mypy_globs=mypy_globs,
            left_ref=left_ref,
            right_ref=right_ref,
        )
        for path in sorted(changed)
    )
    tamper = contract_tamper_finding(repo_root, changed, left_ref, right_ref)
    digests = criteria_digest_findings(
        repo_root,
        changed,
        left_ref,
        right_ref,
        governance=adr_governance(repo_root),
        cited=cited_adr_ids(range_commit_messages(repo_root, range_spec)),
    )
    return ContractTouchReport(range_spec, verdicts, tamper=tamper, criteria_digests=digests)


def build_report(
    repo_root: pathlib.Path | None = None, explicit_range: str | None = None
) -> ContractTouchReport | None:
    """None means 'nothing to check' (mirrors check_consistency.resolve_range)."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    range_spec = resolve_range(repo_root, explicit_range)
    if range_spec is None:
        return None
    changed = changed_files(repo_root, range_spec)
    return classify_files(repo_root, range_spec, changed)


def format_report(report: ContractTouchReport) -> str:
    lines = []
    for v in report.verdicts:
        label = "CONTRACT-LEVEL" if v.contract else "within-contract"
        reasons = "; ".join(f"{h.kind}: {h.detail}" for h in v.hits) or "no contract signal"
        lines.append(f"[{label}] {v.path}: {reasons}")
    n_total = len(report.verdicts)
    n_contract = len(report.contract_files)
    lines.append(
        f"\ncontract-touch ({report.range_spec}): {n_total} changed file(s), "
        f"{n_contract} contract-level, {n_total - n_contract} within-contract. "
        "Advisory: escalates review ATTENTION, never merge authority."
    )
    if report.tamper is not None:
        lines.append(f"[CONTRACT-TAMPER] {report.tamper.kind}: {report.tamper.detail}")
    for digest in report.criteria_digests:
        lines.append(f"[CRITERIA-DIGEST] {digest.kind}: {digest.detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = pathlib.Path.cwd()
    require_review = "--require-review" in argv
    positional = [a for a in argv if not a.startswith("-")]
    explicit = positional[0] if positional else None

    report = build_report(repo_root, explicit)
    if report is None:
        print("contract-touch: no usable diff range (no origin/main, no parent commit); skipping.")
        return 0
    print(format_report(report))
    if require_review and report.contract_files:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
