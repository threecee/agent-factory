"""Shared primitives for the guard rules (harness/guards.md §3).

Package-relative and standard library only: every rule module imports ``guards._common``
and nothing else, so the package runs under a bare ``python3`` wherever the two directories
(``guards/`` and ``adapters/``) are copied together, as long as the package's parent is on
``sys.path`` — the entry script puts it there.

Process identity (``process_table``, ``live_agents``, ``agents_writing_in``) is parameterized
by ``FACTORY_GUARD_CLI`` (the lane CLI's executable basename), ``FACTORY_GUARD_CLI_TOKEN``
(its exact headless verb as one argv token) and ``FACTORY_GUARD_CLI_DIR_FLAG`` (the flag whose
operand is the lane directory). Unbound, every process query answers "no lanes" — never a
text match over the command line (harness/run-lifecycle.md §6).
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

VerdictKind = Literal["allow", "deny", "context"]
_SEPARATORS = frozenset(";&|\n")
_PYTHON_RE = re.compile(r"^python(?:3(?:\.\d+)?)?$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_ENV_OPTIONS_WITH_OPERAND = frozenset({"-u", "--unset", "-C", "--chdir"})
_PYTHON_OPTIONS_WITH_OPERAND = frozenset({"-X", "-W"})

CLI_VAR = "FACTORY_GUARD_CLI"
CLI_TOKEN_VAR = "FACTORY_GUARD_CLI_TOKEN"
CLI_DIR_FLAG_VAR = "FACTORY_GUARD_CLI_DIR_FLAG"
EVENTS_FILE = "factory-events.log"
ALLOW_FILE = "factory-guard-allow"


@dataclass(frozen=True)
class Verdict:
    """One rule's answer for one hook invocation."""

    kind: VerdictKind
    id: str
    message: str = ""


ALLOW = Verdict("allow", "")


@dataclass(frozen=True)
class GuardContext:
    """What the dispatcher knows when it calls a rule."""

    event: str
    repo_root: pathlib.Path
    state_dir: pathlib.Path
    environ: Mapping[str, str]
    allowed: frozenset[str] = frozenset()
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run

    def switched_off(self, rule_id: str) -> bool:
        return rule_id in self.allowed


@dataclass(frozen=True)
class Statement:
    """One shell statement: a pipeline of segments plus the separator that ended it."""

    pipeline: tuple[tuple[str, ...], ...]
    terminator: str = ";"

    @property
    def first(self) -> tuple[str, ...]:
        return self.pipeline[0] if self.pipeline else ()


@dataclass(frozen=True)
class FalsificationCase:
    """A planted violation (``expect='deny'``), a note (``'context'``) or a green form
    (``'allow'``) replayed through the real entry script by ``guard_dispatch.py falsify``."""

    name: str
    event: str
    payload: dict[str, object]
    expect: VerdictKind
    needle: str = ""
    env: dict[str, str] = field(default_factory=dict)
    setup: Callable[[], Callable[[], None]] | None = None
    after: Callable[[], str | None] | None = None  # side-effect check: failure detail or None


_REDIRECTION_RE = re.compile(r"\d*>>?&\d+|&>>?|\d*<&\d+")
REDIRECTION = "__REDIR__"


def parse_statements(command: str) -> list[Statement]:
    """Split a shell command into statements and pipelines, honouring quotes.

    Redirection operators that contain ``&`` (``2>&1``, ``&>``) are replaced by the word
    ``__REDIR__`` first, so the ``&`` never reads as a statement separator.
    """
    normalized = _REDIRECTION_RE.sub(f" {REDIRECTION} ", command)
    try:
        lexer = shlex.shlex(normalized, posix=True, punctuation_chars=";&|\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []
    statements: list[Statement] = []
    pipeline: list[tuple[str, ...]] = []
    segment: list[str] = []
    for token in [*tokens, ";"]:
        if not (token and set(token) <= _SEPARATORS):
            segment.append(token)
            continue
        if segment:
            pipeline.append(tuple(segment))
        segment = []
        if _is_pipe(token):
            continue
        if pipeline:
            statements.append(Statement(tuple(pipeline), token))
        pipeline = []
    return statements


def _is_pipe(separator: str) -> bool:
    """``|`` (and ``|&``) continue a pipeline; ``;``, ``&``, ``&&``, ``||`` end it."""
    return separator in {"|", "|&"}


def strip_prefixes(tokens: Iterable[str]) -> list[str]:
    """Drop leading ``VAR=value`` assignments, ``command``, ``env`` and their options."""
    effective = list(tokens)
    while effective and _is_assignment(effective[0]):
        effective.pop(0)
    if effective and pathlib.PurePath(effective[0]).name == "command":
        effective.pop(0)
        while effective and effective[0].startswith("-"):
            effective.pop(0)
    if effective and pathlib.PurePath(effective[0]).name == "env":
        effective = _strip_env_options(effective[1:])
    return effective


def _strip_env_options(tokens: list[str]) -> list[str]:
    effective = list(tokens)
    while effective:
        option = effective[0]
        if option == "--":
            return effective[1:]
        if option in _ENV_OPTIONS_WITH_OPERAND:
            del effective[:2]
            continue
        if option.startswith("-") or _is_assignment(option):
            effective.pop(0)
            continue
        break
    return effective


def _is_assignment(token: str) -> bool:
    return "=" in token and not token.startswith("=") and token.split("=", 1)[0].isidentifier()


def leading_assignments(command: str) -> dict[str, str]:
    """``VAR=value`` pairs that prefix any statement of the command (first wins)."""
    found: dict[str, str] = {}
    for statement in parse_statements(command):
        for token in statement.first:
            if not _is_assignment(token):
                break
            name, _, value = token.partition("=")
            found.setdefault(name, value)
    return found


def basename(token: str) -> str:
    return pathlib.PurePath(token).name


def is_python(token: str) -> bool:
    return bool(_PYTHON_RE.match(basename(token)))


def invoked_target(tokens: Sequence[str]) -> str | None:
    """What a statement *runs*: its head, or the script path / ``-m`` module a python head runs.

    ``grep serve …`` and ``cat scripts/serve.py`` only *name* a program; a guard that gates
    invocations reads this instead of every token — mentions are never gated.
    """
    if not tokens:
        return None
    head = tokens[0]
    if not is_python(head):
        return head
    rest = list(tokens[1:])
    while rest and rest[0].startswith("-"):
        option = rest.pop(0)
        if option == "-m":
            return rest[0] if rest else None
        if option == "-c":
            return None
        if option in _PYTHON_OPTIONS_WITH_OPERAND and rest:
            rest.pop(0)
    return rest[0] if rest else None


def effective_cwd(command: str, payload_cwd: str | None) -> pathlib.Path:
    """The directory the last ``cd`` in the command leaves the shell in."""
    cwd = pathlib.Path(payload_cwd or os.getcwd())
    for statement in parse_statements(command):
        tokens = strip_prefixes(statement.first)
        if len(tokens) == 2 and basename(tokens[0]) == "cd":
            target = pathlib.Path(tokens[1]).expanduser()
            candidate = target if target.is_absolute() else cwd / target
            if candidate.is_dir():
                cwd = candidate.resolve()
    return cwd


def git(
    context: GuardContext, cwd: pathlib.Path, *args: str, timeout: float = 30.0
) -> tuple[int, str]:
    """Run git in ``cwd``; returns (returncode, stripped stdout) and never raises."""
    try:
        result = context.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return 127, str(error)
    return result.returncode, (result.stdout or "").strip()


def is_full_sha(value: str) -> bool:
    return bool(_SHA_RE.fullmatch(value))


def current_branch(context: GuardContext, cwd: pathlib.Path) -> str | None:
    code, branch = git(context, cwd, "rev-parse", "--abbrev-ref", "HEAD")
    return branch if code == 0 and branch and branch != "HEAD" else None


def is_linked_worktree(path: pathlib.Path) -> bool:
    """A linked worktree carries a ``.git`` *file* (gitfile), the primary a directory."""
    return (path / ".git").is_file()


def primary_checkout(context: GuardContext, cwd: pathlib.Path) -> pathlib.Path | None:
    code, common = git(context, cwd, "rev-parse", "--git-common-dir")
    if code != 0 or not common:
        return None
    common_dir = pathlib.Path(common)
    if not common_dir.is_absolute():
        common_dir = (cwd / common_dir).resolve()
    return common_dir.parent


def read_key_values(path: pathlib.Path) -> dict[str, str]:
    """``KEY=value`` receipts (``EXIT=``/``BASE=``/``HEAD=``/``LOG=``; last occurrence wins)."""
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return values
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip():
            values[key.strip()] = value.strip()
    return values


def tool_input(payload: Mapping[str, object]) -> Mapping[str, object]:
    value = payload.get("tool_input")
    return value if isinstance(value, Mapping) else {}


def command_of(payload: Mapping[str, object]) -> str:
    command = tool_input(payload).get("command")
    return command if isinstance(command, str) else ""


def file_path_of(payload: Mapping[str, object]) -> str | None:
    path = tool_input(payload).get("file_path") or tool_input(payload).get("notebook_path")
    return path if isinstance(path, str) and path else None


def payload_cwd(payload: Mapping[str, object]) -> str | None:
    cwd = payload.get("cwd")
    return cwd if isinstance(cwd, str) and cwd else None


def session_of(payload: Mapping[str, object]) -> str:
    session = payload.get("session_id")
    return session if isinstance(session, str) and session else "?"


def is_subagent(payload: Mapping[str, object], environ: Mapping[str, str]) -> bool:
    """A harness-subagent turn: agent markers in the payload, or a child-session environment."""
    if any(key in payload for key in ("agent_id", "agent_type", "parent_session_id")):
        return True
    return environ.get("CLAUDE_CODE_CHILD_SESSION") == "1" or bool(environ.get("LANE_RESULT_PATH"))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: pathlib.Path, data: Mapping[str, object]) -> None:
    """Atomic: temp file + rename, so a reader never sees a half-written state file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def deny(rule_id: str, message: str, *, escape: str | None = None) -> Verdict:
    """A refusal that always names its switch (harness/guards.md §5): the message ends with
    ``Switch: FACTORY_GUARD_ALLOW=<id> (logged).`` unless the rule names another escape."""
    switch = escape if escape is not None else f"FACTORY_GUARD_ALLOW={rule_id}"
    text = message if message.endswith(".") else message + "."
    return Verdict("deny", rule_id, f"{text} Switch: {switch} (logged).")


def context_note(rule_id: str, message: str) -> Verdict:
    return Verdict("context", rule_id, message)


def append_event(
    state_dir: pathlib.Path, session: str, event: str, kind: str, rule: str, text: str
) -> None:
    """One tab-separated line per denial / switch use in ``<state-dir>/factory-events.log``."""
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        with (state_dir / EVENTS_FILE).open("a", encoding="utf-8") as handle:
            flat = " ".join(text.split())[:200]
            handle.write(f"{utc_now()}\t{session}\t{event}\t{kind}\t{rule}\t{flat}\n")
    except OSError:
        pass


def read_events(state_dir: pathlib.Path, session: str | None = None) -> list[tuple[str, ...]]:
    try:
        lines = (state_dir / EVENTS_FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = [tuple(line.split("\t", 5)) for line in lines if line.strip()]
    rows = [row for row in rows if len(row) == 6]
    return [row for row in rows if session is None or row[1] == session]


_GIT_OPTIONS_WITH_OPERAND = frozenset({"-c", "--git-dir", "--work-tree"})


def _git_global_options(rest: list[str]) -> pathlib.Path | None:
    """Consume git's global options from ``rest`` in place; the ``-C`` directory if any."""
    directory: pathlib.Path | None = None
    while rest and rest[0].startswith("-"):
        option = rest.pop(0)
        if option == "-C" and rest:
            directory = pathlib.Path(rest.pop(0))
        elif option.startswith("-C") and len(option) > 2:
            directory = pathlib.Path(option[2:])
        elif option in _GIT_OPTIONS_WITH_OPERAND and rest:
            rest.pop(0)
    return directory


def git_statement(tokens: list[str]) -> tuple[pathlib.Path | None, str | None, list[str]]:
    """``(-C dir, subcommand, rest)`` for a ``git`` statement, else ``(None, None, [])``."""
    stripped = strip_prefixes(tokens)
    if not stripped or basename(stripped[0]) != "git":
        return None, None, []
    rest = stripped[1:]
    directory = _git_global_options(rest)
    if not rest:
        return directory, None, []
    return directory, rest[0], rest[1:]


def git_tree(directory: pathlib.Path | None, cwd: pathlib.Path) -> pathlib.Path:
    """The tree a git statement acts on: its ``-C`` operand resolved against ``cwd``."""
    if directory is None:
        return cwd
    return directory if directory.is_absolute() else cwd / directory


def disk_free_gb(path: pathlib.Path) -> float | None:
    try:
        return shutil.disk_usage(path).free / 1e9
    except OSError:
        return None


# --- process identity: executable name + exact argv token, never a text match ----------


@dataclass(frozen=True)
class LiveAgent:
    """A running lane CLI found by process identity (comm + exact token + directory flag)."""

    pid: int
    comm: str
    directory: pathlib.Path | None


def process_table(context: GuardContext) -> dict[int, tuple[int, str]]:
    """``pid -> (ppid, args)`` from one wide ``ps``; empty when ``ps`` is unavailable. The
    ``comm`` column is NOT taken from this table — multi-column ``comm`` is truncated on
    macOS — identity comes from :func:`pid_comm`, one pid at a time."""
    try:
        result = context.run(
            ["ps", "-axww", "-o", "pid=,ppid=,args="],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if result.returncode != 0:
        return {}
    rows: dict[int, tuple[int, str]] = {}
    for line in (result.stdout or "").splitlines():
        parts = line.split(None, 2)
        if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        rows[int(parts[0])] = (int(parts[1]), parts[2] if len(parts) > 2 else "")
    return rows


def pid_comm(context: GuardContext, pid: int) -> str:
    """The untruncated executable name the kernel reports for ONE pid (``ps -o comm= -p``),
    the launcher's method; empty when the pid is gone."""
    try:
        result = context.run(
            ["ps", "-o", "comm=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return (result.stdout or "").strip() if result.returncode == 0 else ""


def flag_operand(tokens: Sequence[str], flag: str) -> str | None:
    """The operand of ``<flag> <value>`` or ``<flag>=<value>`` in an argv, else ``None``."""
    for index, token in enumerate(tokens):
        name, sep, value = token.partition("=")
        if name == flag:
            if sep:
                return value
            if index + 1 < len(tokens):
                return tokens[index + 1]
    return None


def live_agents(context: GuardContext) -> list[LiveAgent]:
    """Every running lane CLI: comm basename equals ``FACTORY_GUARD_CLI`` and argv[1:] carries
    ``FACTORY_GUARD_CLI_TOKEN`` as one exact token. Unbound variables → no lanes, by design.
    The argv comes whitespace-joined from ``ps``: a directory operand containing a space is
    read up to its first space (harness/guards.md §13)."""
    cli = context.environ.get(CLI_VAR, "")
    token = context.environ.get(CLI_TOKEN_VAR, "")
    dir_flag = context.environ.get(CLI_DIR_FLAG_VAR, "")
    if not cli or not token:
        return []
    agents: list[LiveAgent] = []
    for pid, (_, args) in sorted(process_table(context).items()):
        tokens = args.split()
        if token not in tokens[1:]:  # cheap prefilter on the exact token …
            continue
        comm = basename(pid_comm(context, pid))  # … then the authoritative identity
        if comm != cli:
            continue
        directory = flag_operand(tokens[1:], dir_flag) if dir_flag else None
        agents.append(LiveAgent(pid, comm, _resolved(directory) if directory else None))
    return agents


def _resolved(path: str) -> pathlib.Path:
    try:
        return pathlib.Path(path).expanduser().resolve()
    except OSError:
        return pathlib.Path(path)


def agents_writing_in(context: GuardContext, directory: pathlib.Path) -> list[LiveAgent]:
    target = _resolved(str(directory))
    return [agent for agent in live_agents(context) if agent.directory == target]
