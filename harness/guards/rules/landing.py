"""Landing guard (harness/guards.md §6, mechanism M-1) — both landing modes
(verification/landing-modes.md; the mechanisms around it are verification/protections.md).

PreToolUse on the shell tool, for the landing forms of lander-duties §1 step 10:

* ``git push … main`` / ``… refs/heads/main`` (or a bare ``git push`` while the default
  branch is checked out) — the direct-push override;
* ``gh pr merge <n> …`` — the pull-request mode's irreversible step;

plus two hard-form rows in the same module: ``gh pr merge`` with ``--squash``, ``--rebase``,
``--auto`` or ``--admin`` is refused naming ``--merge --match-head-commit <HEAD=>`` (the
forbidden forms of landing-modes.md §4.5), and ``gh pr create`` from a lane branch is refused
(a lane never opens a pull request; the lander boards it).

The landing is refused unless the newest exit receipt (``<train>-<n>.exit`` in the artifacts
directory) says ``EXIT=0`` for exactly this ``HEAD`` with ``BASE`` an ancestor of it; every
boarder the choices ledger records still heads its branch on origin (``git ls-remote``); the
ledger ``<ledger-dir>/<train>.md`` exists with no ``unsound`` entry lacking a fix note; for a
merge, ``--match-head-commit`` equals ``HEAD=``. Optional legs run when bound: the registry
check when the registry file changed since ``BASE`` (``FACTORY_GUARD_REGISTRY_CMD``), a
``ui-pass: <path>`` line in the ledger's ``## Landing`` section when the diff touches
``FACTORY_GUARD_UI_GLOB`` (choices-ledger README §1), and the docs-only classifier when the
receipt carries the optional line ``DOCS_ONLY=1`` (``FACTORY_GUARD_DOCS_ONLY_CMD <BASE>
<HEAD>``; harness/train-plan.md §4). The boarders the train carries are read by the gate's
``boarders_from_merges`` (the merge commits since ``BASE``) — one derivation for the guard and
the gate. The ledger lint (``check_choices_protocol --at-push``, protections.md §5) runs under
its own switch ``protocol``; ``FACTORY_GUARD_ALLOW=landing`` skips the receipt, boarder and
registry checks but never the lint, and vice versa (``HONORS_ALLOW``). A switched ``protocol``
leg answers a context note under its own id; the dispatcher logs that switch use, the rule
writes no events-log line itself (harness/guards.md §4).

PostToolUse after a push or a merge: origin is fetched and the landing counts as registered
when ``origin/<default>`` CONTAINS ``HEAD`` (``git merge-base --is-ancestor``) — never equals:
in pull-request mode main's tip is the merge commit and ``HEAD=`` its second parent. A
registered landing writes ``<state-dir>/landing-in-progress.json`` (read by the close-out
rule) and delivers the lander duties of lander-duties §8 as context; an unregistered one is
reported loudly (exit 2) with the command that shows what landed instead. The guard never
posts the ``local-verify`` status (that is the lander's step, ``post_local_verify.sh``); it
only notes, after the fact, when the combined status on the landed commit lacks it.

Inputs: the artifacts directory from a ``FACTORY_GUARD_ARTIFACTS=<dir>`` prefix on the
command (or the environment), else the ledger's ``receipts:`` line; the train name from the
branch ``train/<name>``; the ledger directory from ``FACTORY_GUARD_LEDGER_DIR`` (default
``docs/choices``); the default branch from ``FACTORY_GUARD_DEFAULT_BRANCH`` (default ``main``);
the project's declared landing mode from ``FACTORY_GUARD_LANDING_MODE_DEFAULT`` (default ``pr``).
Every binding is a ``FACTORY_GUARD_*`` parameter of harness/guards.md §8.

The guard never pushes, never merges, never rewrites a receipt, never accepts a receipt for
another HEAD, and never bypasses a hold — it can only refuse.
"""

from __future__ import annotations

import fnmatch
import pathlib
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field

from guards._common import (
    ALLOW,
    FalsificationCase,
    GuardContext,
    Verdict,
    basename,
    command_of,
    context_note,
    current_branch,
    deny,
    effective_cwd,
    git,
    is_full_sha,
    leading_assignments,
    parse_statements,
    payload_cwd,
    read_key_values,
    session_of,
    strip_prefixes,
    utc_now,
    write_json,
)
from guards.rules import _gates

ID = "landing"
PROTOCOL_ID = "protocol"
EVENTS = frozenset({"PreToolUse", "PostToolUse"})
MATCHER = "Bash"
HONORS_ALLOW = True  # the ``landing`` switch must not silence the ledger lint
STATE_FILE = "landing-in-progress.json"
SWITCHED = Verdict("allow", ID, "switched off")
LINT_GATE = "check_choices_protocol"

DEFAULT_BRANCH_VAR = "FACTORY_GUARD_DEFAULT_BRANCH"
LANDING_MODE_DEFAULT_VAR = "FACTORY_GUARD_LANDING_MODE_DEFAULT"
ARTIFACTS_VAR = "FACTORY_GUARD_ARTIFACTS"
LEDGER_DIR_VAR = "FACTORY_GUARD_LEDGER_DIR"
REGISTRY_CMD_VAR = "FACTORY_GUARD_REGISTRY_CMD"
REGISTRY_FILE_VAR = "FACTORY_GUARD_REGISTRY_FILE"
UI_GLOB_VAR = "FACTORY_GUARD_UI_GLOB"
DOCS_ONLY_CMD_VAR = "FACTORY_GUARD_DOCS_ONLY_CMD"
OFFLINE_VAR = "FACTORY_GUARD_OFFLINE"
DEFAULT_LEDGER_DIR = "docs/choices"
DEFAULT_REGISTRY_FILE = "docs/decisions/NUMBERS.md"
STATUS_CONTEXT = "local-verify"

_TRAIN_BRANCH_RE = re.compile(r"^train/(?P<train>.+)$")
_LANE_BRANCH_RE = re.compile(r"^lane/")
_RECEIPTS_LINE_RE = re.compile(r"^\s*receipts:\s*`?(.+?)`?\s*$", re.M | re.I)  # a path may carry spaces
_UI_PASS_RE = re.compile(r"^\s*ui-pass:\s*\S", re.M | re.I)
_PR_NUMBER_RE = re.compile(r"(\d+)/?$")
_PUSH_OPTIONS_WITH_OPERAND = frozenset({"--repo", "--receive-pack", "--exec", "-o", "--push-option"})
_GH_GLOBAL_WITH_OPERAND = frozenset({"-R", "--repo"})
_MERGE_OPTIONS_WITH_OPERAND = frozenset(
    {"--match-head-commit", "--body", "-b", "--body-file", "-F", "--subject", "-t", "--author-email", "-A"}
)
_HARD_MERGE_FLAGS = ("--squash", "--rebase", "--auto", "--admin")


@dataclass(frozen=True)
class Landing:
    """One landing-shaped statement: a push, a PR merge or a PR create."""

    kind: str  # push | merge | create
    directory: pathlib.Path | None
    destination: str | None = None  # push: refspec destination (None = current branch)
    pr: str | None = None  # merge: the pull request selector as typed
    match_head: str | None = None  # merge: --match-head-commit operand
    hard_flags: tuple[str, ...] = ()  # merge: --squash/--rebase/--auto/--admin present


def default_branch(environ: Mapping[str, str]) -> str:
    return environ.get(DEFAULT_BRANCH_VAR) or "main"


def _git_call(tokens: list[str]) -> tuple[pathlib.Path | None, list[str]]:
    if not tokens or basename(tokens[0]) != "git":
        return None, []
    rest = tokens[1:]
    directory: pathlib.Path | None = None
    while rest and rest[0].startswith("-"):
        if rest[0] == "-C" and len(rest) > 1:
            directory = pathlib.Path(rest[1])
            rest = rest[2:]
        elif rest[0] in {"-c", "--git-dir", "--work-tree"} and len(rest) > 1:
            rest = rest[2:]
        else:
            rest = rest[1:]
    return directory, rest


def _push_positional(rest: list[str]) -> list[str]:
    positional: list[str] = []
    skip = False
    for token in rest:
        if skip:
            skip = False
        elif token in _PUSH_OPTIONS_WITH_OPERAND:
            skip = True
        elif not token.startswith("-"):
            positional.append(token)
    return positional


def _gh_call(tokens: list[str]) -> list[str]:
    if not tokens or basename(tokens[0]) != "gh":
        return []
    rest = tokens[1:]
    while rest and rest[0].startswith("-"):
        if rest[0] in _GH_GLOBAL_WITH_OPERAND and len(rest) > 1:
            rest = rest[2:]
        else:
            rest = rest[1:]
    return rest


def _merge_of(rest: list[str]) -> Landing:
    pr: str | None = None
    match_head: str | None = None
    hard: list[str] = []
    skip = False
    for token in rest:
        if skip:
            skip = False
            continue
        if token in _MERGE_OPTIONS_WITH_OPERAND:
            skip = True
            continue
        if token.startswith("--match-head-commit="):
            match_head = token.partition("=")[2]
            continue
        if token in _HARD_MERGE_FLAGS:
            hard.append(token)
        elif not token.startswith("-") and pr is None:
            pr = token
    for index, token in enumerate(rest):
        if token == "--match-head-commit" and index + 1 < len(rest):
            match_head = rest[index + 1]
    return Landing("merge", None, pr=pr, match_head=match_head, hard_flags=tuple(hard))


def find_landings(command: str) -> list[Landing]:
    """Every landing-shaped statement in the command, in execution order."""
    landings: list[Landing] = []
    for statement in parse_statements(command):
        tokens = strip_prefixes(statement.first)
        directory, rest = _git_call(tokens)
        if rest[:1] == ["push"]:
            positional = _push_positional(rest[1:])
            refspecs = positional[1:] if positional else []
            destination = None
            if refspecs:
                spec = refspecs[0].lstrip("+")
                destination = spec.partition(":")[2] if ":" in spec else spec
                if destination == "HEAD":
                    destination = None
            landings.append(Landing("push", directory, destination=destination))
            continue
        gh = _gh_call(tokens)
        if gh[:2] == ["pr", "merge"]:
            landings.append(_merge_of(gh[2:]))
        elif gh[:2] == ["pr", "create"]:
            landings.append(Landing("create", None))
    return landings


def find_landing(command: str) -> Landing | None:
    """The first landing-shaped statement of the command, else ``None``."""
    return next(iter(find_landings(command)), None)


def _is_default_destination(context: GuardContext, landing: Landing, cwd: pathlib.Path) -> bool:
    branch = default_branch(context.environ)
    if landing.destination is not None:
        return landing.destination in {branch, f"refs/heads/{branch}"}
    return current_branch(context, cwd) == branch


def _landing_cwd(landing: Landing, command: str, payload_dir: str | None) -> pathlib.Path:
    cwd = effective_cwd(command, payload_dir)
    if landing.directory is None:
        return cwd
    return landing.directory if landing.directory.is_absolute() else (cwd / landing.directory).resolve()


def train_of(branch: str | None) -> str | None:
    match = _TRAIN_BRANCH_RE.match(branch or "")
    return match.group("train") if match else None


def ledger_path(context: GuardContext, cwd: pathlib.Path, train: str) -> pathlib.Path:
    directory = context.environ.get(LEDGER_DIR_VAR) or DEFAULT_LEDGER_DIR
    return cwd / directory / f"{train}.md"


def artifacts_dir(command: str, context: GuardContext, ledger_text: str | None) -> pathlib.Path | None:
    raw = leading_assignments(command).get(ARTIFACTS_VAR) or context.environ.get(ARTIFACTS_VAR)
    if not raw and ledger_text:
        match = _RECEIPTS_LINE_RE.search(ledger_text)
        raw = match.group(1) if match else None
    return pathlib.Path(raw).expanduser() if raw else None


def newest_receipt(directory: pathlib.Path, train: str | None) -> pathlib.Path | None:
    candidates = sorted(directory.glob(f"{train}-*.exit")) if train else []
    if not candidates:
        candidates = sorted(directory.glob("*.exit"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


@dataclass
class _State:
    context: GuardContext
    command: str
    cwd: pathlib.Path
    head: str
    branch: str
    train: str | None
    landing: Landing
    session: str = "?"
    ledger: pathlib.Path | None = None
    ledger_text: str | None = None
    directory: pathlib.Path | None = None
    receipt: pathlib.Path | None = None
    values: dict[str, str] = field(default_factory=dict)
    gate: object | None = None
    notes: list[str] = field(default_factory=list)
    merged: dict[str, str] | None = None

    def refuse(self, cause: str, fix: str) -> Verdict:
        receipt = str(self.receipt) if self.receipt else f"{self.directory or '<unknown>'}/(none)"
        return deny(
            ID,
            f"GUARD landing: {cause}. Receipt: {receipt} (EXIT={self.values.get('EXIT', '?')}, "
            f"HEAD={_short(self.values.get('HEAD'))}). Landing HEAD={_short(self.head)}. Fix: {fix}",
        )


def _short(sha: str | None) -> str:
    return sha[:8] if sha else "?"


def _run(context: GuardContext, command: list[str], cwd: pathlib.Path, timeout: float) -> tuple[int, str]:
    try:
        result = context.run(
            command, cwd=str(cwd), capture_output=True, text=True, check=False, timeout=timeout
        )
    except (OSError, subprocess.SubprocessError) as error:
        return 127, str(error)
    return result.returncode, ((result.stdout or "") + (result.stderr or "")).strip()


# --- pre-tool checks -----------------------------------------------------------------------


def _check_receipt(state: _State) -> Verdict | None:
    state.directory = artifacts_dir(state.command, state.context, state.ledger_text)
    if state.directory is None:
        return state.refuse(
            "no receipt directory is known",
            f"prefix the command with {ARTIFACTS_VAR}=<dir>, or carry «receipts: <dir>» in the "
            "ledger's «## Landing» section (harness/train-plan.md §4)",
        )
    if state.directory.is_dir():
        state.receipt = newest_receipt(state.directory, state.train)
    if state.receipt is None:
        return state.refuse(
            f"no exit receipt ({state.train or '*'}-<n>.exit) in {state.directory}",
            "run full verify through the receipt launcher on this tree (harness/train-plan.md §4.2) "
            "and land in the NEXT call",
        )
    state.values = read_key_values(state.receipt)
    exit_code = state.values.get("EXIT")
    if exit_code is None:
        return state.refuse("the receipt carries no EXIT= line", "re-run the receipt launcher; a receipt is EXIT=/BASE=/HEAD=/LOG=")
    if exit_code != "0":
        return state.refuse(
            f"the receipt is red (EXIT={exit_code})",
            f"fix the red leg, re-verify under the next run id ({state.train or '<train>'}-<n+1>) and judge only from the .exit file",
        )
    if state.values.get("HEAD") != state.head:
        return state.refuse(
            "the receipt is for another HEAD; a receipt for another HEAD is never accepted",
            "re-verify exactly this HEAD under a new run id",
        )
    base = state.values.get("BASE", "")
    if not is_full_sha(base):
        return state.refuse("the receipt carries no full BASE= SHA", "re-run the receipt launcher")
    code, _ = git(state.context, state.cwd, "merge-base", "--is-ancestor", base, state.head)
    if code != 0:
        return state.refuse(
            f"BASE={_short(base)} is not an ancestor of HEAD — the receipt verified a tree main has moved away from",
            "re-assemble on the current origin/main and re-verify (verification/lander-duties.md §3)",
        )
    return None


def _check_train(state: _State) -> Verdict | None:
    if state.train is None:
        return state.refuse(
            f"landing from branch «{state.branch or 'HEAD'}», which is not a train tree",
            "assemble the train on a train/<name> branch (verification/lander-duties.md §1) and land from there",
        )
    return None


def _gate(state: _State) -> object | None:
    if state.gate is None:
        try:
            state.gate = _gates.load_gate(state.context.environ, state.context.repo_root, LINT_GATE)
        except Exception as error:  # noqa: BLE001 — a broken gate is a loud note, never a crash
            state.notes.append(f"GUARD landing: the ledger lint could not be imported ({error}); boarders and schema not checked.")
            state.gate = None
    return state.gate


def _boarders(state: _State) -> dict[str, str]:
    gate = _gate(state)
    if gate is None or not state.ledger_text:
        return {}
    return dict(gate.boarders_from_text(state.ledger_text))  # type: ignore[attr-defined]


def _merged(state: _State) -> dict[str, str]:
    """The boarders the train carries (merge commits since BASE, else since the merge-base
    with the default branch) — read by the gate's ``boarders_from_merges``, the one derivation
    the guard and the lint share (protections.md §5)."""
    if state.merged is None:
        gate = _gate(state)
        base = state.values.get("BASE")
        if not base:
            code, base = git(state.context, state.cwd, "merge-base", f"origin/{default_branch(state.context.environ)}", state.head)
            base = base if code == 0 and base else ""
        if gate is None or not base:
            state.merged = {}
        else:
            state.merged = dict(gate.boarders_from_merges(state.cwd, base, state.head, run=state.context.run))  # type: ignore[attr-defined]
    return state.merged


def _lint_boarders(state: _State) -> list[str]:
    return sorted(set(_merged(state)) | set(_boarders(state)))


def _check_boarders(state: _State) -> Verdict | None:
    recorded = _boarders(state)
    for lane, sha in _merged(state).items():
        ledger_sha = recorded.get(lane)
        if ledger_sha and ledger_sha != sha:
            return state.refuse(
                f"the ledger records {_short(ledger_sha)} for boarder {lane} but the train merged {_short(sha)}",
                "correct the boarded SHA in the ledger's lane section, or re-assemble the train from the recorded SHA",
            )
    for lane, sha in recorded.items():
        code, listing = git(
            state.context, state.cwd, "ls-remote", "origin", f"refs/heads/lane/{lane}", f"refs/heads/{lane}", timeout=60
        )
        remote = listing.split()[0] if code == 0 and listing else None
        if remote is None:
            return state.refuse(
                f"boarder {lane} has no branch on origin (lane/{lane} or {lane})",
                f"re-resolve boarder {lane} (git ls-remote origin refs/heads/lane/{lane}) and re-assemble",
            )
        if remote != sha:
            return state.refuse(
                f"boarder {lane} moved: origin has {_short(remote)}, the train boarded {_short(sha)}",
                f"re-resolve boarder {lane} and re-assemble the train on the new branch head (lander-duties §1 step 9)",
            )
    return None


def _check_ledger(state: _State) -> Verdict | None:
    if state.ledger_text is None:
        return state.refuse(
            "the choices ledger is missing",
            f"write {state.ledger or '<ledger-dir>/<train>.md'} (interpretation/choices-ledger-README.md) and commit it on the train",
        )
    gate = _gate(state)
    findings = gate.unsound_without_fix(state.ledger_text) if gate is not None else []  # type: ignore[attr-defined]
    if findings:
        return state.refuse(
            f"the ledger has an unsound entry without a fix note ({findings[0]})",
            "resolve the unsound choice before assembly and record «fixed: <commit>» in the same section",
        )
    return None


def _changed_files(state: _State) -> list[str]:
    base = state.values.get("BASE")
    if not base:
        return []
    code, listing = git(state.context, state.cwd, "diff", "--name-only", f"{base}..{state.head}")
    return listing.splitlines() if code == 0 else []


def _check_optional_legs(state: _State) -> Verdict | None:
    environ = state.context.environ
    changed = _changed_files(state)
    registry_cmd = environ.get(REGISTRY_CMD_VAR)
    registry_file = environ.get(REGISTRY_FILE_VAR) or DEFAULT_REGISTRY_FILE
    if registry_cmd and registry_file in changed:
        code, output = _run(state.context, ["/bin/sh", "-c", registry_cmd], state.cwd, timeout=300)
        if code != 0:
            tail = "\n".join(output.splitlines()[-8:])
            return state.refuse(
                f"the registry file changed since BASE and the registry check is red (exit {code}):\n{tail}\n",
                f"make the registry check green first: {registry_cmd}",
            )
    ui_glob = environ.get(UI_GLOB_VAR)
    if ui_glob and any(fnmatch.fnmatch(path, pattern) for path in changed for pattern in ui_glob.split(",") if pattern):
        if not (state.ledger_text and _UI_PASS_RE.search(state.ledger_text)):
            return state.refuse(
                f"the train touches {ui_glob} without a «ui-pass:» line in the ledger",
                "take the lander's rendered pass on a fresh build and write «ui-pass: <path>» in the ledger's «## Landing» section",
            )
    if state.values.get("DOCS_ONLY") == "1":
        docs_cmd = environ.get(DOCS_ONLY_CMD_VAR)
        if not docs_cmd:
            return state.refuse(
                "the receipt claims DOCS_ONLY=1 but no docs-only classifier is bound",
                f"bind {DOCS_ONLY_CMD_VAR} in the operations doc, or verify the train in full",
            )
        code, output = _run(state.context, ["/bin/sh", "-c", f"{docs_cmd} {state.values.get('BASE', '')} {state.head}"], state.cwd, timeout=300)
        if code != 0:
            tail = "\n".join(output.splitlines()[-6:])
            return state.refuse(
                f"docs-only receipt, but the classifier rejects the diff:\n{tail}\n",
                "verify the train in full through the receipt launcher",
            )
    return None


def _check_merge_form(state: _State) -> Verdict | None:
    landing = state.landing
    if landing.kind != "merge":
        return None
    form = f"gh pr merge {landing.pr or '<n>'} --merge --match-head-commit {state.values.get('HEAD') or state.head}"
    if landing.hard_flags:
        flag = landing.hard_flags[0]
        why = {
            "--squash": "rewrites the SHAs the receipt, the ancestor checks and the registry flip bind to",
            "--rebase": "rewrites the SHAs the receipt, the ancestor checks and the registry flip bind to",
            "--auto": "merges after the session ends, unattended and unreceipted",
            "--admin": "is a silent bypass of the branch policy",
        }[flag]
        return deny(
            ID,
            f"GUARD landing: «gh pr merge {flag}» {why} (verification/landing-modes.md §4.5). "
            f"Fix: {form}",
            escape="none — a hard form (verification/landing-modes.md §4.5)",
        )
    if not landing.match_head:
        return state.refuse(
            "«gh pr merge» without --match-head-commit merges whatever the branch points at",
            form,
        )
    if landing.match_head != state.head:
        return state.refuse(
            f"--match-head-commit {_short(landing.match_head)} is not this tree's HEAD",
            form,
        )
    return None


def _check_create(context: GuardContext, cwd: pathlib.Path) -> Verdict:
    branch = current_branch(context, cwd) or ""
    if not _LANE_BRANCH_RE.match(branch):
        return ALLOW
    return deny(
        ID,
        f"GUARD landing: «gh pr create» from lane branch «{branch}» — a lane never opens a pull "
        "request; push the branch, the lander boards it (planning/lane-brief-template.md §2). "
        f"Fix: git push origin {branch}",
        escape="none — a hard form (verification/landing-modes.md §4)",
    )


def _lint(state: _State) -> Verdict | None:
    """M-7 as HARD: every schema finding refuses the landing under the ``protocol`` switch."""
    if state.train is None or state.ledger_text is None:
        return None
    gate = _gate(state)
    if gate is None:
        state.notes.append(
            f"GUARD landing: the ledger lint ({LINT_GATE}.py) was not found under "
            f"{_gates.GATES_DIR_VAR}, <repo>/scripts or <repo>/verification/gates — boarders and schema not checked."
        )
        return None
    findings = gate.protocol_findings(  # type: ignore[attr-defined]
        state.ledger_text,
        _lint_boarders(state),
        train=state.train,
        at_push=True,
        default_mode=state.context.environ.get(LANDING_MODE_DEFAULT_VAR) or "pr",
    )
    if not findings:
        return None
    if state.context.switched_off(PROTOCOL_ID):
        # A leg-level switch: the note carries the leg's id, and the dispatcher logs the
        # switch use for any context note under a switched id (harness/guards.md §4).
        return context_note(
            PROTOCOL_ID,
            f"GUARD protocol: ledger lint overridden (FACTORY_GUARD_ALLOW={PROTOCOL_ID}) — record the "
            "choice as an O-entry in the ledger: " + "; ".join(findings),
        )
    listed = "\n".join(f"  [HARD] {finding}" for finding in findings)
    return deny(
        PROTOCOL_ID,
        f"GUARD protocol: the ledger lint (M-7) has {len(findings)} finding(s) in "
        f"{state.ledger}:\n{listed}\nLanding HEAD={_short(state.head)}. Fix: finish the ledger per "
        f"interpretation/choices-ledger-README.md and run python3 -m scripts.{LINT_GATE} "
        f"{state.train} --at-push",
    )


def _notes(*verdicts: Verdict | None, extra: list[str] = ()) -> Verdict | None:  # type: ignore[assignment]
    notes = [verdict for verdict in verdicts if verdict is not None]
    messages = [note.message for note in notes] + list(extra)
    if not messages:
        return None
    return context_note(notes[0].id if notes else ID, "\n\n".join(messages))


def _pre_landing(context: GuardContext, command: str, cwd: pathlib.Path, landing: Landing, session: str = "?") -> Verdict:
    code, head = git(context, cwd, "rev-parse", "HEAD")
    if code != 0 or not head:
        return deny(ID, f"GUARD landing: {cwd} is not a git tree. Fix: land from the train worktree")
    branch = current_branch(context, cwd) or ""
    state = _State(context, command, cwd, head, branch, train_of(branch), landing, session=session)
    if state.train is not None:
        state.ledger = ledger_path(context, cwd, state.train)
        state.ledger_text = state.ledger.read_text(encoding="utf-8") if state.ledger.is_file() else None
    if landing.kind == "merge" and landing.hard_flags:
        return _check_merge_form(state)
    if context.switched_off(ID):
        return _lint(state) or _notes(extra=state.notes) or SWITCHED
    verdict = (
        _check_receipt(state)
        or _check_train(state)
        or _check_merge_form(state)
        or _check_boarders(state)
        or _check_ledger(state)
        or _check_optional_legs(state)
    )
    if verdict is not None:
        return verdict
    lint = _lint(state)
    if lint is not None and lint.kind == "deny":
        return lint
    return _notes(lint, extra=state.notes) or ALLOW


# --- post-tool: registration, state file, lander duties -------------------------------------

LANDER_DUTIES = (
    "  [ ] origin/<default> contains the receipt HEAD (the landing registered)",
    "  [ ] pr mode: the pull request reads MERGED (gh pr view <n> --json state)",
    "  [ ] remote train branch deleted: git push origin --delete train/<name>",
    "  [ ] registry rows flipped claimed → landed",
    "  [ ] board sweep, then ONE landed notification keyed on the train HEAD (the merge SHA in the comment, never the key)",
    "  [ ] primary fast-forwarded: git -C <primary> pull --ff-only origin <default>",
    "  [ ] merged worktrees reaped after the ancestor check and the worktree-ritual teardown checks",
    "  [ ] served instances torn down by port",
    "  [ ] build product fresh when the train touched its inputs",
    "  [ ] disk above the floor",
)


def _pr_number(landing: Landing) -> int | None:
    if landing.pr is None:
        return None
    match = _PR_NUMBER_RE.search(landing.pr)
    return int(match.group(1)) if match else None


def _status_note(context: GuardContext, cwd: pathlib.Path, head: str) -> str | None:
    """Context only, after the fact, and only when ``gh`` can be asked: the combined status on
    the landed commit lacks ``local-verify``. Offline or without ``gh`` there is nothing to say —
    the poster itself is loud about both."""
    if context.environ.get(OFFLINE_VAR) == "1":
        return None
    code, output = _run(context, ["gh", "auth", "status"], cwd, timeout=20)
    if code != 0:
        return None
    code, output = _run(
        context,
        ["gh", "api", f"repos/{{owner}}/{{repo}}/commits/{head}/status", "--jq", ".statuses[].context"],
        cwd,
        timeout=30,
    )
    if code != 0 or STATUS_CONTEXT in output.split():
        return None
    return (
        f"GUARD landing: the landed commit {_short(head)} carries no «{STATUS_CONTEXT}» status — post it "
        f"from the receipt: verification/protections/post_local_verify.sh <receipt> (landing-modes.md §2)."
    )


def _record_landing(context: GuardContext, command: str, cwd: pathlib.Path, head: str, landing: Landing) -> Verdict:
    branch = current_branch(context, cwd) or ""
    train = train_of(branch) or branch or default_branch(context.environ)
    ledger = ledger_path(context, cwd, train)
    ledger_text = ledger.read_text(encoding="utf-8") if ledger.is_file() else None
    directory = artifacts_dir(command, context, ledger_text)
    state = _State(context, command, cwd, head, branch, train_of(branch), landing)
    state.ledger_text = ledger_text
    boarders = {**_merged(state), **_boarders(state)}
    mode = "pr" if landing.kind == "merge" else "direct-push"
    path = context.state_dir / STATE_FILE
    write_json(
        path,
        {
            "train": train,
            "head": head,
            "mode": mode,
            "pr": _pr_number(landing),
            "boarders": boarders,
            "artifacts_dir": str(directory) if directory else None,
            "default_branch": default_branch(context.environ),
            "pushed_at": utc_now(),
            "denials": 0,
        },
    )
    duties = "\n".join(LANDER_DUTIES)
    text = (
        f"GUARD landing: LANDER DUTIES (verification/lander-duties.md §8 — train {train} registered in "
        f"{mode} mode, origin/{default_branch(context.environ)} contains {_short(head)}):\n{duties}\n"
        f"  State file: {path} (deleted by the close-out rule when every duty is closed; "
        f"python3 -m scripts.check_landing_closeout --state {path} prints the open ones)"
    )
    extra = [note for note in [_status_note(context, cwd, head)] if note]
    return context_note(ID, "\n\n".join([text, *state.notes, *extra]))


def _post_landing(context: GuardContext, command: str, cwd: pathlib.Path, landing: Landing) -> Verdict:
    code, head = git(context, cwd, "rev-parse", "HEAD")
    if code != 0 or not head:
        return ALLOW
    branch = default_branch(context.environ)
    code, output = git(context, cwd, "fetch", "-q", "origin", timeout=120)
    if code != 0:
        return context_note(ID, f"GUARD landing: could not confirm the landing (git fetch origin failed: {output[:120]}).")
    code, _ = git(context, cwd, "merge-base", "--is-ancestor", head, f"origin/{branch}")
    if code == 0:
        return _record_landing(context, command, cwd, head, landing)
    _, behind = git(context, cwd, "log", "--oneline", "--max-count=10", f"{head}..origin/{branch}")
    what = "merge" if landing.kind == "merge" else "push"
    return Verdict(
        "deny",
        ID,
        f"GUARD landing: the {what} did not register — origin/{branch} does not contain HEAD={_short(head)}. "
        f"Read origin/{branch} before a new attempt (a parallel session may have landed the same): "
        f"git log HEAD..origin/{branch}\n" + (behind or "(no new commits visible)"),
    )


def check(payload: Mapping[str, object], context: GuardContext) -> Verdict:
    command = command_of(payload)
    first_verdict: Verdict | None = None
    for landing in find_landings(command):
        cwd = _landing_cwd(landing, command, payload_cwd(payload))
        if landing.kind == "create":
            verdict = _check_create(context, cwd) if context.event == "PreToolUse" else ALLOW
        elif landing.kind == "push" and not _is_default_destination(context, landing, cwd):
            continue
        elif context.event == "PostToolUse":
            verdict = SWITCHED if context.switched_off(ID) else _post_landing(context, command, cwd, landing)
        else:
            verdict = _pre_landing(context, command, cwd, landing, session_of(payload))
        if verdict.kind == "deny":
            return verdict
        if first_verdict is None or (first_verdict == ALLOW and verdict != ALLOW):
            first_verdict = verdict
    return first_verdict or ALLOW


def falsification_cases(workdir: pathlib.Path) -> list[FalsificationCase]:
    from guards.rules import _landing_fixtures

    return _landing_fixtures.landing_cases(workdir)
