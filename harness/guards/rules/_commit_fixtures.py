"""Real-git fixtures for the commit-msg and pre-commit rules' falsification cases.

``commit_repo`` initialises a tiny repository with the declared identity, one committed
``README.md`` and ``docs/decisions/0097-x.md`` (so ``Refs: ADR-0097`` resolves), optionally
with ``src/pkg/x.py`` in that commit (``head_src``), then stages what the case needs: a
``src/`` change by default, extra staged files, nothing at all (``stage=False``: the amend
shape), or a fake merge in progress (``.git/MERGE_HEAD``). Underscore-prefixed, so the
loader skips it.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess

DECLARED_EMAIL = "factory@example.invalid"


def _run(cwd: pathlib.Path, *args: str) -> str:
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def commit_repo(
    workdir: pathlib.Path,
    name: str,
    *,
    email: str = DECLARED_EMAIL,
    staged_src: bool = True,
    extra_staged: dict[str, str] | None = None,
    extra_untracked: dict[str, str] | None = None,
    merge: bool = False,
    head_src: bool = False,
    stage: bool = True,
) -> pathlib.Path:
    root = workdir / name
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    _run(root, "git", "init", "-q", "-b", "main")
    _run(root, "git", "config", "user.email", email)
    _run(root, "git", "config", "user.name", "factory")
    _run(root, "git", "config", "commit.gpgsign", "false")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    (root / "docs" / "decisions").mkdir(parents=True)
    (root / "docs" / "decisions" / "0097-x.md").write_text("# ADR-0097\n", encoding="utf-8")
    if head_src:
        (root / "src" / "pkg").mkdir(parents=True)
        (root / "src" / "pkg" / "x.py").write_text("X = 0\n", encoding="utf-8")
    _run(root, "git", "add", "-A")
    _run(root, "git", "commit", "-q", "-m", "init")
    files = dict(extra_staged or {})
    if not stage:
        files = {}
    elif staged_src:
        files.setdefault("src/pkg/x.py", "X = 1\n")
    else:
        files.setdefault("docs/note.md", "note\n")
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    _run(root, "git", "add", "-A")
    for rel, text in (extra_untracked or {}).items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    if merge:
        head = _run(root, "git", "rev-parse", "HEAD")
        (root / ".git" / "MERGE_HEAD").write_text(head + "\n", encoding="utf-8")
    return root
