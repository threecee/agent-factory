"""Verdict guard (harness/guards.md §7, mechanism M-2): a gate's verdict is never read
through a pipe, and a verdict and a push never share one call.

Fires only on a known gate invocation — the patterns in ``FACTORY_GUARD_GATES`` (the one
parameter; guards.md §8) — followed in the same command by ``| tail``/``| head`` (always),
by any other pipe stage without ``set -o pipefail``, or by a ``git push`` statement; and on
``cat <x>.exit`` followed by ``git push`` (verdict and push in one call). It never rewrites
the command silently: the exact form stands in the refusal so the operator learns it.
"""

from __future__ import annotations

import fnmatch
import pathlib
import re
import shlex
from collections.abc import Mapping

from guards._common import (
    ALLOW,
    REDIRECTION,
    FalsificationCase,
    GuardContext,
    Statement,
    Verdict,
    basename,
    command_of,
    deny,
    is_python,
    parse_statements,
    strip_prefixes,
)

ID = "verdict"
EVENTS = frozenset({"PreToolUse"})
MATCHER = "Bash"

GATES_VAR = "FACTORY_GUARD_GATES"
DEFAULT_GATES = "verify,verify-*,check-*,pytest,scripts.check_*,scripts.assemble_*"
_HIDING_STAGES = frozenset({"tail", "head"})
_REDIRECT_TOKEN_RE = re.compile(r"^\d*>>?$|^<$")


def gate_patterns(environ: Mapping[str, str]) -> list[str]:
    """``FACTORY_GUARD_GATES`` as a list: ``make`` target patterns and runner names (no dot)
    and ``scripts.<module>`` patterns (with a dot) for ``python -m`` / ``python <path>``."""
    raw = environ.get(GATES_VAR) or DEFAULT_GATES
    return [part.strip() for part in raw.split(",") if part.strip()]


def _module_name(target: str) -> str:
    """``scripts/check_x.py`` → ``scripts.check_x``; ``scripts.check_x`` stays."""
    if target.endswith(".py"):
        target = target[:-3]
    return target.replace("/", ".").lstrip(".")


def gate_name(segment: tuple[str, ...], patterns: list[str]) -> str | None:
    """The gate a pipeline's first segment invokes, or ``None`` for a non-gate command."""
    tokens = strip_prefixes(segment)
    if not tokens:
        return None
    head = basename(tokens[0])
    plain = [pattern for pattern in patterns if "." not in pattern]
    modules = [pattern for pattern in patterns if "." in pattern]
    if head == "make":
        return next(
            (token for token in tokens[1:] if any(fnmatch.fnmatch(token, p) for p in plain)),
            None,
        )
    if any(fnmatch.fnmatch(head, p) for p in plain):
        return head
    if is_python(head):
        return _python_gate(tokens, plain, modules)
    if head.endswith(".py"):
        module = _module_name(tokens[0])
        return module.rsplit(".", 1)[-1] if _matches_module(module, modules) else None
    return None


def _matches_module(module: str, modules: list[str]) -> bool:
    return any(fnmatch.fnmatch(module, pattern) for pattern in modules)


def _python_gate(tokens: list[str], plain: list[str], modules: list[str]) -> str | None:
    """``python -m <module>`` (a runner name or a module pattern) or ``python <script>``."""
    if len(tokens) >= 3 and tokens[1] == "-m":
        target = tokens[2]
        if any(fnmatch.fnmatch(target, p) for p in plain):
            return target
        module = _module_name(target)
    elif len(tokens) >= 2:
        module = _module_name(tokens[1])
    else:
        return None
    return module.rsplit(".", 1)[-1] if _matches_module(module, modules) else None


def _is_git_push(tokens: list[str]) -> bool:
    return bool(tokens) and basename(tokens[0]) == "git" and "push" in tokens[1:]


def _reads_receipt(tokens: list[str]) -> bool:
    return bool(tokens) and any(token.endswith(".exit") for token in tokens[1:])


def _without_redirections(segment: tuple[str, ...]) -> list[str]:
    kept: list[str] = []
    skip_next = False
    for token in segment:
        if skip_next:
            skip_next = False
            continue
        if token == REDIRECTION:
            continue
        if _REDIRECT_TOKEN_RE.match(token):
            skip_next = True
            continue
        kept.append(token)
    return kept


def _rewrite(statement: Statement, gate: str) -> str:
    invocation = shlex.join(_without_redirections(statement.first))
    return f"{invocation} > <lane>-{gate}.log 2>&1; echo EXIT=$?"


def _refusal(through: str, exact: str) -> Verdict:
    return deny(
        ID,
        f"VERDICT GUARD: a verdict cannot be read through «{through}». Run the gate with a "
        "redirect to <lane>-<gate>.log and read $? in ONE call; push in the NEXT "
        f"(harness/train-plan.md §4.1). Fix, exactly: {exact}",
    )


def _piped_refusal(statement: Statement, gate: str, pipefail: bool) -> Verdict | None:
    stages = [
        basename(stripped[0])
        for segment in statement.pipeline[1:]
        if (stripped := strip_prefixes(segment))
    ]
    hiding = next((stage for stage in stages if stage in _HIDING_STAGES), None)
    if hiding is not None:
        return _refusal(f"| {hiding}", _rewrite(statement, gate))
    if stages and not pipefail:
        return _refusal(f"| {stages[0]} without set -o pipefail", _rewrite(statement, gate))
    return None


def verdict_for_command(command: str, patterns: list[str] | None = None) -> Verdict:
    patterns = patterns if patterns is not None else gate_patterns({})
    statements = parse_statements(command)
    pipefail = "pipefail" in command
    gate_statement: tuple[Statement, str] | None = None
    receipt_statement: Statement | None = None
    for statement in statements:
        tokens = strip_prefixes(statement.first)
        gate = gate_name(statement.first, patterns)
        if gate is not None:
            if len(statement.pipeline) > 1:
                refusal = _piped_refusal(statement, gate, pipefail)
                if refusal is not None:
                    return refusal
            gate_statement = (statement, gate)
            continue
        if _is_git_push(tokens):
            if gate_statement is not None:
                first, gate = gate_statement
                return _refusal(
                    "; git push",
                    f"{_rewrite(first, gate)} — then, in the NEXT call when EXIT=0: "
                    f"{shlex.join(tokens)}",
                )
            if receipt_statement is not None:
                return _refusal(
                    "; git push",
                    f"{shlex.join(strip_prefixes(receipt_statement.first))} — then, in the NEXT "
                    f"call when the receipt says EXIT=0: {shlex.join(tokens)}",
                )
        if _reads_receipt(tokens):
            receipt_statement = statement
    return ALLOW


def check(payload: Mapping[str, object], context: GuardContext) -> Verdict:
    return verdict_for_command(command_of(payload), gate_patterns(context.environ))


_DENIED_FORMS = (
    ("tail-after-make", "make check-backlog 2>&1 | tail -6; echo EXIT=$?", "| tail"),
    ("tail-after-pytest", "pytest tests/test_backlog.py -q | tail -1", "| tail"),
    ("head-after-check", "python3 -m scripts.check_backlog | head -20", "| head"),
    ("grep-without-pipefail", "make verify 2>&1 | grep -E 'passed|failed'", "| grep"),
    (
        "tail-after-assemble",
        "python3 -m scripts.assemble_train t-42 --run-id t-42-1 | tail",
        "| tail",
    ),
    ("gate-then-push", "make check-backlog; git push origin HEAD:main", "; git push"),
    ("receipt-then-push", "cat t-42-1.exit; git push origin HEAD:main", "; git push"),
    ("tee-without-pipefail", "pytest tests -q 2>&1 | tee lane-full.log", "| tee"),
    ("verify-target-tail", "make verify-fast | tail -2", "| tail"),
    (
        "two-gates-then-push",
        "make check-backlog && make check-numbers && git push origin HEAD:main",
        "; git push",
    ),
)
_ALLOWED_FORMS = (
    ("grep-on-log", "grep -n FAILED verify-t-42.log | tail -5"),
    ("tail-after-ls", "ls -t artifacts | tail -3"),
    (
        "tee-with-pipefail",
        "set -o pipefail; make check-backlog 2>&1 | tee t-42-backlog.log; echo EXIT=${PIPESTATUS[0]}",
    ),
    ("redirect-and-exit", "make check-backlog > lane-backlog.log 2>&1; echo EXIT=$?"),
    ("read-receipt-alone", "cat t-42-1.exit"),
    ("push-branch-alone", "git push origin lane/x"),
    ("pytest-alone", "pytest tests/test_backlog.py -q -p no:cacheprovider"),
    ("check-alone", "python3 -m scripts.check_backlog"),
    ("two-gates-chained", "make check-backlog && make check-numbers"),
    ("git-log-head", "git log --oneline | head -3"),
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
        FalsificationCase(
            name,
            "PreToolUse",
            payload(command),
            "deny",
            f"VERDICT GUARD: a verdict cannot be read through «{needle}",
        )
        for name, command, needle in _DENIED_FORMS
    ]
    cases += [
        FalsificationCase(name, "PreToolUse", payload(command), "allow")
        for name, command in _ALLOWED_FORMS
    ]
    return cases
