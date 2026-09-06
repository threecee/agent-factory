"""Guard ``no-verify`` (harness/guards.md §7, row ``no-verify`` of mechanism M-16):
``git commit|push|merge|rebase|am --no-verify`` and ``git commit -n`` are refused — always,
with no precondition.

Why this row exists: git's own ``--no-verify`` cannot be removed on the git side, so a
git hook (the landing check on push, the identity and trailer checks on commit —
verification/protections.md, introduced by PR13) can always be skipped by whoever types
the flag. This harness-side row is what gives those hooks their meaning inside a hooked
session: a red hook is fixed, never bypassed (planning/lane-brief-template.md §2).
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping

from guards._common import (
    ALLOW,
    FalsificationCase,
    GuardContext,
    Verdict,
    command_of,
    deny,
    git_statement,
    parse_statements,
)

ID = "no-verify"
EVENTS = frozenset({"PreToolUse"})
MATCHER = "Bash"

_HOOKED = frozenset({"commit", "push", "merge", "rebase", "am"})


def skips_hooks(command: str) -> str | None:
    """The git subcommand that carries ``--no-verify`` (or ``-n`` on commit), else ``None``.
    ``git -C <dir>`` and other global options are honoured."""
    for statement in parse_statements(command):
        _, sub, rest = git_statement(list(statement.first))
        if sub not in _HOOKED:
            continue
        if "--no-verify" in rest or (sub == "commit" and "-n" in rest):
            return sub
    return None


def check(payload: Mapping[str, object], context: GuardContext) -> Verdict:
    sub = skips_hooks(command_of(payload))
    if sub is None:
        return ALLOW
    return deny(
        ID,
        f"GUARD no-verify: «git {sub} --no-verify» skips the git hooks "
        "(planning/lane-brief-template.md §2; verification/protections.md). "
        f"Fix: run «git {sub}» without the flag — a red hook is fixed, never bypassed",
    )


def falsification_cases(workdir: pathlib.Path) -> list[FalsificationCase]:
    def payload(command: str) -> dict[str, object]:
        return {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "cwd": str(workdir),
        }

    return [
        FalsificationCase(
            "commit-no-verify",
            "PreToolUse",
            payload("git commit --no-verify -m 'x'"),
            "deny",
            "GUARD no-verify: «git commit --no-verify»",
        ),
        FalsificationCase(
            "commit-short-n",
            "PreToolUse",
            payload("git -C /tmp/wt commit -n -m 'x'"),
            "deny",
            "GUARD no-verify: «git commit --no-verify»",
        ),
        FalsificationCase(
            "push-no-verify",
            "PreToolUse",
            payload("git push --no-verify origin lane/x"),
            "deny",
            "GUARD no-verify: «git push --no-verify»",
        ),
        FalsificationCase("commit-plain", "PreToolUse", payload("git commit -m 'x'"), "allow"),
        FalsificationCase(
            "grep-for-the-flag", "PreToolUse", payload("grep -rn -- --no-verify docs"), "allow"
        ),
    ]
