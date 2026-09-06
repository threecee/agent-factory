"""Lander close-out check (verification/lander-duties.md §8; mechanism M-13) — identical in
both landing modes.

After a registered landing the landing guard writes ``<state-dir>/landing-in-progress.json``
with the train, the receipt HEAD, the mode (``pr`` | ``direct-push``), the pull-request
number (pr mode), the boarders and the artifacts dir. This script reads that state and lists
the lander duties still open, every check written as CONTAINS, never equals (in pr mode the
default branch's tip is the merge commit, ``HEAD=`` its second parent):

  origin/<default> contains the landed HEAD          (ls-remote + merge-base --is-ancestor; «moved on» is a note)
  pr mode: the pull request reads MERGED             (gh pr view <n> --json state; offline = a note, never an invented duty)
  the remote train branch is deleted                 (both modes; fix: git push origin --delete train/<name>)
  the primary's HEAD contains the landed HEAD        (fix: git -C <primary> pull --ff-only origin <default>)
  no ``claimed`` registry row whose file is landed   (the drift leg of check_migration_heads; skipped without a registry)
  every worktree of the train or its boarders whose branch is merged into origin/<default> is reaped
                                                      (fix: unlink the ritual symlinks && worktree remove && branch -d)
  no listener in the port range with its cwd in the primary or those trees   (only with --port-range; lsof)
  disk free above the floor                          (only with --floor-gb)
  the build product is fresh                         (only with --build-check <command>; its exit code)

Exit 0 when every duty is closed, 1 with one ``[CLOSEOUT] [ ] <duty>. Fix: <command>`` line per
open duty, 2 when the apparatus is missing (no readable state, no git). The script never
performs a duty — no reap, no flip, no fast-forward, no deletion — it names the exact command.
The close-out Stop rule (harness/guards/rules/closeout.py) calls :func:`closeout` and delivers
the same lines.

    python3 -m scripts.check_landing_closeout --state <state file> [--primary <dir>] [--floor-gb N]
        [--port-range A-B] [--build-check <cmd>] [--default-branch main]

Planted falsifications the package test runs (verification/tests/test_landing_protections.sh
case 21): a merged, unreaped train tree → the reap duty naming unlink + remove; reaped → exit
0; pr mode with the pull request OPEN → duty; the remote train branch present → duty;
origin/main containing HEAD through a merge commit → no remote duty; the primary behind → the
ff duty; floor 0 → no disk duty.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass

Runner = Callable[..., subprocess.CompletedProcess[str]]
REGISTRY_PATH = pathlib.Path("docs/decisions/NUMBERS.md")
RITUAL_LINKS = (".venv", ".env", "frontend/node_modules", "node_modules")


@dataclass(frozen=True)
class Duty:
    text: str
    fix: str

    def line(self) -> str:
        return f"[ ] {self.text}. Fix: {self.fix}"


def _git(run: Runner, cwd: pathlib.Path, *args: str, timeout: float = 30.0) -> tuple[int, str]:
    try:
        result = run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as error:
        return 127, str(error)
    return result.returncode, (result.stdout or "").strip()


def primary_of(run: Runner, tree: pathlib.Path) -> pathlib.Path:
    code, common = _git(run, tree, "rev-parse", "--git-common-dir")
    if code != 0 or not common:
        return tree
    common_dir = pathlib.Path(common)
    if not common_dir.is_absolute():
        common_dir = (tree / common_dir).resolve()
    return common_dir.parent


def remote_duty(run: Runner, primary: pathlib.Path, head: str, branch: str) -> tuple[Duty | None, str | None]:
    code, _ = _git(run, primary, "fetch", "-q", "origin", timeout=120)
    if code != 0:
        return None, f"origin could not be fetched — origin/{branch} not verified"
    code, listing = _git(run, primary, "ls-remote", "origin", f"refs/heads/{branch}", timeout=60)
    if code != 0 or not listing:
        return None, f"origin/{branch} could not be read (git ls-remote failed) — not verified"
    remote = listing.split()[0]
    if remote == head:
        return None, None
    code, _ = _git(run, primary, "merge-base", "--is-ancestor", head, remote)
    if code == 0:
        return None, f"origin/{branch} has moved on to {remote[:8]} (it contains {head[:8]})"
    return (
        Duty(
            f"origin/{branch} ({remote[:8]}) does not contain the landed HEAD ({head[:8]})",
            f"git -C {primary} fetch origin && git -C {primary} log {head[:8]}..origin/{branch}",
        ),
        None,
    )


def _gh(run: Runner, cwd: pathlib.Path, *args: str) -> tuple[int, str]:
    try:
        result = run(["gh", *args], cwd=str(cwd), capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        return 127, str(error)
    return result.returncode, ((result.stdout or "") + (result.stderr or "")).strip()


def pr_duty(run: Runner, primary: pathlib.Path, state: Mapping[str, object], head: str, *, offline: bool) -> tuple[Duty | None, str | None]:
    if state.get("mode") != "pr":
        return None, None
    number = state.get("pr")
    if not number:
        return None, "pr mode without a pull-request number in the state — merge state not verified"
    if offline or shutil.which("gh") is None:
        return None, f"pull request #{number} not verified (offline)"
    code, _ = _gh(run, primary, "auth", "status")
    if code != 0:
        return None, f"pull request #{number} not verified (gh not authenticated)"
    code, output = _gh(run, primary, "pr", "view", str(number), "--json", "state", "--jq", ".state")
    if code != 0:
        return None, f"pull request #{number} not verified (gh pr view failed: {output[:80]})"
    if output.strip().upper() == "MERGED":
        return None, None
    return Duty(
        f"pull request #{number} is not merged (state {output.strip() or '?'})",
        f"gh pr merge {number} --merge --match-head-commit {head} (verification/landing-modes.md §4)",
    ), None


def remote_branch_duty(run: Runner, primary: pathlib.Path, train: str) -> Duty | None:
    if not train:
        return None
    code, listing = _git(run, primary, "ls-remote", "origin", f"refs/heads/train/{train}", timeout=60)
    if code != 0 or not listing:
        return None
    return Duty(f"remote branch train/{train} still exists on origin", f"git push origin --delete train/{train}")


def ff_duty(run: Runner, primary: pathlib.Path, head: str, branch: str) -> Duty | None:
    code, primary_head = _git(run, primary, "rev-parse", "HEAD")
    if code != 0:
        return None
    code, _ = _git(run, primary, "merge-base", "--is-ancestor", head, primary_head)
    if code == 0:
        return None
    return Duty(
        f"fast-forward the primary (primary {primary_head[:8]} does not contain {head[:8]})",
        f"git -C {primary} pull --ff-only origin {branch}",
    )


def _registry_module():
    try:
        from scripts import check_migration_heads  # type: ignore[import-not-found]

        return check_migration_heads
    except ImportError:
        pass
    sibling = pathlib.Path(__file__).resolve().parent / "check_migration_heads.py"
    if not sibling.is_file():
        return None
    spec = importlib.util.spec_from_file_location("factory_gate_check_migration_heads", sibling)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def registry_duties(primary: pathlib.Path) -> list[Duty]:
    if not (primary / REGISTRY_PATH).is_file():
        return []
    module = _registry_module()
    if module is None:
        return [Duty("the registry leg is unavailable (check_migration_heads.py not found)", "copy the gate beside this one")]
    try:
        rows = module.parse_number_registry(primary)
        problems = module.landed_claim_problems(primary, rows, "migration", module._migration_files(primary))
        adr_files = [
            (path.name[:4], path.relative_to(primary))
            for path in sorted((primary / "docs" / "decisions").glob("[0-9][0-9][0-9][0-9]-*.md"))
        ]
        problems += module.landed_claim_problems(primary, rows, "adr", adr_files)
    except Exception as error:  # noqa: BLE001 — the leg's own failure is a duty to look, not a crash
        return [Duty(f"the registry leg failed ({error})", "run python3 -m scripts.check_migration_heads")]
    return [Duty(f"registry: {problem}", f"flip the row claimed → landed in {REGISTRY_PATH}") for problem in problems]


def _worktrees(run: Runner, primary: pathlib.Path) -> list[tuple[pathlib.Path, str | None, str | None]]:
    code, listing = _git(run, primary, "worktree", "list", "--porcelain")
    if code != 0:
        return []
    entries: list[tuple[pathlib.Path, str | None, str | None]] = []
    path: pathlib.Path | None = None
    head: str | None = None
    branch: str | None = None
    for line in [*listing.splitlines(), ""]:
        if line.startswith("worktree "):
            path = pathlib.Path(line[9:])
        elif line.startswith("HEAD "):
            head = line[5:]
        elif line.startswith("branch "):
            branch = line[7:].removeprefix("refs/heads/")
        elif not line and path is not None:
            entries.append((path, head, branch))
            path, head, branch = None, None, None
    return entries


def train_trees(run: Runner, primary: pathlib.Path, train: str, boarders: Mapping[str, object]) -> list[tuple[pathlib.Path, str | None, str | None]]:
    lanes = {str(name) for name in boarders}
    chosen = []
    for path, head, branch in _worktrees(run, primary):
        if path.resolve() == primary.resolve():
            continue
        is_train = branch == f"train/{train}"
        is_boarder = branch is not None and (branch.removeprefix("lane/") in lanes or path.name in lanes)
        if is_train or is_boarder:
            chosen.append((path, head, branch))
    return chosen


def reap_duties(run: Runner, primary: pathlib.Path, train: str, boarders: Mapping[str, object], branch: str) -> list[Duty]:
    duties: list[Duty] = []
    for path, tree_head, tree_branch in train_trees(run, primary, train, boarders):
        if tree_head is None:
            continue
        code, _ = _git(run, primary, "merge-base", "--is-ancestor", tree_head, f"origin/{branch}")
        if code != 0:
            continue
        unlink = " ".join(str(path / name) for name in RITUAL_LINKS if (path / name).is_symlink())
        fix = (f"unlink {unlink} && " if unlink else "") + f"git -C {primary} worktree remove {path}"
        if tree_branch:
            fix += f" && git -C {primary} branch -d {tree_branch}"
        duties.append(Duty(f"reap {path} (branch {tree_branch or tree_head[:8]} is merged into origin/{branch})", fix))
    return duties


def _listener_rows(run: Runner, port_range: str) -> list[tuple[int, str]]:
    try:
        result = run(["lsof", "-nP", f"-iTCP:{port_range}", "-sTCP:LISTEN"], capture_output=True, text=True, check=False, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    rows: list[tuple[int, str]] = []
    for line in (result.stdout or "").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 9 and parts[1].isdigit():
            rows.append((int(parts[1]), parts[8]))
    return rows


def _cwd_of(run: Runner, pid: int) -> str | None:
    try:
        result = run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"], capture_output=True, text=True, check=False, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    for line in (result.stdout or "").splitlines():
        if line.startswith("n"):
            return line[1:]
    return None


def listener_duties(run: Runner, roots: list[pathlib.Path], port_range: str) -> list[Duty]:
    duties: list[Duty] = []
    resolved = [root.resolve() for root in roots]
    for pid, name in _listener_rows(run, port_range):
        cwd = _cwd_of(run, pid)
        if cwd is None:
            continue
        where = pathlib.Path(cwd).resolve()
        if any(where == root or root in where.parents for root in resolved):
            port = name.rsplit(":", 1)[-1].split()[0]
            duties.append(Duty(f"listener pid {pid} ({name}, cwd {cwd}) in the port range from the train's served instance", f"kill $(lsof -ti :{port})"))
    return duties


def disk_duty(primary: pathlib.Path, floor_gb: float | None) -> Duty | None:
    if floor_gb is None:
        return None
    try:
        free = shutil.disk_usage(primary).free / 1e9
    except OSError:
        return None
    if free >= floor_gb:
        return None
    return Duty(f"disk: {free:.0f} GB free < floor {floor_gb:.0f} GB", "reap footprints (instance copies in the bank, CLI temp dirs, old worktrees)")


def build_duty(run: Runner, primary: pathlib.Path, build_check: str | None) -> Duty | None:
    if not build_check:
        return None
    try:
        result = run(["/bin/sh", "-c", build_check], cwd=str(primary), capture_output=True, text=True, check=False, timeout=600)
    except (OSError, subprocess.SubprocessError) as error:
        return Duty(f"the build check could not run ({error})", build_check)
    if result.returncode == 0:
        return None
    return Duty("the build product in the primary is not fresh (the build check is red)", f"rebuild, then re-run: {build_check}")


def closeout(
    state: Mapping[str, object],
    primary: pathlib.Path,
    *,
    run: Runner = subprocess.run,
    floor_gb: float | None = None,
    port_range: str | None = None,
    build_check: str | None = None,
    offline: bool = False,
    environ: Mapping[str, str] | None = None,
) -> tuple[list[Duty], list[str]]:
    """``(open duties, notes)`` for one landing state."""
    environ = os.environ if environ is None else environ
    head = str(state.get("head") or "")
    train = str(state.get("train") or "")
    branch = str(state.get("default_branch") or environ.get("FACTORY_DEFAULT_BRANCH") or "main")
    boarders = state.get("boarders") if isinstance(state.get("boarders"), Mapping) else {}
    if not head:
        return [], ["the state file carries no head — nothing to check"]
    notes: list[str] = []
    remote, note = remote_duty(run, primary, head, branch)
    if note:
        notes.append(note)
    pull, note = pr_duty(run, primary, state, head, offline=offline)
    if note:
        notes.append(note)
    trees = train_trees(run, primary, train, boarders)
    candidates: list[Duty | None] = [
        remote,
        pull,
        remote_branch_duty(run, primary, train),
        ff_duty(run, primary, head, branch),
        *registry_duties(primary),
        *reap_duties(run, primary, train, boarders, branch),
        *(listener_duties(run, [primary, *(path for path, _, _ in trees)], port_range) if port_range else []),
        disk_duty(primary, floor_gb),
        build_duty(run, primary, build_check),
    ]
    return [duty for duty in candidates if duty is not None], notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--state", type=pathlib.Path, required=True)
    parser.add_argument("--primary", type=pathlib.Path, default=None)
    parser.add_argument("--floor-gb", type=float, default=None)
    parser.add_argument("--port-range", default=None)
    parser.add_argument("--build-check", default=None)
    parser.add_argument("--default-branch", default=None)
    args = parser.parse_args(argv)
    try:
        state = dict(json.loads(args.state.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as error:
        print(f"[CLOSEOUT] no readable state file ({error}) — the apparatus is missing")
        return 2
    if shutil.which("git") is None:
        print("[CLOSEOUT] git is not on PATH — the apparatus is missing")
        return 2
    if args.default_branch:
        state["default_branch"] = args.default_branch
    primary = (args.primary or primary_of(subprocess.run, pathlib.Path.cwd())).resolve()
    duties, notes = closeout(
        state,
        primary,
        floor_gb=args.floor_gb,
        port_range=args.port_range,
        build_check=args.build_check,
        offline=os.environ.get("FACTORY_GUARD_OFFLINE") == "1",
    )
    for note in notes:
        print(f"[closeout] {note}")
    for duty in duties:
        print(f"[CLOSEOUT] {duty.line()}")
    if not duties:
        print(f"[closeout] train {state.get('train')}: every lander duty closed")
    return 1 if duties else 0


if __name__ == "__main__":
    sys.exit(main())
