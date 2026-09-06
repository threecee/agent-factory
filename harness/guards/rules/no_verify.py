"""Guard ``no-verify`` (harness/guards.md §7, row ``no-verify`` of mechanism M-16):
``git commit|push|merge|rebase|am --no-verify``, ``git commit -n`` and a hooked subcommand
run under ``git -c core.hooksPath=<elsewhere>`` are refused — always, with no precondition.

Why this row exists: git's own ``--no-verify`` cannot be removed on the git side, so a
git hook (the identity and trailer checks on commit; the landing check when the override
landing mode pushes the default branch directly — verification/protections.md) can always
be skipped by whoever types the flag or points ``core.hooksPath`` elsewhere. This
harness-side row is what gives those hooks their meaning inside a hooked session: a red
hook is fixed, never bypassed (planning/lane-brief-template.md §2).
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
    git_hooks_path_override,
    git_statement,
    parse_statements,
)

ID = "no-verify"
EVENTS = frozenset({"PreToolUse"})
MATCHER = "Bash"

_HOOKED = frozenset({"commit", "push", "merge", "rebase", "am"})


def skips_hooks(command: str) -> tuple[str, str] | None:
    """``(subcommand, how)`` for the first hooked git subcommand that skips the hooks —
    ``how`` is ``--no-verify`` (also ``-n`` on commit) or the ``core.hooksPath=…`` override
    among the global options — else ``None``. ``git -C <dir>`` and the other global options
    are honoured."""
    for statement in parse_statements(command):
        tokens = list(statement.first)
        _, sub, rest = git_statement(tokens)
        if sub not in _HOOKED:
            continue
        if "--no-verify" in rest or (sub == "commit" and "-n" in rest):
            return sub, "--no-verify"
        override = git_hooks_path_override(tokens)
        if override is not None:
            return sub, f"-c {override}"
    return None


def check(payload: Mapping[str, object], context: GuardContext) -> Verdict:
    found = skips_hooks(command_of(payload))
    if found is None:
        return ALLOW
    sub, how = found
    quoted = f"git {sub} --no-verify" if how == "--no-verify" else f"git {how} {sub}"
    what = "the flag" if how == "--no-verify" else "the override"
    return deny(
        ID,
        f"GUARD no-verify: «{quoted}» skips the git hooks "
        "(planning/lane-brief-template.md §2; verification/protections.md). "
        f"Fix: run «git {sub}» without {what} — a red hook is fixed, never bypassed",
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
        FalsificationCase(
            "commit-hookspath",
            "PreToolUse",
            payload("git -c core.hooksPath=/dev/null commit -m 'x'"),
            "deny",
            "GUARD no-verify: «git -c core.hooksPath=/dev/null commit»",
        ),
        FalsificationCase(
            "bash-c-wrapped",
            "PreToolUse",
            payload('bash -c "git commit --no-verify -m x"'),
            "deny",
            "GUARD no-verify: «git commit --no-verify»",
        ),
        FalsificationCase("commit-plain", "PreToolUse", payload("git commit -m 'x'"), "allow"),
        FalsificationCase(
            "commit-other-config",
            "PreToolUse",
            payload("git -c user.email=lane@example.invalid commit -m 'x'"),
            "allow",
        ),
        FalsificationCase(
            "grep-for-the-flag", "PreToolUse", payload("grep -rn -- --no-verify docs"), "allow"
        ),
    ]
