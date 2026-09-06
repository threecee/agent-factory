"""Locate and import a gate script for a rule that reads one (verification/protections.md).

The landing rule runs the ledger lint (``check_choices_protocol``) and the close-out rule
runs ``check_landing_closeout``; both live with the other gates, which an installed
repository keeps under ``scripts/`` and this package under ``verification/gates/``. The
search order is ``FACTORY_GUARD_GATES_DIR`` (a §8 parameter), then ``<repo>/scripts``, then
``<repo>/verification/gates``, then the package's own ``verification/gates`` when the two
directories are still side by side. A gate that is not found is reported by the caller as
a loud context note, never as a crash and never as a denial (harness/guards.md §3).

Underscore-prefixed, so the rule loader skips this module.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from collections.abc import Mapping
from types import ModuleType

GATES_DIR_VAR = "FACTORY_GUARD_GATES_DIR"
_PACKAGE = pathlib.Path(__file__).resolve().parents[1]  # …/guards
# The kit keeps the package at harness/guards and the gates at verification/gates; a copy
# that keeps guards/ and verification/gates side by side (the package tests) is found too.
_PACKAGE_GATES = (
    _PACKAGE.parents[1] / "verification" / "gates",
    _PACKAGE.parent / "verification" / "gates",
    _PACKAGE.parent / "scripts",
)


def candidate_dirs(environ: Mapping[str, str], repo_root: pathlib.Path) -> list[pathlib.Path]:
    configured = environ.get(GATES_DIR_VAR)
    dirs: list[pathlib.Path] = []
    if configured:
        dirs.append(pathlib.Path(configured).expanduser())
    dirs += [repo_root / "scripts", repo_root / "verification" / "gates", *_PACKAGE_GATES]
    return dirs


def find_gate(environ: Mapping[str, str], repo_root: pathlib.Path, name: str) -> pathlib.Path | None:
    for directory in candidate_dirs(environ, repo_root):
        path = directory / f"{name}.py"
        if path.is_file():
            return path
    return None


def load_gate(environ: Mapping[str, str], repo_root: pathlib.Path, name: str) -> ModuleType | None:
    """Import ``<name>.py`` from the first directory that has it; ``None`` when absent.

    The gate's directory is put on ``sys.path`` under the package name ``scripts`` when no
    such package is importable yet, so a gate that imports a sibling as
    ``scripts.<module>`` (the documented invocation form) resolves it from the same
    directory."""
    path = find_gate(environ, repo_root, name)
    if path is None:
        return None
    module_name = f"factory_gate_{name}"
    cached = sys.modules.get(module_name)
    if cached is not None and getattr(cached, "__file__", None) == str(path):
        return cached
    parent = str(path.parent.parent)
    if "scripts" not in sys.modules and path.parent.name == "scripts" and parent not in sys.path:
        sys.path.insert(0, parent)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
