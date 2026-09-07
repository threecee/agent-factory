"""Choices-ledger lint (interpretation/choices-ledger-README.md §1–§4; mechanism M-7).

Reads ``<ledger-dir>/<train>.md`` and checks the ledger's FORM — never its truth:

  * the title (first heading) names the train;
  * one ``## Lane `<name>``` section per boarder — boarders from ``--boarders``, plus the
    train's own merge commits since ``--base`` (the newest receipt's ``BASE=`` under
    ``--receipts``, else the merge-base with ``origin/<default>``) whose subject reads
    ``board <lane> (<sha>)`` (harness/train-plan.md §2 row 2), else the lane sections the
    ledger itself carries — and every lane section names its boarded SHA (40 hex, in the
    header or on a ``boarded: <sha>`` line; lander-duties §1 step 2);
  * every entry line carries a stable ID (``**<lane>-<n>**`` / ``**O-<n>**``, optionally
    ``<train>/``-prefixed, or ``id: <id>``), a verdict word (sound | unsound | needs-user) and
    a confidence (H | M | L, or high | medium | low); a lane section with no entry says
    ``no choices`` (the mechanical-lane line of README §1);
  * no ``unsound`` without a fix note (fixed | fix commit | reverted | corrected) in the same
    section; a negated mention («no unsound») is not an unsound entry;
  * no hedge phrase standing in for evidence (one English list, shared with the report lint);
  * a single-boarder train carries the blocker line ``single-lane train — priority …``
    (lander-duties §2 rule 4);
  * with ``--at-push``, a ``## Landing`` section with ``landing mode: pr|direct-push``,
    ``receipts: <dir>`` and ``local-verify: posted|skipped <reason>`` lines, plus ``pr: <n>``
    in pr mode and ``override reason: …`` when direct-push overrides a pr default
    (``--default-mode``, default pr; landing-modes.md §1).

Findings print as ``[HARD] …`` and exit 1; ``--warn`` prints ``[WARN] …`` and exits 0 (the first
train's form); a missing ledger is HARD (exit 0 under ``--warn``). The fix is always to
finish the ledger, never to switch the lint off. The landing guard runs this lint at every
landing under its own switch ``protocol`` (verification/protections.md §5); the assembler
runs it as a WARN cheap gate on the train tree with ``TRAIN_NAME`` and ``TRAIN_ARTIFACTS``
exported (harness/train-plan.md §2 row 6).

    python3 -m scripts.check_choices_protocol <train> [--ledger-dir docs/choices] [--boarders a,b]
        [--receipts <dir>] [--base <sha>] [--default-branch main] [--warn] [--at-push]
        [--default-mode pr|direct-push] [--repo-root .]
    python3 -m scripts.check_choices_protocol            # train from $TRAIN_NAME, receipts from $TRAIN_ARTIFACTS

Python API the landing guard consumes in-process (``harness/guards/rules/landing.py``, located
as ``harness/guards/rules/_gates.py`` says), beside the documented invocation form:
``boarders_from_merges(repo_root, base, head, run=…)`` — the ONE derivation of the boarders a
train carries, shared by the guard and this gate; ``boarders_from_text(text)``;
``unsound_without_fix(text)``; ``protocol_findings(text, boarders, train=, at_push=,
default_mode=)``. Their signatures are part of the contract (gates/README.md).

Planted falsifications the package test runs (verification/tests/test_landing_protections.sh
case 23): missing ledger → HARD; an entry line without an ID → HARD naming the line; unsound
without a fix note → HARD; a hedge phrase → HARD; ``--at-push`` without ``## Landing`` → HARD;
the complete ledger → OK; ``--warn`` → findings printed, exit 0; a boarder read from the
train's merge commit whose lane section is missing → HARD naming the section.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
from collections.abc import Callable

TRAIN_ENV = "TRAIN_NAME"
ARTIFACTS_ENV = "TRAIN_ARTIFACTS"
DEFAULT_BRANCH_VAR = "FACTORY_GUARD_DEFAULT_BRANCH"
DEFAULT_LEDGER_DIR = "docs/choices"
LANDING_HEADER = "## Landing"
MODES = ("pr", "direct-push")
Runner = Callable[..., subprocess.CompletedProcess[str]]

SECTION_RE = re.compile(r"^## ", re.M)
LANE_HEADER_RE = re.compile(r"^## Lane `(?P<lane>[^`]+)`")
SHA_RE = re.compile(r"\b[0-9a-f]{40}\b")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BOARDED_LINE_RE = re.compile(r"^\s*boarded:\s*`?([0-9a-f]{40})`?", re.M | re.I)
BOARD_SUBJECT_RE = re.compile(r"\bboard (?P<lane>[A-Za-z0-9._-]+) \((?P<sha>[0-9a-f]{40})\)")
ENTRY_ID_RE = re.compile(
    r"(?:\*\*|`|\bid:\s*)(?:[A-Za-z0-9._-]+/)?(?P<id>[a-z][a-z0-9]*(?:-[a-z0-9]+)*-\d+|O-\d+)\b"
)
ENTRY_LINE_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*|`|\{?\s*id:|>\s*\*\*)")
VERDICT_RE = re.compile(r"\b(sound|unsound|needs-user)\b", re.I)
CONFIDENCE_RE = re.compile(r"\bconfidence\b\s*[:=]?\s*(?:high|medium|low|H|M|L)\b|[,(]\s*(?:H|M|L)\s*[);]", re.I)
UNSOUND_RE = re.compile(r"\bunsound\b", re.I)
NEGATED_UNSOUND_RE = re.compile(r"\b(?:no|zero|0|without|never)\b[^.\n]{0,24}\bunsound\b|\bunsound\s*\(0\)", re.I)
FIXED_RE = re.compile(r"\b(fixed|fix commit|reverted|corrected)\b", re.I)
NO_CHOICES_RE = re.compile(r"\bno choices\b", re.I)
BLOCKER_RE = re.compile(r"single-lane train\s*[—–-]+\s*priority", re.I)
HEDGES: tuple[str, ...] = (
    "should work now",
    "should pass now",
    "should be fine",
    "looks correct",
    "looks right",
    "probably passes",
    "seems fine",
    "seems to work",
)


def ledger_path(repo_root: pathlib.Path, train: str, ledger_dir: str = DEFAULT_LEDGER_DIR) -> pathlib.Path:
    return repo_root / ledger_dir / f"{train}.md"


def sections(text: str) -> list[tuple[str, str]]:
    """``(header line, body)`` for every ``## `` section; the preamble has header ``""``."""
    parts = SECTION_RE.split(text)
    result: list[tuple[str, str]] = [("", parts[0])]
    for part in parts[1:]:
        header, _, body = part.partition("\n")
        result.append(("## " + header.strip(), body))
    return result


def lane_sections(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for header, body in sections(text):
        match = LANE_HEADER_RE.match(header)
        if match:
            found[match.group("lane")] = header + "\n" + body
    return found


def boarders_from_text(text: str) -> dict[str, str]:
    """``lane -> boarded SHA`` for every lane section that names one (header or ``boarded:``)."""
    boarders: dict[str, str] = {}
    for lane, section in lane_sections(text).items():
        header = section.splitlines()[0]
        match = SHA_RE.search(header) or BOARDED_LINE_RE.search(section)
        if match:
            boarders[lane] = match.group(1) if match.re is BOARDED_LINE_RE else match.group(0)
    return boarders


def _git(run: Runner, cwd: pathlib.Path, *args: str, timeout: float = 30.0) -> tuple[int, str]:
    try:
        result = run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as error:
        return 127, str(error)
    return result.returncode, (result.stdout or "").strip()


def boarders_from_merges(repo_root: pathlib.Path, base: str | None, head: str = "HEAD", *, run: Runner = subprocess.run) -> dict[str, str]:
    """``lane -> second parent`` for every merge commit in ``base..head`` whose subject reads
    ``… board <lane> (<sha>)`` (harness/train-plan.md §2 row 2) — the boarders the train
    actually carries, read from git and independent of what the ledger says. The landing
    guard calls this same function, so the guard and the gate share one derivation. Empty
    without a base, outside git, or when git fails (the caller falls back to the sections)."""
    named: dict[str, str] = {}
    if not base:
        return named
    code, listing = _git(run, repo_root, "log", "--merges", "--format=%H%x09%s", f"{base}..{head}")
    if code != 0:
        return named
    for line in listing.splitlines():
        sha, _, subject = line.partition("\t")
        match = BOARD_SUBJECT_RE.search(subject)
        if not match:
            continue
        code, parent = _git(run, repo_root, "rev-parse", f"{sha}^2")
        if code == 0 and parent:
            named[match.group("lane")] = parent
    return named


def receipt_base(receipts: pathlib.Path | None, train: str) -> str | None:
    """``BASE=`` of the newest ``<train>-*.exit`` receipt under ``receipts`` (train-plan §4)."""
    if receipts is None or not receipts.is_dir():
        return None
    for path in sorted(receipts.glob(f"{train}-*.exit"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if line.startswith("BASE="):
                value = line[5:].strip()
                return value if FULL_SHA_RE.match(value) else None
    return None


def merge_base(repo_root: pathlib.Path, default_branch: str, *, run: Runner = subprocess.run) -> str | None:
    code, sha = _git(run, repo_root, "merge-base", f"origin/{default_branch}", "HEAD")
    return sha if code == 0 and sha else None


def entry_lines(section: str) -> list[str]:
    return [line for line in section.splitlines()[1:] if ENTRY_LINE_RE.match(line)]


def unsound_without_fix(text: str) -> list[str]:
    findings: list[str] = []
    for header, body in sections(text):
        section = header + "\n" + body
        lines = [line for line in section.splitlines() if UNSOUND_RE.search(line) and not NEGATED_UNSOUND_RE.search(line)]
        if lines and not FIXED_RE.search(section):
            findings.append(f"unsound without a fix note in «{header or 'the preamble'}»: {lines[0].strip()[:80]}")
    return findings


def title_findings(text: str, train: str | None) -> list[str]:
    first = next((line for line in text.splitlines() if line.strip()), "")
    if not first.startswith("#"):
        return [f"the first line must be a heading that names the train, found: {first[:60]!r}"]
    if train and not re.search(rf"(?<![A-Za-z0-9_-]){re.escape(train)}(?![A-Za-z0-9_-])", first):
        return [f"the title does not name train {train}: {first[:60]!r}"]
    return []


def _entry_findings(lane: str, section: str) -> list[str]:
    findings: list[str] = []
    entries = entry_lines(section)
    if not entries:
        if not NO_CHOICES_RE.search(section):
            findings.append(f"section for {lane} has no entry line with a stable ID and does not say «no choices»")
        return findings
    for line in entries:
        shown = line.strip()[:70]
        if not ENTRY_ID_RE.search(line):
            findings.append(f"entry without a stable ID (<lane>-<n> or O-<n>) in section {lane}: {shown}")
            continue
        if not VERDICT_RE.search(line):
            findings.append(f"entry without a verdict (sound/unsound/needs-user) in section {lane}: {shown}")
        if not CONFIDENCE_RE.search(line):
            findings.append(f"entry without a confidence (H/M/L) in section {lane}: {shown}")
    return findings


def _lane_findings(lanes: dict[str, str], boarders: list[str]) -> list[str]:
    findings = [f"missing section «## Lane `{boarder}`» for boarder {boarder}" for boarder in boarders if boarder not in lanes]
    named = boarders_from_text("\n".join(lanes.values()))
    for lane, section in lanes.items():
        if lane not in named:
            findings.append(f"section for {lane} names no boarded SHA (40 hex in the header or a boarded: line)")
        findings += _entry_findings(lane, section)
    return findings


def _landing_findings(text: str, default_mode: str) -> list[str]:
    landing = next((body for header, body in sections(text) if header == LANDING_HEADER), None)
    if landing is None:
        return [f"missing section «{LANDING_HEADER}» (landing mode:, receipts:, local-verify:)"]
    findings: list[str] = []
    lowered = landing.lower()
    mode_match = re.search(r"^\s*landing mode:\s*(\S+)", landing, re.M | re.I)
    mode = mode_match.group(1).lower() if mode_match else None
    if mode not in MODES:
        findings.append("«## Landing» lacks a «landing mode: pr|direct-push» line")
    if not re.search(r"^\s*receipts:\s*\S", landing, re.M | re.I):
        findings.append("«## Landing» lacks a «receipts: …» line")
    if not re.search(r"^\s*local-verify:\s*(?:posted\s*$|skipped\s+\S.*$)", landing, re.M | re.I):
        findings.append("«## Landing» lacks a valid «local-verify: posted|skipped <reason>» line")
    if mode == "pr" and not re.search(r"^\s*pr:\s*\d+", landing, re.M | re.I):
        findings.append("«## Landing» in pr mode lacks a «pr: <number>» line")
    if mode == "direct-push" and default_mode == "pr" and "override reason:" not in lowered:
        findings.append("«## Landing» uses direct-push against a pr default without an «override reason:» line")
    return findings


def _text_findings(text: str, boarders: list[str]) -> list[str]:
    lowered = text.lower()
    findings = [f"hedge phrase in the ledger: «{hedge}»" for hedge in HEDGES if hedge in lowered]
    if len(boarders) == 1 and not BLOCKER_RE.search(text):
        findings.append("single-boarder train without the blocker line «single-lane train — priority …» (lander-duties §2)")
    return findings


def protocol_findings(
    text: str,
    boarders: list[str],
    *,
    train: str | None = None,
    at_push: bool = False,
    default_mode: str = "pr",
) -> list[str]:
    """Every schema finding for the ledger text."""
    lanes = lane_sections(text)
    effective = list(boarders) or list(lanes)
    findings = title_findings(text, train) + _lane_findings(lanes, effective) + unsound_without_fix(text) + _text_findings(text, effective)
    if at_push:
        findings += _landing_findings(text, default_mode)
    return findings


def _boarders(listed: str, repo_root: pathlib.Path, base: str | None) -> list[str]:
    """``--boarders`` plus the train's merged boarders since ``base`` (one derivation, above)."""
    boarders = [name for name in listed.split(",") if name]
    boarders += [lane for lane in boarders_from_merges(repo_root, base) if lane not in boarders]
    return boarders


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("train", nargs="?", default=None, help=f"default: ${TRAIN_ENV}")
    parser.add_argument("--repo-root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--ledger-dir", default=DEFAULT_LEDGER_DIR)
    parser.add_argument("--boarders", default="")
    parser.add_argument("--receipts", type=pathlib.Path, default=None, help=f"default: ${ARTIFACTS_ENV}")
    parser.add_argument("--base", default=None, help="default: the newest receipt's BASE=, else the merge-base with origin/<default>")
    parser.add_argument("--default-branch", default=None, help=f"default: ${DEFAULT_BRANCH_VAR}, else main")
    parser.add_argument("--warn", action="store_true", help="print findings, exit 0")
    parser.add_argument("--at-push", action="store_true", help="also require the «## Landing» section")
    parser.add_argument("--default-mode", choices=MODES, default="pr")
    args = parser.parse_args(argv)
    train = args.train or os.environ.get(TRAIN_ENV)
    receipts = args.receipts or (pathlib.Path(os.environ[ARTIFACTS_ENV]) if os.environ.get(ARTIFACTS_ENV) else None)
    branch = args.default_branch or os.environ.get(DEFAULT_BRANCH_VAR) or "main"
    if not train:
        print(f"[HARD] train name missing: give <train> or set {TRAIN_ENV} (the assembler exports it)")
        return 1
    path = ledger_path(args.repo_root, train, args.ledger_dir)
    if not path.is_file():
        print(f"[HARD] ledger missing: {path}")
        return 0 if args.warn else 1
    base = args.base or receipt_base(receipts, train) or merge_base(args.repo_root, branch)
    boarders = _boarders(args.boarders, args.repo_root, base)
    findings = protocol_findings(
        path.read_text(encoding="utf-8"), boarders, train=train, at_push=args.at_push, default_mode=args.default_mode
    )
    level = "WARN" if args.warn else "HARD"
    for finding in findings:
        print(f"[{level}] {finding}")
    print(f"ledger {path.name}: {len(findings)} finding(s), {len(boarders) or len(lane_sections(path.read_text(encoding='utf-8')))} boarder(s)")
    return 0 if args.warn or not findings else 1


if __name__ == "__main__":
    sys.exit(main())
