"""Alembic single-head and migration-number registry gate (ADR-0071).

Closes the implicit-single-head gap: today a single head only falls out as a side
effect of `command.upgrade(cfg, "head")` succeeding. Make it explicit and
machine-checked — assert exactly one head in the migration graph, so a divergent
migration branch (two heads) fails the gate instead of surfacing later as a
non-deterministic upgrade order.

The registry leg checks every numbered migration file against
docs/decisions/NUMBERS.md. Active claims make allocations visible across
branches; duplicate allocations and unregistered tree files are hard findings,
while a claimed number owned by another branch is reported as a warning.

    python -m scripts.check_migration_heads          # exit 1 if != 1 head
    python -m scripts.check_migration_heads --report  # print heads, exit 0
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
from collections import Counter
from typing import Literal, NamedTuple

ALEMBIC_INI = "alembic.ini"
MIGRATIONS_DIR = "migrations"
NUMBERS_PATH = pathlib.Path("docs/decisions/NUMBERS.md")
_ACTIVE_STATUSES = {"claimed", "landed"}
_MIGRATION_RE = re.compile(r"^(\d{4})_.*\.py$")


class NumberRow(NamedTuple):
    """One allocation row from the shared number ledger."""

    kind: Literal["migration", "adr"]
    number: str
    owner: str
    date: str
    status: str
    note: str


def parse_number_registry(repo_root: pathlib.Path) -> list[NumberRow]:
    """Parse allocation rows, ignoring prose and non-ledger table rows."""
    rows: list[NumberRow] = []
    text = (repo_root / NUMBERS_PATH).read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0] not in {"migration", "adr"}:
            continue
        rows.append(NumberRow(cells[0], *cells[1:6]))
    return rows


def _migration_files(repo_root: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    versions = repo_root / MIGRATIONS_DIR / "versions"
    files: list[tuple[str, pathlib.Path]] = []
    for path in sorted(versions.glob("*.py")):
        match = _MIGRATION_RE.match(path.name)
        if match:
            files.append((match.group(1), path.relative_to(repo_root)))
    return files


def _duplicate_problems(rows: list[NumberRow], kind: str) -> list[str]:
    counts = Counter(row.number for row in rows if row.kind == kind)
    return [
        f"duplicate {kind} number {number} in {NUMBERS_PATH}; each (kind, number) "
        "allocation must appear only once"
        for number, count in sorted(counts.items())
        if count > 1
    ]


def _missing_claim_message(kind: str, number: str, path: pathlib.Path) -> str:
    return (
        f"{NUMBERS_PATH} has no active {kind} claim for {number}, used by {path}; "
        f"claim the number by landing a one-line addition to {NUMBERS_PATH} on main first"
    )


def _git_ok(repo_root: pathlib.Path, *args: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args], capture_output=True, text=True, check=False
        )
    except OSError:
        return False
    return result.returncode == 0


def _landed_refs(repo_root: pathlib.Path) -> list[str]:
    """The refs that mean "on the default branch" here: ``origin/<default>`` and/or a local
    ``<default>`` (``FACTORY_GUARD_DEFAULT_BRANCH``, default ``main``)."""
    branch = os.environ.get("FACTORY_GUARD_DEFAULT_BRANCH") or "main"
    return [
        ref
        for ref in (f"origin/{branch}", branch)
        if _git_ok(repo_root, "rev-parse", "--verify", "-q", ref)
    ]


def landed_claim_problems(
    repo_root: pathlib.Path,
    rows: list[NumberRow],
    kind: str,
    tree_files: list[tuple[str, pathlib.Path]],
) -> list[str]:
    """The drift leg (software-factory-kit deviation two, 2026-09; verification/protections.md §7,
    mechanism M-8): a ``claimed`` row whose numbered file is already on the default branch
    must be flipped — ``[HARD] claimed <kind> number NNNN is landed on main; flip the row``.

    On a lane branch where the file exists only locally the leg is silent — that is the
    normal claim state. Outside git (fixture trees) it is silent too. No switch: the fix is
    the flip, never the row.
    """
    refs = _landed_refs(repo_root)
    if not refs:
        return []
    by_number = dict(tree_files)
    return [
        f"claimed {kind} number {row.number} is landed on main; flip the row to landed in "
        f"{NUMBERS_PATH} ({path.as_posix()})"
        for row in rows
        if row.kind == kind
        and row.status == "claimed"
        and (path := by_number.get(row.number)) is not None
        and any(_git_ok(repo_root, "cat-file", "-e", f"{ref}:{path.as_posix()}") for ref in refs)
    ]


def migration_registry_problems(repo_root: pathlib.Path | None = None) -> list[str]:
    """Hard migration registry findings. Empty means every tree number is registered."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    try:
        rows = parse_number_registry(repo_root)
    except FileNotFoundError:
        return [f"missing required number allocation ledger: {NUMBERS_PATH}"]
    problems = _duplicate_problems(rows, "migration")
    active = {
        row.number for row in rows if row.kind == "migration" and row.status in _ACTIVE_STATUSES
    }
    tree_files = _migration_files(repo_root)
    for number, path in tree_files:
        if number not in active:
            problems.append(_missing_claim_message("migration", number, path))
    problems += landed_claim_problems(repo_root, rows, "migration", tree_files)
    return problems


def _current_branch(repo_root: pathlib.Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    branch = result.stdout.strip()
    return branch if result.returncode == 0 and branch and branch != "HEAD" else None


def _registry_warnings(
    repo_root: pathlib.Path, rows: list[NumberRow], kind: str, tree_numbers: set[str]
) -> list[str]:
    branch = _current_branch(repo_root)
    if branch is None:
        return []
    return [
        f"{kind} number {row.number} is present in this tree but claimed by {row.owner}, "
        f"not current branch {branch}"
        for row in rows
        if row.kind == kind
        and row.status == "claimed"
        and row.number in tree_numbers
        and row.owner != branch
    ]


def migration_registry_warnings(repo_root: pathlib.Path | None = None) -> list[str]:
    """Non-failing cross-branch ownership warnings for migration claims."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    try:
        rows = parse_number_registry(repo_root)
    except FileNotFoundError:
        return []
    return _registry_warnings(
        repo_root, rows, "migration", {number for number, _path in _migration_files(repo_root)}
    )


def migration_registry_counts(repo_root: pathlib.Path | None = None) -> tuple[int, int]:
    """(active registered migration numbers, numbered migration files checked)."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    try:
        rows = parse_number_registry(repo_root)
    except FileNotFoundError:
        rows = []
    registered = {
        row.number for row in rows if row.kind == "migration" and row.status in _ACTIVE_STATUSES
    }
    return len(registered), len(_migration_files(repo_root))


def get_heads(repo_root: pathlib.Path | None = None) -> list[str]:
    """Return the alembic revision heads for the repo's migration graph."""
    # Imported here, not at module top: the NUMBERS-registry helpers this module
    # exports to check_backlog.py have no alembic dependency, and a repository
    # without migrations must be able to run those without installing alembic
    # (software-factory-kit install trial, 2026-09-06). Logic unchanged.
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    cfg = Config(str(repo_root / ALEMBIC_INI))
    cfg.set_main_option("script_location", str(repo_root / MIGRATIONS_DIR))
    script = ScriptDirectory.from_config(cfg)
    return list(script.get_heads())


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    heads = get_heads()
    problems = migration_registry_problems()
    warnings = migration_registry_warnings()
    if len(heads) == 1:
        print(f"alembic single head OK: {heads[0]}")
    else:
        problems.insert(0, f"alembic has {len(heads)} head(s) (expected 1): {heads}")
        print(f"[HARD] alembic has {len(heads)} head(s) (expected 1): {heads}")
        print(
            "Multiple heads mean divergent migration branches — the upgrade order is no "
            "longer deterministic. Reconcile with `alembic merge <rev1> <rev2>`."
        )
    for problem in problems[(1 if len(heads) != 1 else 0) :]:
        print(f"[HARD] {problem}")
    for warning in warnings:
        print(f"[WARN] {warning}")
    return 0 if "--report" in argv else (1 if problems else 0)


if __name__ == "__main__":
    sys.exit(main())
