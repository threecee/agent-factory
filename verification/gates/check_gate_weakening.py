"""Never-weaken check over a train range (verify-portfolio.md, "Legs that bring lane-green
closer to train-green"; mechanism M-17d).

Over ``<base>..<head>`` (default: the merge-base with ``origin/<default>`` to ``HEAD``) three
legs read the diff and report:

1. a baseline file (``--baseline-glob``, default ``*baseline.json``) whose tolerated volume
   grew — more list entries, higher counts — without a commit in the range that touches the
   file and says ``--update`` (the only path to a new baseline);
2. a gate script (``--gate-glob``, default ``scripts/check_*.py``) changed without a paired
   changed test file under ``--tests-dir`` (default ``tests``) whose content names it
   (falsification.md rule 1: red before green, for a gate too);
3. a net loss of ``assert`` lines under the tests dir — a rewrite keeps the count, a
   deletion lowers the criterion.

A commit in the range carrying the trailer ``Gate-change: ADR-NNNN`` documents the exception
for every leg and is printed as such. The check starts as WARN (findings printed, exit 0);
``--hard`` makes findings the exit code — the documented flip for the train after the first.
No switch: the fix is the fix, and a legitimate exception is a trailer, not a variable.

    python3 -m scripts.check_gate_weakening [--base <ref>] [--head <ref>] [--hard]
        [--baseline-glob '*baseline.json'] [--gate-glob 'scripts/check_*.py'] [--tests-dir tests]
        [--default-branch main] [--repo-root .]

Planted falsifications the package test runs (verification/tests/test_landing_protections.sh
case 26): a baseline that grew without an ``--update`` commit → finding; a gate changed without
a test naming it → finding; a net assert loss → finding; the ``Gate-change:`` trailer → the
exception printed and no finding; WARN → exit 0; ``--hard`` → exit 1.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import pathlib
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field

ASSERT_RE = re.compile(r"^[+-]\s*assert\b")
GATE_CHANGE_RE = re.compile(r"^Gate-change:\s*(ADR-\d{4})", re.M)
DEFAULT_BASELINE_GLOB = "*baseline.json"
DEFAULT_GATE_GLOB = "scripts/check_*.py"
DEFAULT_TESTS_DIR = "tests"


@dataclass
class Diff:
    base: str
    head: str
    changed: dict[str, str] = field(default_factory=dict)  # path -> status letter
    messages: dict[str, str] = field(default_factory=dict)  # sha -> message
    touched_by: dict[str, set[str]] = field(default_factory=dict)  # path -> shas


def _git(repo: pathlib.Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    return result.stdout if result.returncode == 0 else ""


def resolve_base(repo: pathlib.Path, base: str | None, head: str, default_branch: str = "main") -> str:
    if base:
        return base
    merge_base = _git(repo, "merge-base", f"origin/{default_branch}", head).strip()
    return merge_base or _git(repo, "merge-base", default_branch, head).strip() or f"{head}~1"


def read_diff(repo: pathlib.Path, base: str, head: str) -> Diff:
    diff = Diff(base, head)
    for line in _git(repo, "diff", "--name-status", "-M", f"{base}..{head}").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            diff.changed[parts[-1]] = parts[0][:1]
    log = _git(repo, "log", "--format=%H%x00%B%x1e", f"{base}..{head}")
    for entry in log.split("\x1e"):
        if "\x00" not in entry:
            continue
        sha, _, message = entry.strip().partition("\x00")
        diff.messages[sha] = message
        for path in _git(repo, "show", "--name-only", "--format=", sha).split():
            diff.touched_by.setdefault(path, set()).add(sha)
    return diff


def tolerance(value: object) -> float:
    """How much a baseline tolerates: numbers add, list entries count one each."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, list):
        return float(len(value))
    if isinstance(value, dict):
        return sum(tolerance(item) for item in value.values())
    return 0.0


def _load(repo: pathlib.Path, ref: str, path: str) -> object | None:
    text = _git(repo, "show", f"{ref}:{path}")
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def gate_change_exceptions(diff: Diff) -> list[str]:
    return sorted({f"{match.group(1)} ({sha[:8]})" for sha, message in diff.messages.items() for match in GATE_CHANGE_RE.finditer(message)})


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(pathlib.PurePosixPath(path).name, pattern)


def baseline_findings(repo: pathlib.Path, diff: Diff, baseline_glob: str) -> list[str]:
    findings: list[str] = []
    for path, status in sorted(diff.changed.items()):
        if not _matches(path, baseline_glob) or status not in {"M", "A"}:
            continue
        old = _load(repo, diff.base, path)
        new = _load(repo, diff.head, path)
        if new is None:
            continue
        before = tolerance(old) if old is not None else 0.0
        after = tolerance(new)
        if after <= before:
            continue
        if any("--update" in diff.messages.get(sha, "") for sha in diff.touched_by.get(path, ())):
            continue
        findings.append(
            f"{path}: the tolerated volume grew {before:g} → {after:g} without an «--update» commit touching the file "
            "(a baseline is regenerated only in the primary on a clean HEAD, through the gate's own --update)"
        )
    return findings


def _test_files_naming(repo: pathlib.Path, head: str, changed_tests: Iterable[str], name: str) -> bool:
    return any(name in _git(repo, "show", f"{head}:{test_path}") for test_path in changed_tests)


def unpaired_gate_findings(repo: pathlib.Path, diff: Diff, gate_glob: str, tests_dir: str) -> list[str]:
    prefix = tests_dir.rstrip("/") + "/"
    changed_tests = [path for path in diff.changed if path.startswith(prefix)]
    findings: list[str] = []
    for path, status in sorted(diff.changed.items()):
        if not _matches(path, gate_glob) or status == "D":
            continue
        name = pathlib.PurePosixPath(path).stem
        if not _test_files_naming(repo, diff.head, changed_tests, name):
            findings.append(
                f"{path} changed without a paired test change (no changed file under {prefix} names {name}; "
                "falsification.md rule 1 asks for red→green proof of every gate change)"
            )
    return findings


def assert_delta(repo: pathlib.Path, diff: Diff, tests_dir: str) -> tuple[int, int, list[str]]:
    added = removed = 0
    files: set[str] = set()
    current = ""
    for line in _git(repo, "diff", "-U0", f"{diff.base}..{diff.head}", "--", tests_dir).splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            continue
        if line.startswith(("+++", "---")) or not ASSERT_RE.match(line):
            continue
        files.add(current)
        if line.startswith("+"):
            added += 1
        else:
            removed += 1
    return added, removed, sorted(files)


def assert_findings(repo: pathlib.Path, diff: Diff, tests_dir: str) -> list[str]:
    added, removed, files = assert_delta(repo, diff, tests_dir)
    if removed <= added:
        return []
    return [
        f"net {removed - added} assert line(s) removed under {tests_dir}/ (+{added}/−{removed}; "
        f"{', '.join(files[:6])}{' …' if len(files) > 6 else ''}) — a rewrite keeps the count, a deletion lowers the criterion"
    ]


def weakening_findings(
    repo: pathlib.Path,
    diff: Diff,
    *,
    baseline_glob: str = DEFAULT_BASELINE_GLOB,
    gate_glob: str = DEFAULT_GATE_GLOB,
    tests_dir: str = DEFAULT_TESTS_DIR,
) -> tuple[list[str], list[str]]:
    """``(findings, documented exceptions)`` — findings are empty when an exception stands."""
    findings = (
        baseline_findings(repo, diff, baseline_glob)
        + unpaired_gate_findings(repo, diff, gate_glob, tests_dir)
        + assert_findings(repo, diff, tests_dir)
    )
    exceptions = gate_change_exceptions(diff)
    return ([] if exceptions else findings), exceptions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--base", default=None)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--hard", action="store_true", help="findings decide the exit code")
    parser.add_argument("--baseline-glob", default=DEFAULT_BASELINE_GLOB)
    parser.add_argument("--gate-glob", default=DEFAULT_GATE_GLOB)
    parser.add_argument("--tests-dir", default=DEFAULT_TESTS_DIR)
    parser.add_argument("--default-branch", default="main")
    args = parser.parse_args(argv)
    base = resolve_base(args.repo_root, args.base, args.head, args.default_branch)
    diff = read_diff(args.repo_root, base, args.head)
    findings, exceptions = weakening_findings(
        args.repo_root, diff, baseline_glob=args.baseline_glob, gate_glob=args.gate_glob, tests_dir=args.tests_dir
    )
    level = "HARD" if args.hard else "WARN"
    for exception in exceptions:
        print(f"[INFO] documented exception Gate-change: {exception}")
    for finding in findings:
        print(f"[{level}] {finding}")
    print(f"gate-weakening ({level}): {len(findings)} finding(s) over {base[:8]}..{args.head} ({len(diff.changed)} changed file(s), {len(diff.messages)} commit(s))")
    return 1 if args.hard and findings else 0


if __name__ == "__main__":
    sys.exit(main())
