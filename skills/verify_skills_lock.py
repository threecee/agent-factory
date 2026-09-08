#!/usr/bin/env python3
"""Content lock for the vendored skill set (`skills/skills-lock.json`).

The lock answers one question mechanically: are the skill directories the
ones this package shipped, byte for byte? It is a CONTENT digest, not a
signature and not an upstream pin — upstream commit refs were not recorded
when the skills were vendored, so `origin` is attribution (see
ATTRIBUTION.md), never a fetchable reference.

    python3 skills/verify_skills_lock.py            # check; exit 1 on drift, missing or extra skill
    python3 skills/verify_skills_lock.py --check    # explicit form of the same check
    python3 skills/verify_skills_lock.py --report   # print per-skill digests, exit 0
    python3 skills/verify_skills_lock.py --update   # rewrite the lock (the ONLY path to a new lock)

`--check` is run from the package (must be green on an untouched checkout)
and from the installed copy (`.agents/skills/`) via `--root <dir>`. A local
adaptation is legitimate; it is recorded by `--update` on the copy, with the
reason in the repo's ATTRIBUTION, never by editing the JSON by hand.

Digest algorithm (stdlib only; recomputable with coreutils, so a repo
without Python can verify it):

    per skill directory (a direct child of --root that contains SKILL.md):
      for every regular file below it, excluding __pycache__/ and .DS_Store,
      one line  "<relative path>\\t<sha256 hex of the file>\\n"
      sorted by relative path in byte order (LC_ALL=C)
      tree_sha256 = sha256 of the concatenated lines

    shell equivalent, from inside one skill directory:
      find . -type f ! -path '*/__pycache__/*' ! -name .DS_Store \\
        | sed 's|^\\./||' | LC_ALL=C sort \\
        | while read -r f; do printf '%s\\t%s\\n' "$f" "$(sha256sum "$f" | cut -d' ' -f1)"; done \\
        | sha256sum

Exit codes: 0 verified / reported / updated; 1 drift, missing or extra skill;
2 usage or unreadable lock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

LOCK_NAME = "skills-lock.json"
_SKIP_DIRS = {"__pycache__"}
_SKIP_FILES = {".DS_Store"}


def _file_sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_digest(skill_dir: pathlib.Path) -> tuple[str, int]:
    """(tree_sha256, file count) for one skill directory, per the docstring."""
    lines: list[tuple[bytes, str]] = []
    for path in skill_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir)
        if any(part in _SKIP_DIRS for part in rel.parts) or rel.name in _SKIP_FILES:
            continue
        lines.append((rel.as_posix().encode("utf-8"), _file_sha256(path)))
    lines.sort(key=lambda item: item[0])
    h = hashlib.sha256()
    for rel_bytes, digest in lines:
        h.update(rel_bytes + b"\t" + digest.encode("ascii") + b"\n")
    return h.hexdigest(), len(lines)


def iter_skill_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())


def load_lock(lock_path: pathlib.Path) -> dict:
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[skills-lock] no lock file at {lock_path} (exit 2)")
    except json.JSONDecodeError as exc:
        sys.exit(f"[skills-lock] unreadable lock {lock_path}: {exc} (exit 2)")
    if data.get("version") != 1 or not isinstance(data.get("skills"), dict):
        sys.exit(f"[skills-lock] {lock_path} is not a version-1 lock (exit 2)")
    return data


def check(root: pathlib.Path, lock_path: pathlib.Path) -> int:
    lock = load_lock(lock_path)
    locked = lock["skills"]
    present = {p.name: p for p in iter_skill_dirs(root)}
    problems: list[str] = []
    for name in sorted(set(locked) | set(present)):
        if name not in present:
            problems.append(f"missing: {name} is locked but not present under {root}")
            continue
        if name not in locked:
            problems.append(f"extra: {name} is present under {root} but not locked")
            continue
        got, n = tree_digest(present[name])
        want = locked[name].get("tree_sha256")
        if got != want:
            problems.append(
                f"drift: {name} tree_sha256 {got[:12]}… ({n} files) != locked {str(want)[:12]}…"
            )
    if problems:
        print(f"[skills-lock] HARD: {len(problems)} problem(s) against {lock_path}")
        for line in problems:
            print("  " + line)
        print("[skills-lock] a deliberate local adaptation is recorded with --update and a note in ATTRIBUTION.md")
        return 1
    print(f"[skills-lock] verified: {len(present)} skill(s) under {root} match {lock_path}")
    return 0


def report(root: pathlib.Path, lock_path: pathlib.Path) -> int:
    locked = load_lock(lock_path)["skills"] if lock_path.exists() else {}
    for skill in iter_skill_dirs(root):
        digest, n = tree_digest(skill)
        state = "locked" if locked.get(skill.name, {}).get("tree_sha256") == digest else "UNLOCKED/DRIFT"
        origin = locked.get(skill.name, {}).get("origin", "-")
        print(f"{skill.name:34} {digest[:16]}  {n:3d} files  {state:14} {origin}")
    return 0


def update(root: pathlib.Path, lock_path: pathlib.Path) -> int:
    previous = {}
    if lock_path.exists():
        previous = load_lock(lock_path)["skills"]
    skills = {}
    for skill in iter_skill_dirs(root):
        digest, n = tree_digest(skill)
        entry = dict(previous.get(skill.name, {}))
        entry.setdefault("origin", "unrecorded — add to ATTRIBUTION.md")
        entry["tree_sha256"] = digest
        entry["files"] = n
        skills[skill.name] = entry
    data = {
        "version": 1,
        "digest": "sha256 over LC_ALL=C-sorted '<relpath>\\t<sha256(file)>\\n' lines per skill dir; "
        "see verify_skills_lock.py",
        "skills": skills,
    }
    lock_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[skills-lock] wrote {lock_path}: {len(skills)} skill(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    here = pathlib.Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--report", action="store_true")
    mode.add_argument("--update", action="store_true")
    ap.add_argument("--root", type=pathlib.Path, default=here, help="directory holding the skill dirs (default: this script's directory)")
    ap.add_argument("--lock", type=pathlib.Path, default=None, help=f"lock path (default: <root>/{LOCK_NAME})")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        sys.exit(f"[skills-lock] --root is not a directory: {root} (exit 2)")
    lock_path = (args.lock or root / LOCK_NAME).resolve()
    if args.report:
        return report(root, lock_path)
    if args.update:
        return update(root, lock_path)
    return check(root, lock_path)


if __name__ == "__main__":
    sys.exit(main())
