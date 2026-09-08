"""Undriven-public-producer advisory (software-factory advisory leg).

This is a REPORT, not a gate: it emits `[REACHABILITY] ADVISORY` findings for public
top-level producers under src/kripos which no other src caller reaches, but is
exit-inert this wave (always exit 0 on findings; the only nonzero exit is 2 on an
internal analysis error). It closes the "landed-but-undriven-producer" class caught by
hand in the v3-increment4 lane (a §4 reader-translation producer landed with zero
callers), the single genuinely-new rigour lever the code-graph evaluation surfaced.

It deliberately has a syntactic honesty ceiling: its offline stdlib `ast`, name-based
index does not resolve dynamic dispatch, registry-by-string, or framework entrypoints.
A dynamically-driven producer can therefore appear undriven; that is why this is an
advisory, baseline-snapshotted report rather than a gate (a NEW undriven producer stands
out against the recorded snapshot, so growth is visible without the gate ever blocking).
References are counted from src/kripos code only, so a producer reached only from tests/
is correctly reported undriven — that is the v3-increment4 class, by design.

Composes with the ADR-0089 ungated-module coverage report: ADR-0089 answers
disposability at intent-register granularity (is a module's intent written down
anywhere?), this answers it at call-edge granularity (does any src caller reach this
producer?). A fully-gated module can still hold an undriven producer symbol.

    python -m scripts.check_reachability            # advisory report, exit 0
    python -m scripts.check_reachability --report    # identical explicit report
    python -m scripts.check_reachability --update    # record the current snapshot

Refs: docs/design-notes/2026-07-24_eksterne-fabrikk-kilder.md (compass code-graph
evaluation, candidate adoption #1); board item VhPg; composes with ADR-0089.
"""

from __future__ import annotations

import ast
import json
import pathlib
import sys
from collections import defaultdict
from typing import NamedTuple

SRC_ROOT = "src/kripos"
BASELINE = pathlib.Path("reachability-baseline.json")
ENTRYPOINT_DECORATORS = frozenset(
    {
        "get",
        "post",
        "put",
        "delete",
        "patch",
        "head",
        "options",
        "websocket",
        "exception_handler",
        "middleware",
        "on_event",
        "command",
        "callback",
        "task",
        "hookimpl",
        "fixture",
        "validator",
        "field_validator",
        "root_validator",
        "model_validator",
        "listens_for",
        "register",
    }
)


class Producer(NamedTuple):
    module: str
    symbol: str
    kind: str
    lineno: int
    end_lineno: int = 0  # 0 for a hand-built producer -> its span is the single lineno

    @property
    def key(self) -> str:
        return f"{self.module}::{self.symbol}"


def iter_source_files(repo_root: pathlib.Path, src_root: str = SRC_ROOT) -> list[pathlib.Path]:
    """Every Python source file under ``src_root``, in deterministic order."""
    root = repo_root / src_root
    if not root.exists():
        return []
    return sorted(root.rglob("*.py"))


def _dotted_module(repo_root: pathlib.Path, path: pathlib.Path) -> str:
    """``src/kripos/foo.py`` -> ``kripos.foo`` (dropping package ``__init__``)."""
    rel = path.relative_to(repo_root / "src")
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def decorator_names(node: ast.AST) -> set[str]:
    """Terminal names of a definition's decorators, unwrapping decorator calls."""
    names: set[str] = set()
    for decorator in getattr(node, "decorator_list", []):
        current = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(current, ast.Attribute):
            names.add(current.attr)
        elif isinstance(current, ast.Name):
            names.add(current.id)
    return names


def is_entrypoint(node: ast.AST) -> bool:
    """Whether a framework dispatch decorator drives this producer externally."""
    return bool(decorator_names(node) & ENTRYPOINT_DECORATORS)


def _is_all_assignment(node: ast.AST) -> bool:
    """A module-level ``__all__ = [...]`` / ``__all__: ... = [...]`` assignment."""
    if isinstance(node, ast.Assign):
        targets: list[ast.expr] = list(node.targets)
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    else:
        return False
    return any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets)


def _string_elements(value: ast.expr | None) -> list[tuple[str, int]]:
    """``(string, lineno)`` for each str constant in a List/Tuple literal, else empty."""
    if not isinstance(value, (ast.List, ast.Tuple)):
        return []
    return [
        (element.value, element.lineno)
        for element in value.elts
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    ]


def _module_all_references(tree: ast.Module) -> list[tuple[str, int]]:
    """Names exported via a module-level ``__all__`` (a public re-export is a reference)."""
    refs: list[tuple[str, int]] = []
    for node in tree.body:
        if _is_all_assignment(node):
            refs.extend(_string_elements(node.value))
    return refs


def build_reference_index(
    repo_root: pathlib.Path, files: list[pathlib.Path]
) -> dict[str, list[tuple[str, int]]]:
    """Name -> source locations that syntactically mention that name."""
    refs: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for path in files:
        module = _dotted_module(repo_root, path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                refs[node.id].append((module, node.lineno))
            elif isinstance(node, ast.Attribute):
                refs[node.attr].append((module, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    refs[alias.name].append((module, node.lineno))
                    if alias.asname:
                        refs[alias.asname].append((module, node.lineno))
        for name, lineno in _module_all_references(tree):
            refs[name].append((module, lineno))
    return dict(refs)


def public_producers(repo_root: pathlib.Path, files: list[pathlib.Path]) -> list[Producer]:
    """Public top-level functions and classes, excluding framework entrypoints."""
    producers: list[Producer] = []
    for path in files:
        module = _dotted_module(repo_root, path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if node.name.startswith("_") or is_entrypoint(node):
                continue
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            producers.append(
                Producer(module, node.name, kind, node.lineno, node.end_lineno or node.lineno)
            )
    return producers


def is_reached(producer: Producer, refs: dict[str, list[tuple[str, int]]]) -> bool:
    """Whether a name reference occurs outside the producer's own definition span.

    A reference inside the producer's own body (recursion / the def site itself) does
    not count as reached; a reference anywhere else in src/kripos does."""
    hi = producer.end_lineno or producer.lineno
    return any(
        module != producer.module or not (producer.lineno <= lineno <= hi)
        for module, lineno in refs.get(producer.symbol, [])
    )


def _collect(
    repo_root: pathlib.Path | None = None, src_root: str = SRC_ROOT
) -> tuple[list[Producer], list[Producer]]:
    """(all public producers, undriven subset sorted by (module, symbol)) in one parse."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    files = iter_source_files(repo_root, src_root)
    refs = build_reference_index(repo_root, files)
    producers = public_producers(repo_root, files)
    undriven = sorted(
        (p for p in producers if not is_reached(p, refs)), key=lambda p: (p.module, p.symbol)
    )
    return producers, undriven


def undriven_producers(
    repo_root: pathlib.Path | None = None, src_root: str = SRC_ROOT
) -> list[Producer]:
    """Public, non-entrypoint producers that no ``src/kripos`` caller reaches."""
    return _collect(repo_root, src_root)[1]


def load_baseline(repo_root: pathlib.Path) -> set[str]:
    """Keys in the saved undriven-producer baseline, or an empty missing snapshot."""
    path = repo_root / BASELINE
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    values = data.get("undriven_producers") if isinstance(data, dict) else None
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError(f"malformed {BASELINE}")
    return set(values)


def write_baseline(repo_root: pathlib.Path, producers: list[Producer]) -> None:
    """Persist a deterministic snapshot of the current advisory findings."""
    data = {"undriven_producers": sorted(producer.key for producer in producers)}
    (repo_root / BASELINE).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def render_report(
    producers: list[Producer], baseline: set[str], n_public: int | None = None
) -> str:
    """Render the exit-inert ADVISORY report and its baseline delta.

    ``n_public`` is the total public-producer count for the summary line; when omitted
    (e.g. a hand-built producer list in a test) it falls back to the number of findings."""
    producers = sorted(producers, key=lambda p: (p.module, p.symbol))
    lines = []
    for producer in producers:
        line = (
            f"[REACHABILITY] ADVISORY {producer.key} ({producer.kind}, line {producer.lineno}): "
            "public producer no src caller reaches"
        )
        if producer.key not in baseline:
            line += "  (NEW since baseline)"
        lines.append(line)
    n_public = n_public if n_public is not None else len(producers)
    lines.append(
        f"\nreachability: {n_public} public producer(s) under {SRC_ROOT}, "
        f"{len(producers)} undriven (baseline {len(baseline)}). Advisory: "
        "flags undriven producers, never changes exit code."
    )
    n_new = sum(producer.key not in baseline for producer in producers)
    if n_new:
        lines.append(
            f"{n_new} undriven producer(s) not in the baseline snapshot "
            "(advisory; run --update to record)."
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = pathlib.Path.cwd()
    try:
        producers, undriven = _collect(repo_root)
        if "--update" in argv:
            write_baseline(repo_root, undriven)
            print(f"wrote {BASELINE}: {len(undriven)} undriven producer(s)")
            return 0
        print(render_report(undriven, load_baseline(repo_root), n_public=len(producers)))
        return 0
    except Exception as exc:  # noqa: BLE001 - internal analysis failures are exit 2
        print(f"[ERROR] reachability analysis failed: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
