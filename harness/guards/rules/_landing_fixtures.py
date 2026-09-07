"""Real-git falsification fixtures for the landing rule (both modes) and the pre-push hook rule.

One template per work directory — a bare origin holding ``main`` and ``lane/alpha``, and a
clone on ``train/wtest`` with the boarder merged ``--no-ff`` — copied per case and then
varied: the ledger committed (or not, or with a planted schema break), the receipt written
for exactly HEAD (or red, or for another HEAD), the boarder moved on origin, the train
merged into ``origin/main`` by a merge commit whose second parent is HEAD (pull-request
registration), or main left where it was (an unregistered push). No fake ``git``: the rule
reads the same repository a lander would. Underscore-prefixed, so the loader skips it.
"""

from __future__ import annotations

import os
import pathlib
import shlex
import shutil
import subprocess
from dataclasses import dataclass

from guards._common import FalsificationCase

EMAIL = "lander@example.invalid"
OTHER_SHA = "d" * 40
PUSH = "git push origin HEAD:main"
LEDGER = """# Choices ledger — train wtest (falsification train)

Audited by the falsification runner with audit-choices, {date}.

## Lane `alpha` — boarded {boarder} — two sound

**alpha-1** The lane keeps the constant in the runtime module (sound, H).
**alpha-2** The test pins behaviour, not the helper (sound, M).

## Orchestrator choices

**O-1 — single boarder:** single-lane train — priority P1 (the falsification fixture carries one lane) (sound, H).

## Landing

landing mode: {mode}
{mode_lines}receipts: {artifacts}
local-verify: skipped (no host in the fixture)
"""


def git(cwd: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), "-c", f"user.email={EMAIL}", "-c", "user.name=lander", *args],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    return result.stdout.strip()


@dataclass(frozen=True)
class Template:
    origin: pathlib.Path
    train: pathlib.Path
    main_sha: str
    boarder_sha: str


def template(workdir: pathlib.Path) -> Template:
    root = workdir / "_template"
    origin = root / "origin.git"
    train = root / "train"
    marker = root / "ready"
    if marker.is_file():
        return Template(origin, train, git(train, "rev-parse", "origin/main"), git(train, "rev-parse", "origin/lane/alpha"))
    shutil.rmtree(root, ignore_errors=True)
    origin.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    seed = root / "seed"
    seed.mkdir()
    git(seed, "init", "-q", "-b", "main")
    git(seed, "config", "user.email", EMAIL)
    git(seed, "config", "user.name", "lander")
    git(seed, "remote", "add", "origin", str(origin))
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    git(seed, "add", "README.md")
    git(seed, "commit", "-q", "-m", "init")
    git(seed, "push", "-q", "-u", "origin", "main")
    main_sha = git(seed, "rev-parse", "HEAD")
    git(seed, "checkout", "-q", "-b", "lane/alpha")
    (seed / "src" / "pkg").mkdir(parents=True)
    (seed / "src" / "pkg" / "x.py").write_text("X = 1\n", encoding="utf-8")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "feat(pkg): x")
    git(seed, "push", "-q", "origin", "lane/alpha")
    boarder_sha = git(seed, "rev-parse", "HEAD")
    subprocess.run(["git", "clone", "-q", str(origin), str(train)], check=True)
    git(train, "config", "user.email", EMAIL)
    git(train, "config", "user.name", "lander")
    git(train, "checkout", "-q", "-b", "train/wtest", "origin/main")
    git(train, "merge", "-q", "--no-ff", "origin/lane/alpha", "-m", f"train(wtest): board alpha ({boarder_sha})")
    marker.write_text("ready\n", encoding="utf-8")
    return Template(origin, train, main_sha, boarder_sha)


def ledger_text(artifacts: pathlib.Path, boarder: str, *, mode: str = "direct-push", pr: int | None = None) -> str:
    if mode == "pr":
        mode_lines = f"pr: {pr or 7}\n"
    else:
        mode_lines = "override reason: the falsification fixture has no pull-request host\n"
    return LEDGER.format(date="2026-09-06", boarder=boarder, mode=mode, mode_lines=mode_lines, artifacts=artifacts)


@dataclass(frozen=True)
class Tree:
    root: pathlib.Path
    origin: pathlib.Path
    train: pathlib.Path
    head: str
    main_sha: str
    boarder_sha: str
    artifacts: pathlib.Path

    def env(self, **extra: str) -> dict[str, str]:
        return {"FACTORY_GUARD_STATE_DIR": str(self.root / "state"), "GIT_TERMINAL_PROMPT": "0", **extra}


def case_tree(
    workdir: pathlib.Path,
    name: str,
    *,
    exit_code: str = "0",
    head_mismatch: bool = False,
    moved_boarder: bool = False,
    ledger: str | None = "green",
    mode: str = "direct-push",
    pr: int | None = None,
    registered: str | None = None,  # None | "push" | "merge"
    lane_checkout: bool = False,
    push_train: bool = True,
    receipt_extra: str = "",  # optional receipt lines after LOG= (train-plan §4: DOCS_ONLY=1)
) -> Tree:
    """A copy of the template varied for one case; ``ledger`` is ``"green"``, ``None`` (no
    ledger committed) or the ledger text to commit (``{artifacts}``/``{boarder}`` filled)."""
    base = template(workdir)
    root = workdir / name
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    origin = root / "origin.git"
    train = root / "train"
    shutil.copytree(base.origin, origin)
    shutil.copytree(base.train, train)
    git(train, "remote", "set-url", "origin", str(origin))
    artifacts = root / "artifacts"
    artifacts.mkdir()
    if moved_boarder:
        scratch = root / "scratch"
        subprocess.run(["git", "clone", "-q", "-b", "lane/alpha", str(origin), str(scratch)], check=True)
        (scratch / "src" / "pkg" / "y.py").write_text("Y = 2\n", encoding="utf-8")
        git(scratch, "add", "-A")
        git(scratch, "commit", "-q", "-m", "feat(pkg): y")
        git(scratch, "push", "-q", "origin", "lane/alpha")
    if ledger is not None:
        text = ledger_text(artifacts, base.boarder_sha, mode=mode, pr=pr) if ledger == "green" else ledger
        text = text.replace("{artifacts}", str(artifacts)).replace("{boarder}", base.boarder_sha)
        (train / "docs" / "choices").mkdir(parents=True, exist_ok=True)
        (train / "docs" / "choices" / "wtest.md").write_text(text, encoding="utf-8")
        git(train, "add", "-A")
        git(train, "commit", "-q", "-m", "train(wtest): choices ledger")
    head = git(train, "rev-parse", "HEAD")
    if push_train:
        git(train, "push", "-q", "-u", "origin", "train/wtest")
    receipt_head = OTHER_SHA if head_mismatch else head
    (artifacts / "wtest-1.log").write_text("verify log\n", encoding="utf-8")
    (artifacts / "wtest-1.exit").write_text(
        f"EXIT={exit_code}\nBASE={base.main_sha}\nHEAD={receipt_head}\nLOG={artifacts / 'wtest-1.log'}\n{receipt_extra}",
        encoding="utf-8",
    )
    if registered == "push":
        git(train, "push", "-q", "origin", "HEAD:main")
    elif registered == "merge":
        scratch = root / "merge-scratch"
        subprocess.run(["git", "clone", "-q", str(origin), str(scratch)], check=True)
        git(scratch, "merge", "-q", "--no-ff", "origin/train/wtest", "-m", "Merge pull request #7 from origin/train/wtest")
        git(scratch, "push", "-q", "origin", "HEAD:main")
    if lane_checkout:
        git(train, "checkout", "-q", "-b", "lane/alpha", "origin/lane/alpha")
    return Tree(root, origin, train, head, base.main_sha, base.boarder_sha, artifacts)


def bash_payload(event: str, cwd: pathlib.Path, command: str) -> dict[str, object]:
    return {
        "hook_event_name": event,
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(cwd),
        "session_id": "falsify",
        "tool_response": {"stdout": "", "stderr": ""},
    }


def pre_push_payload(cwd: pathlib.Path, refs: list[tuple[str, str, str, str]], remote: str = "origin") -> dict[str, object]:
    """The payload ``verification/protections/git_hooks.py pre-push`` builds from git's stdin."""
    return {
        "hook_event_name": "GitPrePush",
        "cwd": str(cwd),
        "session_id": "falsify",
        "git": {
            "hook": "pre-push",
            "remote": remote,
            "url": str(cwd.parent / "origin.git"),
            "refs": [
                {"local_ref": local_ref, "local_sha": local_sha, "remote_ref": remote_ref, "remote_sha": remote_sha}
                for local_ref, local_sha, remote_ref, remote_sha in refs
            ],
        },
    }


def _case(name: str, expect: str, needle: str, tree: Tree, command: str = PUSH, event: str = "PreToolUse", env: dict[str, str] | None = None, after=None) -> FalsificationCase:
    return FalsificationCase(
        name,
        event,
        bash_payload(event, tree.train, command),
        expect,  # type: ignore[arg-type]
        needle,
        tree.env(**(env or {})),
        after=after,
    )


def _state_written(tree: Tree, mode: str, pr: int | None) -> str | None:
    import json

    path = tree.root / "state" / "landing-in-progress.json"
    if not path.is_file():
        return f"state file missing: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("mode") != mode or data.get("pr") != pr or data.get("head") != tree.head:
        return f"state file wrong: {data}"
    return None


# A ledger only the lint can fault: the entries carry no confidence mark (README §1) — the
# receipt, the boarders and the unsound check are all still green on it.
BROKEN_LEDGER = LEDGER.replace("(sound, H).\n**alpha-2**", "(sound).\n**alpha-2**").replace("helper (sound, M).", "helper (sound).")
# A ledger whose lane section is renamed: the lint faults it only when the boarder list comes
# from the train's merge commits, never from the ledger itself.
RENAMED_LEDGER = LEDGER.replace("## Lane `alpha` — boarded {boarder} — two sound", "## Lane `beta` — boarded {boarder} — two sound")
# A ledger whose «## Landing» section carries the rendered pass (choices-ledger README §1).
UI_PASS_LEDGER = LEDGER.replace(
    "local-verify: skipped (no host in the fixture)\n",
    "local-verify: skipped (no host in the fixture)\nui-pass: {artifacts}/pass.png\n",
)


def direct_push_ledger(template: str) -> str:
    """A ledger template filled for the direct-push fixture (``{artifacts}``/``{boarder}`` stay
    for ``case_tree`` to fill)."""
    return template.replace("{mode}", "direct-push").replace("{mode_lines}", "override reason: fixture\n").replace("{date}", "2026-09-06")


def landing_cases(workdir: pathlib.Path) -> list[FalsificationCase]:
    cases: list[FalsificationCase] = []
    tree = case_tree(workdir, "red-receipt", exit_code="2")
    cases.append(_case("red-receipt", "deny", "the receipt is red (EXIT=2)", tree))
    tree = case_tree(workdir, "other-head", head_mismatch=True)
    cases.append(_case("receipt-for-other-head", "deny", "the receipt is for another HEAD", tree))
    tree = case_tree(workdir, "moved-boarder", moved_boarder=True)
    cases.append(_case("moved-boarder", "deny", "boarder alpha moved", tree))
    tree = case_tree(workdir, "no-ledger", ledger=None)
    cases.append(_case("missing-ledger", "deny", "the choices ledger is missing", tree, f"FACTORY_GUARD_ARTIFACTS={shlex.quote(str(tree.artifacts))} {PUSH}"))  # a path may carry spaces
    unsound = LEDGER.replace("**alpha-2** The test pins behaviour, not the helper (sound, M).", "**alpha-2** The helper was inlined (unsound, L).")
    tree = case_tree(workdir, "unsound", ledger=unsound.replace("{mode}", "direct-push").replace("{mode_lines}", "override reason: fixture\n").replace("{date}", "2026-09-06"))
    cases.append(_case("unsound-without-fix", "deny", "unsound entry without a fix note", tree))
    tree = case_tree(workdir, "merge-squash", mode="pr", pr=7)
    cases.append(_case("merge-with-squash", "deny", "«gh pr merge --squash» rewrites the SHAs", tree, f"gh pr merge 7 --squash --match-head-commit {tree.head}"))
    cases.append(_case("merge-with-auto", "deny", f"--merge --match-head-commit {tree.head}", tree, "gh pr merge 7 --auto --merge"))
    cases.append(_case("merge-without-match-head", "deny", "without --match-head-commit", tree, "gh pr merge 7 --merge"))
    cases.append(_case("merge-with-wrong-match-head", "deny", "is not this tree's HEAD", tree, f"gh pr merge 7 --merge --match-head-commit {OTHER_SHA}"))
    cases.append(_case("green-merge", "allow", "", tree, f"gh pr merge 7 --merge --match-head-commit {tree.head}"))
    lane = case_tree(workdir, "lane-create", lane_checkout=True)
    cases.append(_case("pr-create-from-lane-branch", "deny", "push the branch, the lander boards it", lane, "gh pr create --base main --head lane/alpha --title x --body y"))
    tree = case_tree(workdir, "green")
    cases.append(_case("green-push", "allow", "", tree))
    cases.append(_case("push-of-lane-branch", "allow", "", tree, "git push origin lane/alpha"))
    cases.append(
        _case(
            "non-default-push-before-forbidden-merge",
            "deny",
            "«gh pr merge --squash» rewrites the SHAs",
            tree,
            "git push origin HEAD:train/x && gh pr merge 7 --squash",
        )
    )
    tree = case_tree(workdir, "registered-merge", mode="pr", pr=7, registered="merge")
    cases.append(
        _case(
            "post-merge-registered-second-parent",
            "context",
            "LANDER DUTIES",
            tree,
            f"gh pr merge 7 --merge --match-head-commit {tree.head}",
            event="PostToolUse",
            after=lambda t=tree: _state_written(t, "pr", 7),
        )
    )
    tree = case_tree(workdir, "registered-push", registered="push")
    cases.append(_case("post-push-registered", "context", "LANDER DUTIES", tree, event="PostToolUse", after=lambda t=tree: _state_written(t, "direct-push", None)))
    tree = case_tree(workdir, "unregistered")
    cases.append(_case("post-push-not-registered", "deny", "did not register", tree, event="PostToolUse"))
    tree = case_tree(workdir, "landing-switch-lints", ledger=BROKEN_LEDGER.replace("{mode}", "direct-push").replace("{mode_lines}", "override reason: fixture\n").replace("{date}", "2026-09-06"), exit_code="2")
    cases.append(_case("landing-switch-does-not-cover-the-lint", "deny", "GUARD protocol: the ledger lint (M-7)", tree, f"FACTORY_GUARD_ALLOW=landing {PUSH}"))
    tree = case_tree(workdir, "protocol-switch", ledger=BROKEN_LEDGER.replace("{mode}", "direct-push").replace("{mode_lines}", "override reason: fixture\n").replace("{date}", "2026-09-06"))
    cases.append(_case("protocol-switch-gives-context", "context", "ledger lint overridden", tree, f"FACTORY_GUARD_ALLOW=protocol {PUSH}"))
    tree = case_tree(workdir, "renamed-section", ledger=RENAMED_LEDGER.replace("{mode}", "direct-push").replace("{mode_lines}", "override reason: fixture\n").replace("{date}", "2026-09-06"))
    cases.append(_case("merged-boarder-without-ledger-section", "deny", "missing section «## Lane `alpha`»", tree, f"FACTORY_GUARD_ALLOW=landing {PUSH}"))
    tree = case_tree(workdir, "escape", exit_code="2")
    cases.append(_case("landing-switch-skips-the-receipt", "allow", "", tree, f"FACTORY_GUARD_ALLOW=landing {PUSH}"))
    # The optional legs, bound (protections.md §1.1): the boarder's src/ files changed since BASE.
    tree = case_tree(workdir, "ui-glob")
    cases.append(_case("ui-glob-without-ui-pass-line", "deny", "without a «ui-pass:» line in the ledger", tree, env={"FACTORY_GUARD_UI_GLOB": "src/*"}))
    tree = case_tree(workdir, "ui-pass", ledger=direct_push_ledger(UI_PASS_LEDGER))
    cases.append(_case("ui-glob-with-ui-pass-line", "allow", "", tree, env={"FACTORY_GUARD_UI_GLOB": "src/*"}))
    tree = case_tree(workdir, "docs-only-unbound", receipt_extra="DOCS_ONLY=1\n")
    cases.append(_case("docs-only-receipt-without-classifier", "deny", "no docs-only classifier is bound", tree))
    tree = case_tree(workdir, "docs-only-rejected", receipt_extra="DOCS_ONLY=1\n")
    cases.append(_case("docs-only-receipt-classifier-rejects", "deny", "the classifier rejects the diff", tree, env={"FACTORY_GUARD_DOCS_ONLY_CMD": "false"}))
    return cases
