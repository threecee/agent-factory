#!/usr/bin/env python3
"""Git-hook driver for the factory guards (verification/protections.md §1, mechanism M-10).

The tracked shims under ``verification/protections/githooks/`` exec::

    python3 verification/protections/git_hooks.py pre-commit|commit-msg|pre-push [args]

with git's cwd (the worktree) and git's stdin. The driver turns each hook into one dispatcher
pseudo-event — ``GitPreCommit``, ``GitCommitMsg`` (carrying the proposed message) and
``GitPrePush`` (carrying the parsed ``<local ref> <local sha> <remote ref> <remote sha>``
lines) — and runs ``guards.guard_dispatch.main`` over the same rule modules, switches
(``FACTORY_GUARD_DISABLED``/``FACTORY_GUARD_ALLOW`` from the environment and the state
directory's allow file — a git hook has no command prefix to read) and verdict log as the
harness hook. A refusal is exit 2 with the message on stderr (git aborts on any non-zero
exit); a WARN is plain text on stderr with exit 0. Git's ``--no-verify`` cannot be removed
here; the ``no-verify`` rule refuses that flag inside a hooked session.

    python3 verification/protections/git_hooks.py install [--hooks-dir <dir>]
        sets core.hooksPath once per repository (shared by every linked worktree) to the
        tracked shims — ``<toplevel>/.githooks`` when it exists, else the directory beside
        this driver — relative when inside the toplevel, absolute otherwise; chmod +x. A
        core.hooksPath that already points elsewhere (another tool's hooks) is replaced
        with one loud ``replacing core.hooksPath <old>`` line: chain the old hooks from the
        shims, or keep them with --hooks-dir.
    python3 verification/protections/git_hooks.py status
        exit 1 until installed and every shim is executable — the verdict the session-start
        reminder keys its GIT HOOKS line on (a foreign hooksPath is «not installed» too)

The shims locate this driver themselves (``FACTORY_PROTECTIONS_DIR``, the directory beside
theirs, ``<toplevel>/verification/protections``, ``<toplevel>/scripts/protections``), so a
copy of the shims under ``<toplevel>/.githooks`` works; a shim that finds no driver lets the
commit or push through with one loud line.

The guards package is located through ``FACTORY_GUARD_DIR``, else ``harness/guards`` beside
this package, else ``<toplevel>/harness/guards``, else ``<toplevel>/scripts/guards``; its
parent goes on ``sys.path``. Exit codes: 2 deny, 0 allow or WARN, 64 usage. Never runs the
verify portfolio; never called by a guard.
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import re
import subprocess
import sys
from collections.abc import Mapping

HERE = pathlib.Path(__file__).resolve().parent
HOOKS: tuple[str, ...] = ("pre-commit", "commit-msg", "pre-push")
EVENTS = {"pre-commit": "GitPreCommit", "commit-msg": "GitCommitMsg", "pre-push": "GitPrePush"}
TRACKED_HOOKS_DIR = ".githooks"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _git(cwd: pathlib.Path, *args: str) -> str | None:
    try:
        result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def toplevel(cwd: pathlib.Path) -> pathlib.Path:
    top = _git(cwd, "rev-parse", "--show-toplevel")
    return pathlib.Path(top) if top else cwd


def guards_dir(environ: Mapping[str, str], repo: pathlib.Path) -> pathlib.Path | None:
    configured = environ.get("FACTORY_GUARD_DIR")
    candidates = [pathlib.Path(configured).expanduser()] if configured else []
    candidates += [HERE.parents[1] / "harness" / "guards", repo / "harness" / "guards", repo / "scripts" / "guards"]
    for candidate in candidates:
        if (candidate / "guard_dispatch.py").is_file():
            return candidate.resolve()
    return None


def _dispatch(environ: Mapping[str, str], repo: pathlib.Path):
    package = guards_dir(environ, repo)
    if package is None:
        return None
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(package.parent))
    from guards import guard_dispatch  # noqa: PLC0415 — located at run time on purpose

    return guard_dispatch


def parse_ref_lines(text: str) -> list[dict[str, str]]:
    """``<local ref> <local sha> <remote ref> <remote sha>`` lines from git's pre-push stdin."""
    refs: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4 and _SHA_RE.match(parts[1]) and _SHA_RE.match(parts[3]):
            refs.append({"local_ref": parts[0], "local_sha": parts[1], "remote_ref": parts[2], "remote_sha": parts[3]})
    return refs


def payload_for(hook: str, args: list[str], stdin_text: str, cwd: pathlib.Path) -> dict[str, object]:
    info: dict[str, object] = {"hook": hook, "args": list(args)}
    if hook == "commit-msg" and args:
        try:
            info["message"] = pathlib.Path(args[0]).read_text(encoding="utf-8")
        except OSError:
            info["message"] = ""
    if hook == "pre-push":
        info["remote"] = args[0] if args else "origin"
        info["url"] = args[1] if len(args) > 1 else ""
        info["refs"] = parse_ref_lines(stdin_text)
    return {"hook_event_name": EVENTS[hook], "cwd": str(cwd), "session_id": f"git-{hook}", "git": info}


def run_hook(hook: str, args: list[str], *, stdin_text: str = "", environ: Mapping[str, str] | None = None) -> int:
    environ = os.environ if environ is None else environ
    cwd = toplevel(pathlib.Path(os.getcwd()))
    dispatcher = _dispatch(environ, cwd)
    if dispatcher is None:
        sys.stderr.write(
            "factory git hook: the guards package was not found (FACTORY_GUARD_DIR, harness/guards, "
            "scripts/guards) — nothing checked, the commit or push goes through (verification/protections.md §1)\n"
        )
        return 0
    payload = payload_for(hook, args, stdin_text, cwd)
    return dispatcher.main([EVENTS[hook]], stdin=io.StringIO(json.dumps(payload)), environ=environ)


def hooks_dir(repo: pathlib.Path, requested: str | None = None) -> pathlib.Path:
    if requested:
        return pathlib.Path(requested).expanduser().resolve()
    tracked = repo / TRACKED_HOOKS_DIR
    return tracked.resolve() if tracked.is_dir() else (HERE / "githooks").resolve()


def config_value(repo: pathlib.Path, directory: pathlib.Path) -> str:
    """Relative when the shims live inside the toplevel, absolute otherwise."""
    try:
        return directory.relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(directory)


def status_problems(repo: pathlib.Path, directory: pathlib.Path | None = None) -> list[str]:
    directory = directory or hooks_dir(repo)
    expected = config_value(repo, directory)
    configured = _git(repo, "config", "--get", "core.hooksPath")
    resolved = _resolved_hooks_path(repo, configured)
    problems: list[str] = []
    if resolved != directory.resolve():
        problems.append(f"core.hooksPath is «{configured or '(unset)'}», not {expected}")
    for hook in HOOKS:
        shim = directory / hook
        if not shim.is_file():
            problems.append(f"{shim} missing")
        elif not os.access(shim, os.X_OK):
            problems.append(f"{shim} not executable")
    return problems


def _resolved_hooks_path(repo: pathlib.Path, configured: str | None) -> pathlib.Path | None:
    if not configured:
        return None
    path = pathlib.Path(configured).expanduser()
    return (path if path.is_absolute() else repo / path).resolve()


def install(repo: pathlib.Path, directory: pathlib.Path | None = None) -> list[str]:
    directory = directory or hooks_dir(repo)
    value = config_value(repo, directory)
    steps: list[str] = []
    current = _git(repo, "config", "--get", "core.hooksPath")
    if current and _resolved_hooks_path(repo, current) != directory.resolve():
        steps.append(
            f"replacing core.hooksPath «{current}» — chain your existing hooks from the shims in "
            f"{value}, or keep them with --hooks-dir {current} (verification/protections.md §1)"
        )
    subprocess.run(["git", "-C", str(repo), "config", "core.hooksPath", value], check=True, timeout=30)
    steps.append(f"git config core.hooksPath {value}")
    for hook in HOOKS:
        shim = directory / hook
        if shim.is_file() and not os.access(shim, os.X_OK):
            shim.chmod(shim.stat().st_mode | 0o111)
            steps.append(f"chmod +x {shim}")
    return steps


def _status_command(repo: pathlib.Path, directory: pathlib.Path | None) -> int:
    problems = status_problems(repo, directory)
    for problem in problems:
        print(f"[HOOKS] {problem} — fix: python3 {HERE / 'git_hooks.py'} install (verification/protections.md §1)")
    if not problems:
        print(f"[hooks] core.hooksPath={config_value(repo, directory or hooks_dir(repo))}; {', '.join(HOOKS)} executable in {repo}")
    return 1 if problems else 0


def _install_command(repo: pathlib.Path, directory: pathlib.Path | None) -> int:
    for step in install(repo, directory):
        print(f"[hooks/install] {step}")
    return 0


def _hook_stdin(hook: str) -> str:
    if hook != "pre-push" or sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def _requested_dir(args: list[str]) -> str | None:
    for index, token in enumerate(args):
        if token == "--hooks-dir" and index + 1 < len(args):
            return args[index + 1]
        if token.startswith("--hooks-dir="):
            return token.partition("=")[2]
    return None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.stderr.write(__doc__ or "")
        return 64
    command, args = argv[0], argv[1:]
    repo = toplevel(pathlib.Path(os.getcwd()))
    if command == "status":
        requested = _requested_dir(args)
        return _status_command(repo, pathlib.Path(requested).resolve() if requested else None)
    if command == "install":
        requested = _requested_dir(args)
        return _install_command(repo, pathlib.Path(requested).resolve() if requested else None)
    if command not in EVENTS:
        sys.stderr.write(f"unknown hook «{command}»; known: {', '.join(HOOKS)}, status, install\n")
        return 64
    return run_hook(command, args, stdin_text=_hook_stdin(command))


if __name__ == "__main__":
    raise SystemExit(main())
