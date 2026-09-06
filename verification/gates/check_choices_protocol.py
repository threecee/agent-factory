"""Choices-ledger lint (interpretation/choices-ledger-README.md §1–§4; mechanism M-7).

Reads ``<ledger-dir>/<train>.md`` and checks the ledger's FORM — never its truth:

  * the title (first heading) names the train;
  * one ``## Lane `<name>``` section per boarder — boarders from ``--boarders``, else the
    ``board <lane> (<sha>)`` lines of ``<train>-*.log`` under ``--receipts``, else the lane
    sections the ledger itself carries — and every lane section names its boarded SHA
    (40 hex, in the header or on a ``boarded: <sha>`` line; lander-duties §1 step 2);
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
        [--receipts <dir>] [--warn] [--at-push] [--default-mode pr|direct-push] [--repo-root .]
    python3 -m scripts.check_choices_protocol            # train from $TRAIN_NAME, receipts from $TRAIN_ARTIFACTS

Planted falsifications the package test runs (verification/tests/test_landing_protections.sh
case 23): missing ledger → HARD; an entry line without an ID → HARD naming the line; unsound
without a fix note → HARD; a hedge phrase → HARD; ``--at-push`` without ``## Landing`` → HARD;
the complete ledger → OK; ``--warn`` → findings printed, exit 0.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

TRAIN_ENV = "TRAIN_NAME"
ARTIFACTS_ENV = "TRAIN_ARTIFACTS"
DEFAULT_LEDGER_DIR = "docs/choices"
LANDING_HEADER = "## Landing"
MODES = ("pr", "direct-push")

SECTION_RE = re.compile(r"^## ", re.M)
LANE_HEADER_RE = re.compile(r"^## Lane `(?P<lane>[^`]+)`")
SHA_RE = re.compile(r"\b[0-9a-f]{40}\b")
BOARDED_LINE_RE = re.compile(r"^\s*boarded:\s*`?([0-9a-f]{40})`?", re.M | re.I)
BOARD_LOG_RE = re.compile(r"\bboard (?P<lane>[A-Za-z0-9._-]+) \((?P<sha>[0-9a-f]{40})\)")
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


def boarders_from_logs(receipts: pathlib.Path, train: str) -> dict[str, str]:
    """``lane -> SHA`` from every ``board <lane> (<sha>)`` line in ``<train>-*.log``."""
    boarders: dict[str, str] = {}
    for log in sorted(receipts.glob(f"{train}-*.log"), key=lambda path: path.stat().st_mtime):
        try:
            text = log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in BOARD_LOG_RE.finditer(text):
            boarders[match.group("lane")] = match.group("sha")
    return boarders


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
    for key in ("receipts:", "local-verify:"):
        if not re.search(rf"^\s*{re.escape(key)}\s*\S", landing, re.M | re.I):
            findings.append(f"«## Landing» lacks a «{key} …» line")
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


def _boarders(listed: str, receipts: pathlib.Path | None, train: str) -> list[str]:
    boarders = [name for name in listed.split(",") if name]
    if receipts is not None and receipts.is_dir():
        boarders += [lane for lane in boarders_from_logs(receipts, train) if lane not in boarders]
    return boarders


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("train", nargs="?", default=None, help=f"default: ${TRAIN_ENV}")
    parser.add_argument("--repo-root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--ledger-dir", default=DEFAULT_LEDGER_DIR)
    parser.add_argument("--boarders", default="")
    parser.add_argument("--receipts", type=pathlib.Path, default=None, help=f"default: ${ARTIFACTS_ENV}")
    parser.add_argument("--warn", action="store_true", help="print findings, exit 0")
    parser.add_argument("--at-push", action="store_true", help="also require the «## Landing» section")
    parser.add_argument("--default-mode", choices=MODES, default="pr")
    args = parser.parse_args(argv)
    train = args.train or os.environ.get(TRAIN_ENV)
    receipts = args.receipts or (pathlib.Path(os.environ[ARTIFACTS_ENV]) if os.environ.get(ARTIFACTS_ENV) else None)
    if not train:
        print(f"[HARD] train name missing: give <train> or set {TRAIN_ENV} (the assembler exports it)")
        return 1
    path = ledger_path(args.repo_root, train, args.ledger_dir)
    if not path.is_file():
        print(f"[HARD] ledger missing: {path}")
        return 0 if args.warn else 1
    boarders = _boarders(args.boarders, receipts, train)
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
