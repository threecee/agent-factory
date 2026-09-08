#!/usr/bin/env python3
"""Check compact skill entrypoints against their pre-split origin/main body."""

from __future__ import annotations

import argparse
from collections import Counter
import pathlib
import subprocess
import sys


TARGETS = (
    "test-driven-development",
    "write-spec",
    "implement-spec",
    "code-review",
    "audit-choices",
    "systematic-debugging",
    "brainstorming",
    "refactor-clean",
    "independent-lane-review",
    "finishing-a-development-branch",
)


def split_frontmatter(text: str, source: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{source}: missing opening frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"{source}: missing closing frontmatter delimiter") from exc
    return lines[1:end], lines[end + 1 :]


def description(frontmatter: list[str], source: str) -> str:
    rows = [line for line in frontmatter if line.startswith("description:")]
    if len(rows) != 1:
        raise ValueError(f"{source}: expected exactly one single-line description")
    value = rows[0].split(":", 1)[1].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def normalized(lines: list[str]) -> Counter[str]:
    return Counter(value for line in lines if (value := " ".join(line.split())))


def baseline(repo: pathlib.Path, skill: str) -> str:
    proc = subprocess.run(
        ["git", "show", f"origin/main:skills/{skill}/SKILL.md"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode:
        raise ValueError(f"{skill}: cannot read origin/main baseline: {proc.stderr.strip()}")
    return proc.stdout


def check(root: pathlib.Path, repo: pathlib.Path) -> int:
    problems: list[str] = []
    summaries: list[str] = []
    for skill in TARGETS:
        skill_file = root / skill / "SKILL.md"
        try:
            current_text = skill_file.read_text(encoding="utf-8")
            current_frontmatter, current_body = split_frontmatter(current_text, str(skill_file))
            baseline_text = baseline(repo, skill)
            _, baseline_body = split_frontmatter(baseline_text, f"origin/main:{skill}")
            desc = description(current_frontmatter, str(skill_file))
        except (OSError, ValueError) as exc:
            problems.append(str(exc))
            continue

        skill_lines = len(current_text.splitlines())
        if skill_lines > 120:
            problems.append(f"{skill}: SKILL.md has {skill_lines} lines; maximum is 120")
        if len(desc) > 300:
            problems.append(f"{skill}: description has {len(desc)} characters; maximum is 300")

        references_dir = root / skill / "references"
        references = sorted(references_dir.glob("*.md")) if references_dir.is_dir() else []
        for reference in references:
            link = reference.relative_to(root / skill).as_posix()
            if link not in current_text:
                problems.append(f"{skill}: {link} is not referenced from SKILL.md")

        combined = list(current_body)
        for reference in references:
            combined.extend(reference.read_text(encoding="utf-8").splitlines())
        missing = normalized(baseline_body) - normalized(combined)
        if missing:
            sample, count = next(iter(missing.items()))
            problems.append(
                f"{skill}: {sum(missing.values())} baseline line occurrence(s) missing; "
                f"first is {sample!r} ({count} occurrence(s))"
            )
        summaries.append(
            f"{skill}: source_lines={len(baseline_text.splitlines())} "
            f"skill_lines={skill_lines} description_chars={len(desc)} "
            f"references={len(references)} preserved_lines={sum(normalized(baseline_body).values())}"
        )

    if problems:
        print(f"[skill-shape] HARD: {len(problems)} problem(s)")
        for problem in problems:
            print(f"  {problem}")
        return 1
    for summary in summaries:
        print(f"[skill-shape] {summary}")
    print(f"[skill-shape] verified: {len(TARGETS)} compact skill(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    here = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=here)
    args = parser.parse_args(argv)
    return check(args.root.resolve(), here.parent)


if __name__ == "__main__":
    sys.exit(main())
