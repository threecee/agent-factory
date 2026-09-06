#!/usr/bin/env python3
"""One dispatcher for every factory guard (harness/guards.md §3).

Usage — fed by an adapter (``harness/adapters/factory_guard.py`` routes here; the adapter
table is guards.md §9)::

    python3 harness/guards/guard_dispatch.py <event>          # hook payload as JSON on stdin
    python3 harness/guards/guard_dispatch.py falsify --lane <lane> --out <dir>

Exit codes: ``0`` allow or context, ``2`` deny (the refusal text on stderr). ``falsify``:
``0`` when every planted violation went red and every green form stayed silent, ``1`` on
any ``FAIL``; it writes ``<out>/<lane>-guard-falsification.log`` (guards.md §11).

The dispatcher reads the payload from stdin and the event from ``argv[1]`` (falling back to
the payload's ``hook_event_name``), resolves the switches (§4) from four logged sources,
runs every rule registered for the event (§3), writes one JSON line per invocation to
``FACTORY_GUARD_LOG`` and one events-log line per denial and per switch use to the state
directory (§3), and answers the harness:

* any ``deny`` → the refusal on stderr, exit 2 (the harness blocks the tool call);
* otherwise every ``context`` note → ``hookSpecificOutput.additionalContext`` JSON on
  stdout for harness events, plain text on stderr for the git pseudo-events (git has no
  JSON channel; the driver is verification/protections.md, introduced by PR13), exit 0;
* a rule that raises never locks the session out: it is logged and reported as context
  (``<id> failed and let the call through (<error>)``), never as a denial.

The state directory is ``FACTORY_GUARD_STATE_DIR``, else ``.factory-guard/`` in the
*primary* checkout (the parent of ``git rev-parse --git-common-dir``) so every linked
worktree, a session started in a worktree and the git hooks share one allow file and one
events log. Tests MUST set the override or they write into the primary's log.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import traceback
from collections.abc import Mapping
from types import ModuleType
from typing import IO

if __package__ in (None, ""):  # run as a script: make ``guards`` importable
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from guards import load_report, rules_directory  # noqa: E402
from guards._common import (  # noqa: E402
    ALLOW_FILE,
    FalsificationCase,
    GuardContext,
    Verdict,
    append_event,
    command_of,
    leading_assignments,
    payload_cwd,
    session_of,
    utc_now,
)

# Harness events whose context channel is ``hookSpecificOutput.additionalContext`` (§2).
CONTEXT_EVENTS = frozenset(
    {
        "SessionStart",
        "SubagentStart",
        "UserPromptSubmit",
        "UserPromptExpansion",
        "PreToolUse",
        "PostToolUse",
        "PostToolUseFailure",
        "PostToolBatch",
        "Stop",
        "SubagentStop",
        "PostModelSwitch",
    }
)
# Git-hook pseudo-events fed by the git-hook driver (PR13). Git has no JSON channel: a context
# note is plain text on stderr (exit 0), a refusal stderr + exit 2 as everywhere else.
GIT_EVENTS = frozenset({"GitPreCommit", "GitCommitMsg", "GitPrePush"})
_EXPORT_RE = re.compile(r"^\s*(?:export\s+)?(FACTORY_GUARD_[A-Z_]+)=['\"]?([^'\"\n]*)['\"]?\s*$")
PACKAGE_DIR = pathlib.Path(__file__).resolve().parent
SWITCHED_OFF = "switched off"


def _git_toplevel(cwd: pathlib.Path) -> pathlib.Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    top = (result.stdout or "").strip()
    return pathlib.Path(top) if result.returncode == 0 and top else None


def repo_root_from(environ: Mapping[str, str]) -> pathlib.Path:
    """``FACTORY_GUARD_DIR``'s parent-of-parent (``<repo>/harness/guards`` or
    ``<repo>/scripts/guards``), else ``CLAUDE_PROJECT_DIR``, else the checkout the current
    directory is in, else the tree this file lives in."""
    guards_dir = environ.get("FACTORY_GUARD_DIR")
    if guards_dir:
        return pathlib.Path(guards_dir).expanduser().resolve().parents[1]
    configured = environ.get("CLAUDE_PROJECT_DIR")
    if configured:
        return pathlib.Path(configured).expanduser().resolve()
    return _git_toplevel(pathlib.Path.cwd()) or PACKAGE_DIR.parents[1]


def primary_root(repo_root: pathlib.Path) -> pathlib.Path | None:
    """The primary checkout that ``repo_root`` belongs to (the parent of ``git rev-parse
    --git-common-dir``; ``repo_root`` itself when it is the primary), or ``None`` outside a
    repository or without git. Never raises: a guard that cannot find its state directory
    falls back to the tree it runs in rather than locking the session out."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    common = (result.stdout or "").strip()
    if result.returncode != 0 or not common:
        return None
    common_dir = pathlib.Path(common)
    if not common_dir.is_absolute():
        common_dir = (repo_root / common_dir).resolve()
    return common_dir.parent


def state_dir_from(environ: Mapping[str, str], repo_root: pathlib.Path) -> pathlib.Path:
    """``FACTORY_GUARD_STATE_DIR``, else ``.factory-guard/`` in the primary checkout — one
    directory for every worktree and every adapter (harness and git alike)."""
    configured = environ.get("FACTORY_GUARD_STATE_DIR")
    if configured:
        return pathlib.Path(configured).expanduser()
    return (primary_root(repo_root) or repo_root) / ".factory-guard"


def log_path_from(environ: Mapping[str, str], repo_root: pathlib.Path) -> pathlib.Path:
    configured = environ.get("FACTORY_GUARD_LOG")
    return pathlib.Path(configured).expanduser() if configured else repo_root / ".factory-guard.log"


def env_file_switches(environ: Mapping[str, str]) -> dict[str, str]:
    """``FACTORY_GUARD_*`` export lines the harness wrote to its env file (``CLAUDE_ENV_FILE``)
    mid-session; last wins."""
    path = environ.get("CLAUDE_ENV_FILE")
    if not path:
        return {}
    try:
        lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    found: dict[str, str] = {}
    for line in lines:
        match = _EXPORT_RE.match(line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def _split_ids(value: str | None) -> set[str]:
    return {part.strip() for part in (value or "").split(",") if part.strip()}


def resolve_switches(
    payload: Mapping[str, object], environ: Mapping[str, str], state_dir: pathlib.Path
) -> tuple[bool, frozenset[str], list[str]]:
    """``(disabled, allowed rule ids, where each switch came from)`` — the four sources of
    guards.md §4, every one of them named in the log record."""
    merged = {**environ, **env_file_switches(environ)}
    sources: list[str] = []
    disabled = merged.get("FACTORY_GUARD_DISABLED") == "1"
    if disabled:
        sources.append("FACTORY_GUARD_DISABLED=1")
    allowed = _split_ids(merged.get("FACTORY_GUARD_ALLOW"))
    if allowed:
        origin = "env-file" if "FACTORY_GUARD_ALLOW" in env_file_switches(environ) else "env"
        sources.append(f"{origin}:FACTORY_GUARD_ALLOW=" + ",".join(sorted(allowed)))
    prefixed = _split_ids(leading_assignments(command_of(payload)).get("FACTORY_GUARD_ALLOW"))
    if prefixed:
        sources.append("prefix:FACTORY_GUARD_ALLOW=" + ",".join(sorted(prefixed)))
    allowed |= prefixed
    try:
        from_file = {
            line.strip()
            for line in (state_dir / ALLOW_FILE).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
    except OSError:
        from_file = set()
    if from_file:
        sources.append(f"file:{ALLOW_FILE}=" + ",".join(sorted(from_file)))
    return disabled, frozenset(allowed | from_file), sources


def _matches(rule: ModuleType, event: str, payload: Mapping[str, object]) -> bool:
    if event not in rule.EVENTS:
        return False
    matcher = getattr(rule, "MATCHER", None)
    if matcher is None:
        return True
    tool = payload.get("tool_name")
    if isinstance(matcher, str):
        return tool == matcher
    return tool in matcher


def _run_rule(rule: ModuleType, payload: Mapping[str, object], context: GuardContext) -> Verdict:
    rule_id = getattr(rule, "ID", None) or getattr(rule, "__name__", "?")
    if context.switched_off(rule_id) and not getattr(rule, "HONORS_ALLOW", False):
        return Verdict("allow", rule_id, SWITCHED_OFF)
    try:
        verdict = rule.check(payload, context)
        return verdict if verdict.id else Verdict(verdict.kind, rule_id, verdict.message)
    except Exception as error:  # noqa: BLE001 — a crashing guard must never lock the session out
        detail = "".join(traceback.format_exception_only(type(error), error)).strip()
        return Verdict(
            "context",
            rule_id,
            f"GUARD {rule_id} failed and let the call through ({detail}). "
            "Fix it before it counts as standard (harness/guards.md §3).",
        )


def _log(path: pathlib.Path, record: Mapping[str, object]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass


def _emit(event: str, verdicts: list[Verdict], stdout: IO[str], stderr: IO[str]) -> int:
    denials = [verdict for verdict in verdicts if verdict.kind == "deny"]
    if denials:
        stderr.write("\n\n".join(verdict.message for verdict in denials) + "\n")
        return 2
    notes = [verdict.message for verdict in verdicts if verdict.kind == "context"]
    if notes:
        _write_notes(event, notes, stdout, stderr)
    return 0


def _write_notes(event: str, notes: list[str], stdout: IO[str], stderr: IO[str]) -> None:
    """Harness events get ``additionalContext`` JSON on stdout; git pseudo-events plain stderr;
    any other event has no context channel and the notes stay in the log."""
    if event in CONTEXT_EVENTS:
        stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": "\n\n".join(notes),
                    }
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    elif event in GIT_EVENTS:
        stderr.write("\n\n".join(notes) + "\n")


def _load_payload(stdin: IO[str]) -> dict[str, object]:
    try:
        payload = json.load(stdin)
    except (json.JSONDecodeError, OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _record(event: str, payload: Mapping[str, object], sources: list[str]) -> dict[str, object]:
    git_info = payload.get("git")
    return {
        "ts": utc_now(),
        "session": session_of(payload),
        "event": event,
        "tool": payload.get("tool_name"),
        "cwd": payload_cwd(payload),
        "command": command_of(payload)[:200],
        "git_hook": git_info.get("hook") if isinstance(git_info, Mapping) else None,
        "switches": sources,
        "verdicts": {},
    }


def _run_rules(
    rules: list[ModuleType], event: str, payload: Mapping[str, object], context: GuardContext
) -> list[Verdict]:
    return [_run_rule(rule, payload, context) for rule in rules if _matches(rule, event, payload)]


def _record_events(
    state_dir: pathlib.Path, session: str, event: str, verdicts: list[Verdict], sources: list[str]
) -> None:
    """The events log: one line per denial and per switch that silenced a rule."""
    for verdict in verdicts:
        if verdict.kind == "deny":
            append_event(state_dir, session, event, "deny", verdict.id, verdict.message)
        elif verdict.message == SWITCHED_OFF:
            append_event(state_dir, session, event, "allow-switch", verdict.id, "; ".join(sources))


def dispatch(
    event: str,
    payload: Mapping[str, object],
    *,
    stdout: IO[str],
    stderr: IO[str],
    environ: Mapping[str, str],
    rules: list[ModuleType] | None = None,
) -> int:
    repo_root = repo_root_from(environ)
    state_dir = state_dir_from(environ, repo_root)
    disabled, allowed, sources = resolve_switches(payload, environ, state_dir)
    record = _record(event, payload, sources)
    log_path = log_path_from(environ, repo_root)
    if disabled:
        record["verdicts"] = {"*": "disabled"}
        _log(log_path, record)
        return 0
    problems: list[str] = []
    if rules is None:
        rules, problems = load_report()
    context = GuardContext(
        event=event, repo_root=repo_root, state_dir=state_dir, environ=environ, allowed=allowed
    )
    verdicts = [Verdict("context", "loader", f"GUARD loader: {p} (harness/guards.md §3).") for p in problems]
    verdicts += _run_rules(rules, event, payload, context)
    record["verdicts"] = {
        verdict.id: ("switched" if verdict.message == SWITCHED_OFF else verdict.kind)
        for verdict in verdicts
    }
    record["messages"] = [verdict.message for verdict in verdicts if verdict.kind != "allow"]
    _log(log_path, record)
    _record_events(state_dir, session_of(payload), event, verdicts, sources)
    return _emit(event, verdicts, stdout, stderr)


# --- falsify: replay every rule's cases through the REAL entry script -------------------


def entry_script(environ: Mapping[str, str], package_dir: pathlib.Path) -> pathlib.Path:
    """``FACTORY_GUARD_ENTRY``, else the adapter beside the package
    (``<package>/../adapters/factory_guard.py``)."""
    configured = environ.get("FACTORY_GUARD_ENTRY")
    if configured:
        return pathlib.Path(configured).expanduser()
    return package_dir.parent / "adapters" / "factory_guard.py"


def _case_env(
    environ: Mapping[str, str], package_dir: pathlib.Path, out: pathlib.Path, lane: str
) -> dict[str, str]:
    env = dict(environ)
    for key in ("FACTORY_GUARD_ALLOW", "FACTORY_GUARD_DISABLED", "CLAUDE_ENV_FILE"):
        env.pop(key, None)
    env.update(
        {
            "FACTORY_GUARD_DIR": str(package_dir),
            "FACTORY_GUARD_STATE_DIR": str(out / f"{lane}-guard-state"),
            "FACTORY_GUARD_LOG": str(out / f"{lane}-guard-falsify.jsonl"),
            "FACTORY_GUARD_OFFLINE": "1",
        }
    )
    return env


def judge(case: FalsificationCase, result: subprocess.CompletedProcess[str]) -> tuple[bool, str]:
    """Exit code AND the needle in the RIGHT stream (falsification.md rule 2: the message)."""
    if case.expect == "deny":
        ok = result.returncode == 2 and case.needle in result.stderr
        return ok, f"exit {result.returncode}; stderr: {result.stderr.strip()[:160]!r}"
    if case.expect == "context":
        stream = result.stdout if case.event in CONTEXT_EVENTS else result.stderr
        ok = result.returncode == 0 and case.needle in stream
        return ok, f"exit {result.returncode}; output: {stream.strip()[:160]!r}"
    ok = result.returncode == 0 and "additionalContext" not in result.stdout and not result.stderr
    return ok, f"exit {result.returncode}; silent={not (result.stdout.strip() or result.stderr.strip())}"


def falsify(
    lane: str,
    out: pathlib.Path,
    rules_dir: pathlib.Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    stdout: IO[str] | None = None,
) -> int:
    environ = os.environ if environ is None else environ
    stdout = sys.stdout if stdout is None else stdout
    directory = rules_directory(rules_dir)
    package_dir = directory.parent
    entry = entry_script(environ, package_dir)
    out = out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    workdir = out / f"{lane}-guard-work"
    rules, problems = load_report(directory)
    lines: list[str] = [f"GREEN {'FAIL':<4} loader/{p}" for p in problems]
    failures = len(problems)
    total = len(problems)
    env = _case_env(environ, package_dir, out, lane)
    for rule in rules:
        rule_work = workdir / rule.ID
        rule_work.mkdir(parents=True, exist_ok=True)
        for case in rule.falsification_cases(rule_work):
            teardown = case.setup() if case.setup else None
            try:
                result = subprocess.run(
                    [sys.executable, str(entry), case.event],
                    input=json.dumps(case.payload),
                    capture_output=True,
                    text=True,
                    check=False,
                    env={**env, **case.env},
                    cwd=str(out),
                    timeout=300,
                )
            finally:
                if teardown is not None:
                    teardown()
            ok, detail = judge(case, result)
            if ok and case.after is not None:
                problem = case.after()
                if problem:
                    ok, detail = False, f"{detail}; after: {problem}"
            colour = "RED" if case.expect == "deny" else "GREEN"
            status = "ok" if ok else "FAIL"
            lines.append(f"{colour:<5} {status:<4} {rule.ID}/{case.name}: {detail}")
            total += 1
            failures += 0 if ok else 1
    receipt = out / f"{lane}-guard-falsification.log"
    receipt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    stdout.write(
        f"{lane}: {total} cases, {total - failures} ok, {failures} FAIL over "
        f"{len(rules)} rule(s) through {entry} — {receipt}\n"
    )
    return 1 if failures else 0


def _falsify_main(argv: list[str], environ: Mapping[str, str], stdout: IO[str], stderr: IO[str]) -> int:
    lane: str | None = None
    out: str | None = None
    rules_dir: str | None = None
    rest = list(argv)
    while rest:
        flag = rest.pop(0)
        if flag == "--lane" and rest:
            lane = rest.pop(0)
        elif flag == "--out" and rest:
            out = rest.pop(0)
        elif flag == "--rules-dir" and rest:
            rules_dir = rest.pop(0)
        else:
            stderr.write(f"falsify: unknown or incomplete argument {flag!r}\n")
            return 2
    if not lane or not out:
        stderr.write("usage: guard_dispatch.py falsify --lane <lane> --out <dir> [--rules-dir <dir>]\n")
        return 2
    return falsify(
        lane,
        pathlib.Path(out),
        pathlib.Path(rules_dir) if rules_dir else None,
        environ=environ,
        stdout=stdout,
    )


def main(
    argv: list[str] | None = None,
    *,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
    stderr: IO[str] | None = None,
    environ: Mapping[str, str] | None = None,
    rules: list[ModuleType] | None = None,
) -> int:
    argv = sys.argv[1:] if argv is None else argv
    environ = os.environ if environ is None else environ
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    if argv and argv[0] == "falsify":
        return _falsify_main(argv[1:], environ, stdout, stderr)
    payload = _load_payload(stdin or sys.stdin)
    event = argv[0] if argv else str(payload.get("hook_event_name") or "")
    return dispatch(event, payload, stdout=stdout, stderr=stderr, environ=environ, rules=rules)


if __name__ == "__main__":
    raise SystemExit(main())
