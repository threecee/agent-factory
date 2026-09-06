"""Pre-push git hook (verification/protections.md §1.1, mechanism M-10): the landing guard
outside the harness hook, in the direct-push override mode.

The tracked shim ``verification/protections/githooks/pre-push`` feeds git's ref lines to the
dispatcher as event ``GitPrePush``. For every update whose remote ref is the default branch
(``refs/heads/<FACTORY_DEFAULT_BRANCH>``, default ``main``) this rule runs *the same* landing
check as the ``landing`` rule (``landing.check`` over a ``git push <remote> HEAD:<default>``
payload) — receipt for exactly HEAD, boarders, ledger, optional legs, the ledger lint — so
the guard also holds for a coding-CLI session, a plain terminal and a foreign harness. A
local SHA other than HEAD is refused (a receipt binds exactly HEAD); a deletion of the default
branch is refused; a push of any other destination (``lane/*``, ``train/*``) is silent — the
integration-branch push is never gated. The rule's id is the landing rule's (``landing``): it
is the same guard, and the same switch.

Git's own ``--no-verify`` cannot be removed here; the ``no-verify`` rule refuses the flag inside
a hooked session, and the branch policy makes the flag harmless. This hook never runs the
verify portfolio.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping
from dataclasses import replace

from guards._common import ALLOW, FalsificationCase, GuardContext, Verdict, deny, git, payload_cwd
from guards.rules import landing

ID = landing.ID
EVENTS = frozenset({"GitPrePush"})
MATCHER = None
ZERO_SHA = "0" * 40


def refs_of(payload: Mapping[str, object]) -> list[dict[str, str]]:
    info = payload.get("git")
    refs = info.get("refs") if isinstance(info, Mapping) else None
    return [dict(ref) for ref in refs if isinstance(ref, Mapping)] if isinstance(refs, list) else []


def remote_of(payload: Mapping[str, object]) -> str:
    info = payload.get("git")
    remote = info.get("remote") if isinstance(info, Mapping) else None
    return remote if isinstance(remote, str) and remote else "origin"


def default_updates(refs: list[dict[str, str]], branch: str) -> list[dict[str, str]]:
    return [ref for ref in refs if ref.get("remote_ref") == f"refs/heads/{branch}"]


def check(payload: Mapping[str, object], context: GuardContext) -> Verdict:
    branch = landing.default_branch(context.environ)
    updates = default_updates(refs_of(payload), branch)
    if not updates:
        return ALLOW
    cwd = pathlib.Path(payload_cwd(payload) or ".").resolve()
    code, head = git(context, cwd, "rev-parse", "HEAD")
    if code != 0 or not head:
        return deny(ID, f"GUARD landing: {cwd} is not a git tree. Fix: push from the train worktree")
    for ref in updates:
        local_sha = ref.get("local_sha", "")
        if local_sha == ZERO_SHA:
            return deny(
                ID,
                f"GUARD landing: deletion of {branch} is refused (verification/landing-modes.md §3). "
                f"Fix: none — the default branch is never deleted",
                escape="none — a hard form",
            )
        if local_sha != head:
            return deny(
                ID,
                f"GUARD landing: {local_sha[:8]} ({ref.get('local_ref', '?')}) is another commit than "
                f"HEAD {head[:8]}; a receipt binds exactly HEAD (harness/train-plan.md §4.1). "
                f"Fix: git push {remote_of(payload)} HEAD:{branch} from the train worktree",
            )
    bash_payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": f"git push {remote_of(payload)} HEAD:{branch}"},
        "cwd": str(cwd),
        "session_id": payload.get("session_id", "?"),
    }
    return landing.check(bash_payload, replace(context, event="PreToolUse"))


def falsification_cases(workdir: pathlib.Path) -> list[FalsificationCase]:
    from guards.rules import _landing_fixtures as fx

    def case(name: str, expect: str, needle: str, tree: fx.Tree, refs: list[tuple[str, str, str, str]], **env: str) -> FalsificationCase:
        return FalsificationCase(
            name,
            "GitPrePush",
            fx.pre_push_payload(tree.train, refs),
            expect,  # type: ignore[arg-type]
            needle,
            tree.env(**env),
        )

    red = fx.case_tree(workdir, "hook-red", exit_code="2")
    to_main = [("refs/heads/train/wtest", red.head, "refs/heads/main", red.main_sha)]
    green = fx.case_tree(workdir, "hook-green")
    return [
        case("hook-main-without-green-receipt", "deny", "GUARD landing: the receipt is red", red, to_main),
        case("hook-main-green-train", "allow", "", green, [("refs/heads/train/wtest", green.head, "refs/heads/main", green.main_sha)]),
        case("hook-other-commit-than-head", "deny", "is another commit than HEAD", green, [("refs/heads/train/wtest", fx.OTHER_SHA, "refs/heads/main", green.main_sha)]),
        case("hook-delete-main", "deny", "deletion of main is refused", green, [("", "0" * 40, "refs/heads/main", green.main_sha)]),
        case("hook-lane-branch-is-silent", "allow", "", red, [("refs/heads/lane/alpha", red.boarder_sha, "refs/heads/lane/alpha", red.boarder_sha)]),
        case("hook-train-branch-is-silent", "allow", "", red, [("refs/heads/train/wtest", red.head, "refs/heads/train/wtest", "0" * 40)]),
        case("hook-landing-switch", "allow", "", red, to_main, FACTORY_GUARD_ALLOW=ID),
    ]
