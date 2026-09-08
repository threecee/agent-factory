#!/usr/bin/env python3
"""Classify the latest red default-branch CI run without rerunning CI or pushing."""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import Any

sys.dont_write_bytecode = True

CLASSES = ("cancelled", "null-job", "known-flake", "real", "environment")
ENVIRONMENT = re.compile(
    r"(?i)\b(runner (?:lost|offline|unavailable)|network (?:error|failure|connection)|connection (?:reset|refused)|disk full|no space|rate limit(?:ed)?|timed? out|service unavailable|infrastructure (?:error|failure))\b"
)
TEST_ID = re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_./-]+\.(?:py|js|jsx|ts|tsx|go|rs)::[A-Za-z0-9_./:\[\]-]+)")


@dataclasses.dataclass
class Completed:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str]], Completed]


def subprocess_runner(argv: Sequence[str]) -> Completed:
    result = subprocess.run(argv, text=True, capture_output=True, check=False)
    return Completed(result.returncode, result.stdout, result.stderr)


class GitHub:
    """Small injectable boundary; tests pass a fake runner or a fake executable."""

    def __init__(self, executable: str = "gh", runner: Runner = subprocess_runner):
        self.executable = executable
        self.runner = runner

    def text(self, *args: str) -> str:
        result = self.runner([self.executable, *args])
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
            raise RuntimeError(f"gh {' '.join(args)}: {detail}")
        return result.stdout

    def json(self, *args: str) -> Any:
        text = self.text(*args)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"gh {' '.join(args)} returned invalid JSON: {exc}") from exc


def patterns(path: pathlib.Path | None) -> list[tuple[str, re.Pattern[str]]]:
    if path is None:
        return []
    result: list[tuple[str, re.Pattern[str]]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        expression = raw.strip()
        if not expression or expression.startswith("#"):
            continue
        try:
            result.append((expression, re.compile(expression)))
        except re.error as exc:
            raise SystemExit(f"ci_triage: invalid regex at {path}:{number}: {exc}") from exc
    return result


def failed_jobs(payload: Any) -> list[dict[str, Any]]:
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    return [job for job in jobs if isinstance(job, dict) and job.get("conclusion") not in ("success", "skipped", "neutral")]


def classify(job: dict[str, Any], log: str, flakes: list[tuple[str, re.Pattern[str]]]) -> tuple[str, str]:
    if job.get("conclusion") == "cancelled":
        return "cancelled", "job conclusion is cancelled"
    if not job.get("startedAt") or not job.get("completedAt") or not job.get("steps"):
        return "null-job", "job has no complete execution record"
    evidence = f"{job.get('name', '')}\n{log}"
    for label, expression in flakes:
        if expression.search(evidence):
            return "known-flake", label
    if ENVIRONMENT.search(evidence):
        return "environment", "environment signature in failed log"
    return "real", "no cancellation, null-job, known-flake, or environment signature"


def test_ids(log: str) -> list[str]:
    return sorted(set(TEST_ID.findall(log)))


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "job"


def write_delta(directory: pathlib.Path, run: dict[str, Any], job: dict[str, Any], ids: list[str], reproduction: int) -> pathlib.Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"ci-{run['databaseId']}-{safe_name(str(job.get('name', 'job')))}.md"
    tests = "\n".join(f"- `{item}`" for item in ids) or "- No stable test ID was extracted; owner must supply one."
    text = f"""# CI fix-lane delta

This delta uses the task shape from `planning/lane-brief-template.md §3`.

## 1. Lane header

- Source run: {run.get('url') or run['databaseId']}
- Workflow: {run.get('name', 'unknown')}
- Head: {run.get('headSha', 'unknown')}
- Failed job: {job.get('name', 'unknown')}

## 2. Measurement baseline

- Local reproduction exit: {reproduction}
- Failed test IDs:
{tests}

## 3. Task

Fix only the real failure represented by the test IDs above. Preserve the original criterion, rerun the same IDs after the change, and attach red-to-green evidence.
"""
    path.write_text(text, encoding="utf-8")
    return path


def local_run(argv: list[str]) -> int:
    return subprocess.run(argv, stdin=subprocess.DEVNULL, check=False).returncode


def triage(args: argparse.Namespace, *, gh_runner: Runner = subprocess_runner) -> dict[str, Any]:
    gh = GitHub(args.gh, gh_runner)
    runs = gh.json(
        "run", "list", "--workflow", args.workflow, "--branch", args.branch,
        "--status", "failure", "--limit", "2",
        "--json", "databaseId,conclusion,createdAt,headSha,url,name",
    )
    if not isinstance(runs, list) or not runs:
        raise RuntimeError(f"no red runs found for workflow {args.workflow!r} on branch {args.branch!r}")
    latest = runs[0]
    previous = runs[1] if len(runs) > 1 else None
    current_jobs = failed_jobs(gh.json("run", "view", str(latest["databaseId"]), "--json", "jobs"))
    previous_jobs = failed_jobs(gh.json("run", "view", str(previous["databaseId"]), "--json", "jobs")) if previous else []
    old_names = {str(job.get("name", "")) for job in previous_jobs}
    new_names = {str(job.get("name", "")) for job in current_jobs}
    diff = {
        "added": sorted(new_names - old_names),
        "persisting": sorted(new_names & old_names),
        "resolved": sorted(old_names - new_names),
    }

    flakes = patterns(args.known_flakes)
    classified: list[dict[str, Any]] = []
    real: list[tuple[dict[str, Any], list[str]]] = []
    rerun = f"gh run rerun {latest['databaseId']} --failed"
    for job in current_jobs:
        job_id = str(job.get("databaseId", ""))
        log = gh.text("run", "view", str(latest["databaseId"]), "--job", job_id, "--log") if job_id else ""
        kind, evidence = classify(job, log, flakes)
        ids = test_ids(log) if kind == "real" else []
        if kind == "real":
            real.append((job, ids))
            action = "write-fix-lane-delta"
        elif kind == "known-flake":
            action = f"cite-known-flake:{evidence}"
        elif kind == "cancelled":
            action = f"print-rerun:{rerun}"
        else:
            action = "escalate-owner"
        classified.append({"name": job.get("name"), "class": kind, "evidence": evidence, "test_ids": ids, "action": action})

    deltas: list[str] = []
    if real:
        idle = local_run([args.idle_check])
        if idle != 0:
            raise RuntimeError(f"idle precondition refused local reproduction (exit {idle})")
        for job, ids in real:
            if not ids:
                for item in classified:
                    if item["name"] == job.get("name"):
                        item["action"] = "escalate-owner:no-test-id"
                continue
            reproduction = local_run([args.test_command, *ids])
            delta = write_delta(args.delta_dir, latest, job, ids, reproduction)
            deltas.append(str(delta))

    return {
        "workflow": args.workflow,
        "branch": args.branch,
        "run": latest,
        "previous_run": previous,
        "failed_set_diff": diff,
        "jobs": classified,
        "rerun_command": rerun,
        "deltas": deltas,
        "safety": "CI was not rerun and no push was performed",
    }


def render(data: dict[str, Any]) -> str:
    lines = [
        f"CI triage: {data['workflow']} on {data['branch']} (run {data['run']['databaseId']})",
        f"FAILED added={','.join(data['failed_set_diff']['added']) or '-'} persisting={','.join(data['failed_set_diff']['persisting']) or '-'} resolved={','.join(data['failed_set_diff']['resolved']) or '-'}",
    ]
    for job in data["jobs"]:
        lines.append(f"{job['name']}: {job['class']} -> {job['action']}")
    lines.append(f"rerun command (printed only): {data['rerun_command']}")
    lines.append(data["safety"])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gh", default="gh", help="gh executable (inject a fake in tests)")
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--known-flakes", type=pathlib.Path)
    parser.add_argument("--idle-check", required=True, help="local executable that enforces the idle precondition")
    parser.add_argument("--test-command", required=True, help="local test executable; real test IDs are appended")
    parser.add_argument("--delta-dir", required=True, type=pathlib.Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = triage(args)
    except (OSError, RuntimeError) as exc:
        print(f"ci_triage: {exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(render(data), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
