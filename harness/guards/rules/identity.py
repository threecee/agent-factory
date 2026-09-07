"""Identity guard (harness/guards.md §7, mechanism M-3b) plus the lint helper (M-3a).

(b) :func:`check` refuses the text-match process-selection forms (each a forbidden form)
in a shell tool call — ``pgrep -f``/``--full``, ``pkill -f`` and ``ps aux|-ef|ax|-ax … |
grep|egrep|rg`` — and names the identity form instead (executable basename + exact argv
token, harness/run-lifecycle.md §6). It never kills anything.
(a) :func:`lint_findings` returns ``path:line: text`` for the same forms in a tree, outside
lines that carry the marker ``forbidden form`` (on the line, or on the previous non-blank
line). The installer's own lint test and ``harness/tests/test_guards.sh`` use it.

Every quoted forbidden form in this file carries the marker so the lint stays green on the
package itself.
"""

from __future__ import annotations

import pathlib
import re
from collections.abc import Iterable, Mapping

from guards._common import (
    ALLOW,
    CLI_TOKEN_VAR,
    CLI_VAR,
    FalsificationCase,
    GuardContext,
    Verdict,
    basename,
    command_of,
    deny,
    parse_statements,
    strip_prefixes,
)

ID = "identity"
EVENTS = frozenset({"PreToolUse"})
MATCHER = "Bash"

EXEMPTION_MARKER = "forbidden form"
DEFAULT_LINT_ROOTS: tuple[str, ...] = ("harness",)
_LINT_SUFFIXES = frozenset({".py", ".sh", ".md", ".example", ""})
_FORBIDDEN_TEXT = (
    re.compile(r"pgrep\s+(?:-[A-Za-z]*f[A-Za-z]*\b|--full\b)"),
    re.compile(r"\bps\s+(?:aux|-ef|ax|-ax)\b[^|\n]*\|\s*grep\b"),
    re.compile(r"pkill\s+(?:-[A-Za-z]*f[A-Za-z]*\b|--full\b)"),
)
_PS_WIDE_FLAGS = frozenset({"aux", "-ef", "ax", "-ax", "-aux", "-e"})


LAUNCHER = "harness/launch_lane.sh"


def identity_form(environ: Mapping[str, str]) -> str:
    """The exact alternative the refusal names: the launcher's ``running`` subcommand, which
    implements harness/run-lifecycle.md §6 (the untruncated ``comm`` of ONE pid at a time plus
    the exact argv token — never a multi-column ``comm``, never a substring match), with the
    CLI and token filled in from ``FACTORY_GUARD_CLI``/``FACTORY_GUARD_CLI_TOKEN``
    (placeholders when unset)."""
    cli = environ.get(CLI_VAR) or "<cli>"
    token = environ.get(CLI_TOKEN_VAR) or "<token>"
    return f"{LAUNCHER} running {cli} {token}"


def _has_full_flag(tokens: list[str]) -> bool:
    return any(
        token == "--full" or (token.startswith("-") and not token.startswith("--") and "f" in token)
        for token in tokens[1:]
    )


def _pipes_into_grep(stages: tuple[tuple[str, ...], ...]) -> bool:
    for stage in stages:
        stripped = strip_prefixes(stage)
        if stripped and basename(stripped[0]) in {"grep", "egrep", "rg"}:
            return True
    return False


def _forbidden_form(statement_pipeline: tuple[tuple[str, ...], ...]) -> str | None:
    first = strip_prefixes(statement_pipeline[0]) if statement_pipeline else []
    if not first:
        return None
    head = basename(first[0])
    if head in {"pgrep", "pkill"} and _has_full_flag(first):
        return f"{head} -f"
    wide = head == "ps" and any(token in _PS_WIDE_FLAGS for token in first[1:])
    if wide and _pipes_into_grep(statement_pipeline[1:]):
        return "ps aux | grep"  # forbidden form, quoted for the refusal
    return None


def verdict_for_command(command: str, environ: Mapping[str, str]) -> Verdict:
    form_of_identity = identity_form(environ)
    for statement in parse_statements(command):
        form = _forbidden_form(statement.pipeline)
        if form is None:
            continue
        if form.startswith("pkill"):
            # forbidden form quoted in the refusal below
            return deny(
                ID,
                f"GUARD identity: «{form}» kills by text match and hits other lanes' processes "
                "(harness/run-lifecycle.md §6). Fix: tear down by port: lsof -ti :<port>, or "
                f"select by identity: {form_of_identity}",
            )
        # forbidden form quoted in the refusal below
        return deny(
            ID,
            f"GUARD identity: «{form}» matches the inspecting shell "
            f"(harness/run-lifecycle.md §6). Fix: {form_of_identity}",
        )
    return ALLOW


def check(payload: Mapping[str, object], context: GuardContext) -> Verdict:
    return verdict_for_command(command_of(payload), context.environ)


def _lint_files(root: pathlib.Path, roots: Iterable[str]) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for entry in roots:
        path = root / entry
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in sorted(path.rglob("*"))
                if candidate.is_file()
                and candidate.suffix in _LINT_SUFFIXES
                and "__pycache__" not in candidate.parts
            )
    return files


def _exempt(lines: list[str], index: int, marker: str) -> bool:
    if marker in lines[index]:
        return True
    previous = index - 1
    while previous >= 0 and not lines[previous].strip():
        previous -= 1
    return previous >= 0 and marker in lines[previous]


def lint_findings(
    root: pathlib.Path,
    roots: Iterable[str] = DEFAULT_LINT_ROOTS,
    marker: str = EXEMPTION_MARKER,
) -> list[str]:
    """``path:line: <text>`` for every forbidden process-identity form under ``roots``."""
    findings: list[str] = []
    for path in _lint_files(pathlib.Path(root), roots):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for index, line in enumerate(lines):
            if any(pattern.search(line) for pattern in _FORBIDDEN_TEXT) and not _exempt(
                lines, index, marker
            ):
                relative = path.relative_to(root).as_posix()
                findings.append(f"{relative}:{index + 1}: {line.strip()}")
    return findings


_DENIED_FORMS = (
    # forbidden form — planted violation in the falsification table
    ("pkill-f-server", "pkill -f serve.py", "GUARD identity: «pkill -f»"),
    # forbidden form — planted violation in the falsification table
    ("pgrep-fl-cli", 'pgrep -fl "<cli> <token>"', "GUARD identity: «pgrep -f»"),
    # forbidden form — planted violation in the falsification table
    ("pgrep-full", "pgrep --full '<cli> <token>' | wc -l", "GUARD identity: «pgrep -f»"),
    # forbidden form — planted violation in the falsification table
    ("ps-aux-grep", "ps aux | grep '[s]erve.py'", "GUARD identity: «ps aux | grep»"),
    # forbidden form — planted violation in the falsification table
    ("cd-then-pgrep", "cd /tmp && pgrep -af serve", "GUARD identity: «pgrep -f»"),
    # forbidden form — planted violation inside a shell -c string (one level of wrapping)
    ("sh-c-wrapped", "sh -c 'pgrep -f serve'", "GUARD identity: «pgrep -f»"),
)
_ALLOWED_FORMS = (
    ("launcher-running", identity_form({})),
    # a multi-column comm read plus an awk: green (no text match over the command line), but
    # not the recommended form — multi-column comm is truncated on macOS and /<token>/ is a
    # substring match (harness/run-lifecycle.md §6, train-plan.md §3.3)
    ("ps-comm-awk", "ps -axo pid=,comm=,args= | awk '$2==\"<cli>\" && /<token>/'"),
    ("lsof-port", "lsof -ti :<port>"),
    ("pgrep-exact", "pgrep -x <cli>"),
    ("grep-for-the-word", "grep -rn pgrep docs"),
    ("kill-by-pid", "kill 4711"),
)


def falsification_cases(workdir: pathlib.Path) -> list[FalsificationCase]:
    def payload(command: str) -> dict[str, object]:
        return {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "cwd": str(workdir),
        }

    cases = [
        FalsificationCase(name, "PreToolUse", payload(command), "deny", needle)
        for name, command, needle in _DENIED_FORMS
    ]
    cases += [
        FalsificationCase(name, "PreToolUse", payload(command), "allow")
        for name, command in _ALLOWED_FORMS
    ]
    return cases
