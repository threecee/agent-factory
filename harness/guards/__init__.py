"""Factory guard rules — one module per mechanism under ``rules/`` (harness/guards.md §3).

The rule-module contract, in five lines:

  ID                   the switch name (``FACTORY_GUARD_ALLOW=<ID>``) and the log key
  EVENTS               the harness events the rule answers (a set of event names)
  MATCHER              a tool name, a set of tool names, or ``None`` for tool-less events
  HONORS_ALLOW         optional, ``True`` when the rule reads its own switch and decides —
                       a switch that is a precondition, or none at all; the dispatcher then
                       calls it even when it is switched off
  check(payload, context) -> Verdict     and     falsification_cases(workdir) -> list

Package-relative imports only (``from guards._common import …``), so the directory can be
copied under ``scripts/`` unchanged: the entry script puts the package's parent on
``sys.path`` and nothing here assumes a repository layout.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import ModuleType

REQUIRED_ATTRIBUTES = ("ID", "EVENTS", "check")


def rules_directory(rules_dir: "str | pathlib.Path | None" = None) -> pathlib.Path:
    if rules_dir:
        return pathlib.Path(rules_dir)
    return pathlib.Path(__file__).resolve().parent / "rules"


def load_report(
    rules_dir: "str | pathlib.Path | None" = None,
) -> "tuple[list[ModuleType], list[str]]":
    """Every rule module under ``rules/`` (sorted by file name) plus the problems found.

    A module that fails to import, or lacks ``ID``/``EVENTS``/``check``, is skipped and
    named in the problem list; the dispatcher reports each problem as a context note
    (fail-open), never as a crash and never as a denial.
    """
    directory = rules_directory(rules_dir)
    modules: list[ModuleType] = []
    problems: list[str] = []
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        name = f"{__name__}.rules.{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"no loader for {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        except Exception as error:  # noqa: BLE001 — a broken rule must never take the hook down
            sys.modules.pop(name, None)
            problems.append(f"rule module {path.name} could not be imported ({error}) and was skipped")
            continue
        missing = [attribute for attribute in REQUIRED_ATTRIBUTES if not hasattr(module, attribute)]
        if missing:
            problems.append(f"rule module {path.name} lacks {', '.join(missing)} and was skipped")
            continue
        modules.append(module)
    return modules, problems


def load_rules(rules_dir: "str | pathlib.Path | None" = None) -> "list[ModuleType]":
    return load_report(rules_dir)[0]
