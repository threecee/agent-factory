"""Entrypoint-doc freshness gate (ADR-0079) -- HARD, deterministic, offline.

The hand-written entrypoint docs (README.md, docs/ARCHITECTURE.md, AGENTS.md)
rotted silently for weeks: nothing paired them to the code surfaces they
describe, so "10 ADRs / ~227 tests / Jinja2-only" shipped as the advertised
front door of a much larger system. This gate makes the mechanically checkable
claims in those docs verifiable against the tree, so the same rot now fails
`make verify` instead of accumulating:

  CHECK 1 -- model-role coverage. Every role in config/models.yaml (and each
  role's pinned default entry name) must appear in docs/ARCHITECTURE.md's
  model-role table.

  CHECK 2 -- subsystem coverage. Every top-level package under src/kripos/ must
  be named in BOTH docs/ARCHITECTURE.md (subsystem inventory) and AGENTS.md
  (module map). A new package that skips the entrypoint docs is a finding.

  CHECK 3 -- README quickstart integrity. Every `make <target>` the README
  tells a newcomer to run must exist in the Makefile, and every `kripos-*` CLI
  it names must exist in pyproject's [project.scripts].

Exact-match mechanical only: this proves the docs NAME what exists; whether the
prose describes it well stays a review call (same split as check_consistency).

    python -m scripts.check_entrypoint_docs      # exit 1 on any finding
"""

from __future__ import annotations

import pathlib
import re
import sys
import tomllib

import yaml

ARCHITECTURE = pathlib.Path("docs/ARCHITECTURE.md")
AGENTS = pathlib.Path("AGENTS.md")
README = pathlib.Path("README.md")
MODELS = pathlib.Path("config/models.yaml")
MAKEFILE = pathlib.Path("Makefile")
PYPROJECT = pathlib.Path("pyproject.toml")
SRC_ROOT = pathlib.Path("src/kripos")

_MAKE_TARGET_REF_RE = re.compile(r"\bmake\s+([a-z][a-z0-9_-]*)")
_MAKEFILE_TARGET_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):", re.MULTILINE)
_CLI_REF_RE = re.compile(r"\bkripos-[a-z][a-z0-9-]*\b")
_CLI_IGNORE = frozenset({"kripos-chatanalyse"})


def _code_spans(text: str) -> str:
    """The README text that makes runnable claims: fenced code blocks plus
    inline backtick spans. Prose like "make sure" never reaches the target
    check."""
    fenced = re.findall(r"```.*?```", text, re.DOTALL)
    inline = re.findall(r"`[^`\n]+`", text)
    return "\n".join(fenced + inline)


def _read(repo_root: pathlib.Path, rel: pathlib.Path) -> str | None:
    path = repo_root / rel
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def model_roles(repo_root: pathlib.Path) -> dict[str, str | None]:
    """role -> pinned default entry name (the resolver's unset-name fallback).

    A role value may be a plain entry list, or the structured
    ``{default: [...], per_language: {...}}`` shape (the translate role,
    ADR-0083) whose default list carries the pinned default. Scalar settings
    keys (``base_language``) are not roles and are skipped."""
    doc = yaml.safe_load((repo_root / MODELS).read_text(encoding="utf-8"))
    roles: dict[str, str | None] = {}
    if not isinstance(doc, dict):
        return roles
    for role, entries in doc.items():
        if isinstance(entries, dict) and "default" in entries:
            entries = entries.get("default")
        if isinstance(entries, list) and entries and isinstance(entries[0], dict):
            roles[str(role)] = entries[0].get("name")
    return roles


def check_model_roles(repo_root: pathlib.Path) -> list[str]:
    """CHECK 1: every models.yaml role + its default entry name is in ARCHITECTURE.md."""
    arch = _read(repo_root, ARCHITECTURE)
    if arch is None:
        return [f"{ARCHITECTURE} is missing"]
    findings: list[str] = []
    for role, default_name in sorted(model_roles(repo_root).items()):
        if f"`{role}`" not in arch:
            findings.append(
                f"model role `{role}` (config/models.yaml) is not named in {ARCHITECTURE}"
            )
        if default_name and default_name not in arch:
            findings.append(
                f"role `{role}` default entry {default_name!r} is not named in {ARCHITECTURE}"
            )
    return findings


def top_level_packages(repo_root: pathlib.Path) -> list[str]:
    root = repo_root / SRC_ROOT
    return sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "__init__.py").is_file())


def check_subsystems(repo_root: pathlib.Path) -> list[str]:
    """CHECK 2: every top-level src/kripos package is named in ARCHITECTURE.md + AGENTS.md."""
    findings: list[str] = []
    packages = top_level_packages(repo_root)
    for rel in (ARCHITECTURE, AGENTS):
        text = _read(repo_root, rel)
        if text is None:
            findings.append(f"{rel} is missing")
            continue
        for pkg in packages:
            if not re.search(rf"(?:\b{re.escape(pkg)}/|kripos\.{re.escape(pkg)}\b)", text):
                findings.append(f"package src/kripos/{pkg}/ is not named in {rel}")
    return findings


def check_readme_quickstart(repo_root: pathlib.Path) -> list[str]:
    """CHECK 3: README make targets exist in the Makefile; README CLIs exist in
    pyproject [project.scripts]."""
    readme = _read(repo_root, README)
    makefile = _read(repo_root, MAKEFILE)
    if readme is None:
        return [f"{README} is missing"]
    if makefile is None:
        return [f"{MAKEFILE} is missing"]
    findings: list[str] = []
    spans = _code_spans(readme)
    defined_targets = set(_MAKEFILE_TARGET_RE.findall(makefile))
    for target in sorted(set(_MAKE_TARGET_REF_RE.findall(spans))):
        if target not in defined_targets:
            findings.append(
                f"README references `make {target}` but the Makefile has no such target"
            )

    pyproject = tomllib.loads((repo_root / PYPROJECT).read_text(encoding="utf-8"))
    scripts = set(pyproject.get("project", {}).get("scripts", {}))
    for cli in sorted(set(_CLI_REF_RE.findall(spans)) - _CLI_IGNORE):
        if cli not in scripts:
            findings.append(
                f"README references CLI {cli!r} but pyproject [project.scripts] does not define it"
            )
    return findings


def check_all(repo_root: pathlib.Path | None = None) -> list[str]:
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    return (
        check_model_roles(repo_root)
        + check_subsystems(repo_root)
        + check_readme_quickstart(repo_root)
    )


def main() -> int:
    findings = check_all()
    for f in findings:
        print(f"[entrypoint-docs] {f}")
    print(f"\n{len(findings)} entrypoint-doc finding(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
