"""Close-out rule (verification/protections.md §6, mechanism M-13): the lander duties of
lander-duties §8 must be closed before the turn ends — identical in both landing modes.

Runs only while ``<state-dir>/landing-in-progress.json`` exists (written by the landing rule
after a registered landing) and, on ``SessionStart``, only for source ``compact`` or
``resume``. It calls the gate ``check_landing_closeout`` (located as
``harness/guards/rules/_gates.py`` says) with the state and the primary checkout. Every duty
closed on ``Stop`` → the state file and its marker are deleted, one ``closeout`` line goes to
the events log, and the rule is silent. A duty open on ``Stop`` → the refusal counts in the
state file: up to three times it is a denial (exit 2, the turn continues) listing every open
duty with its exact command and naming the escape; after three the stop is allowed with a
loud note and the duties stay listed in the state file. On ``SessionStart`` the same list is
context, never a block. The escape is the word ``closeout`` in the state directory's allow
file (a Stop hook has no command to read a prefix from); a state file deleted by hand is the
other way out and is logged as ``state-removed`` the next time the rule runs. The rule performs
no duty itself: no reap, no flip, no fast-forward, no deletion.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
from collections.abc import Callable, Mapping

from guards._common import (
    ALLOW,
    ALLOW_FILE,
    FalsificationCase,
    GuardContext,
    Verdict,
    append_event,
    context_note,
    deny,
    payload_cwd,
    session_of,
    write_json,
)
from guards.rules import _gates
from guards.rules.landing import STATE_FILE

ID = "closeout"
EVENTS = frozenset({"Stop", "SessionStart"})
MATCHER = None
MAX_DENIALS = 3
LAST_FILE = "landing-in-progress.last"
GATE = "check_landing_closeout"
_SESSION_SOURCES = frozenset({"compact", "resume"})


def _floor(context: GuardContext) -> float | None:
    raw = context.environ.get("FACTORY_GUARD_DISK_FLOOR_GB")
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


def _primary(gate, context: GuardContext, payload: Mapping[str, object]) -> pathlib.Path:
    cwd = pathlib.Path(payload_cwd(payload) or os.getcwd())
    return gate.primary_of(context.run, cwd)


def duties_text(duties, allow_file: pathlib.Path) -> str:
    listed = "\n".join(f"  {duty.line()}" for duty in duties)
    return (
        f"GUARD closeout: LANDER DUTIES OPEN (verification/lander-duties.md §8):\n{listed}\n"
        f"  Finish them, or write closeout to {allow_file} with the reason in the ledger."
    )


def _read_state(context: GuardContext, payload: Mapping[str, object]) -> dict[str, object] | None:
    state_path = context.state_dir / STATE_FILE
    marker = context.state_dir / LAST_FILE
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = None
    if not isinstance(state, dict):
        try:
            last = marker.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        marker.unlink(missing_ok=True)
        append_event(
            context.state_dir,
            session_of(payload),
            context.event,
            "state-removed",
            ID,
            f"the state file for train {last} was removed without a close-out (deleted by hand)",
        )
        return None
    try:
        marker.write_text(f"{state.get('train')}\n", encoding="utf-8")
    except OSError:
        pass
    return state


def _closed(context: GuardContext, payload: Mapping[str, object], state: Mapping[str, object]) -> None:
    (context.state_dir / STATE_FILE).unlink(missing_ok=True)
    (context.state_dir / LAST_FILE).unlink(missing_ok=True)
    append_event(
        context.state_dir,
        session_of(payload),
        context.event,
        "closeout",
        ID,
        f"lander duties closed for train {state.get('train')}; state file deleted",
    )


def _stop_verdict(context: GuardContext, state: dict[str, object], text: str) -> Verdict:
    state_path = context.state_dir / STATE_FILE
    denials = int(state.get("denials") or 0) + 1
    state["denials"] = denials
    write_json(state_path, state)
    if denials > MAX_DENIALS:
        return context_note(ID, text + f" ({denials - 1} refusals used — the stop is allowed now; the duties stand in {state_path})")
    return deny(ID, text, escape=f"the word closeout in {context.state_dir / ALLOW_FILE}")


def check(payload: Mapping[str, object], context: GuardContext) -> Verdict:
    if context.event == "SessionStart" and payload.get("source") not in _SESSION_SOURCES:
        return ALLOW
    state = _read_state(context, payload)
    if state is None:
        return ALLOW
    gate = _gates.load_gate(context.environ, context.repo_root, GATE)
    if gate is None:
        return context_note(
            ID,
            f"GUARD closeout: the gate {GATE}.py was not found under {_gates.GATES_DIR_VAR}, <repo>/scripts or "
            f"<repo>/verification/gates — the lander duties of train {state.get('train')} are not checked; "
            f"close them by hand and delete {context.state_dir / STATE_FILE}.",
        )
    primary = _primary(gate, context, payload)
    duties, notes = gate.closeout(
        state,
        primary,
        run=context.run,
        floor_gb=_floor(context),
        port_range=context.environ.get("FACTORY_GUARD_PORT_RANGE") or None,
        offline=context.environ.get("FACTORY_GUARD_OFFLINE") == "1",
        environ=context.environ,
    )
    if not duties:
        if context.event == "Stop":
            _closed(context, payload, state)
        return ALLOW
    text = duties_text(duties, context.state_dir / ALLOW_FILE)
    if notes:
        text += " Note: " + "; ".join(notes) + "."
    if context.event != "Stop":
        return context_note(ID, text)
    return _stop_verdict(context, state, text)


def falsification_cases(workdir: pathlib.Path) -> list[FalsificationCase]:
    from guards.rules import _landing_fixtures as fx

    primary = workdir / "closeout-primary"
    origin = workdir / "closeout-origin.git"
    if not primary.exists():
        origin.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
        primary.mkdir()
        fx.git(primary, "init", "-q", "-b", "main")
        fx.git(primary, "config", "user.email", fx.EMAIL)
        fx.git(primary, "config", "user.name", "lander")
        fx.git(primary, "remote", "add", "origin", str(origin))
        (primary / "README.md").write_text("x\n", encoding="utf-8")
        fx.git(primary, "add", "README.md")
        fx.git(primary, "commit", "-q", "-m", "init")
        fx.git(primary, "push", "-q", "-u", "origin", "main")
    train = (workdir / "closeout-train").resolve()
    if not train.exists():
        fx.git(primary, "worktree", "add", "-q", "-b", "train/wclose", str(train), "HEAD")
        (train / "landed.txt").write_text("y\n", encoding="utf-8")
        fx.git(train, "add", "landed.txt")
        fx.git(train, "commit", "-q", "-m", "train(wclose): board alpha")
        fx.git(train, "push", "-q", "-u", "origin", "train/wclose")
        fx.git(primary, "merge", "-q", "--no-ff", "-m", "Merge pull request #7 from origin/train/wclose", "train/wclose")
        fx.git(primary, "push", "-q", "origin", "main")
    head = fx.git(train, "rev-parse", "HEAD")
    state_dir = workdir / "closeout-state"
    fake_bin = workdir / "closeout-bin"
    fake_bin.mkdir(exist_ok=True)
    gh = fake_bin / "gh"
    gh.write_text('#!/bin/sh\ncase "$1 $2" in "auth status") exit 0 ;; "pr view") printf \'%s\\n\' \'{"state":"OPEN"}\' ;; *) exit 1 ;; esac\n', encoding="utf-8")
    gh.chmod(0o755)

    def env(**extra: str) -> dict[str, str]:
        return {"FACTORY_GUARD_STATE_DIR": str(state_dir), "FACTORY_GUARD_DISK_FLOOR_GB": "0", **extra}

    def state(denials: int = 0, mode: str = "direct-push", pr: int | None = None) -> dict[str, object]:
        return {"train": "wclose", "head": head, "mode": mode, "pr": pr, "boarders": {}, "artifacts_dir": None, "default_branch": "main", "pushed_at": "2026-09-06T12:00:00+00:00", "denials": denials}

    def write_state(denials: int = 0, **kwargs) -> Callable[[], None]:
        write_json(state_dir / STATE_FILE, state(denials, **kwargs))
        return lambda: None

    def clear_state() -> Callable[[], None]:
        (state_dir / STATE_FILE).unlink(missing_ok=True)
        return lambda: None

    def marker_without_state() -> Callable[[], None]:
        (state_dir / STATE_FILE).unlink(missing_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / LAST_FILE).write_text("wclose\n", encoding="utf-8")
        return lambda: None

    def switch_then_state() -> Callable[[], None]:
        write_state()
        allow = state_dir / ALLOW_FILE
        allow.write_text("closeout\n", encoding="utf-8")
        return lambda: allow.unlink(missing_ok=True)

    def reap_then_state() -> Callable[[], None]:
        if train.exists():
            fx.git(primary, "worktree", "remove", "--force", str(train))
            fx.git(primary, "branch", "-D", "train/wclose")
            fx.git(primary, "push", "-q", "origin", "--delete", "train/wclose")
        write_json(state_dir / STATE_FILE, state())
        return lambda: None

    def stop(session: str) -> dict[str, object]:
        return {"hook_event_name": "Stop", "session_id": session, "stop_hook_active": False, "cwd": str(primary)}

    compact = {"hook_event_name": "SessionStart", "source": "compact", "session_id": "falsify", "cwd": str(primary)}
    path_env = {"PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"}
    return [
        FalsificationCase("stop-with-unreaped-train-tree", "Stop", stop("falsify-deny"), "deny", f"[ ] reap {train}", env(), write_state),
        FalsificationCase("stop-lists-the-remote-train-branch", "Stop", stop("falsify-deny"), "deny", "git push origin --delete train/wclose", env(), write_state),
        FalsificationCase("compact-lists-open-duties-as-context", "SessionStart", compact, "context", f"[ ] reap {train}", env(), write_state),
        FalsificationCase("pr-mode-open-pull-request-is-a-duty", "Stop", stop("falsify-deny"), "deny", "pull request #7 is not merged", env(FACTORY_GUARD_OFFLINE="", **path_env), lambda: write_state(mode="pr", pr=7)),
        FalsificationCase("stop-gives-up-after-three-denials", "Stop", stop("falsify-deny"), "context", "3 refusals used — the stop is allowed now", env(), lambda: write_state(3)),
        FalsificationCase("stop-allowed-with-closeout-switch", "Stop", stop("falsify-quiet"), "allow", "", env(), switch_then_state),
        FalsificationCase("stop-after-reap-is-silent-and-clears-state", "Stop", stop("falsify-quiet"), "allow", "", env(), reap_then_state, after=lambda: None if not (state_dir / STATE_FILE).exists() else "state file not deleted"),
        FalsificationCase("stop-without-state-file", "Stop", stop("falsify-quiet"), "allow", "", env(), clear_state),
        FalsificationCase("stop-after-manual-deletion-is-silent-and-logged", "Stop", stop("falsify-quiet"), "allow", "", env(), marker_without_state),
    ]
