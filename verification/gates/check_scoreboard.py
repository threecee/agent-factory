"""Scoreboard substrate validator (design-note §7 Stage 0).

The synthetic-corpus programme records every measured number as a *scoreboard
record*, never as a scalar an implementer could quietly move (§2.4, D2). This
script is the Stage-0 substrate for that: it validates the SHAPE of
``corpus/scoreboard.json`` so that when the ``channel_swarm`` corpus finally
lands, the corpus-scored rows (NET-01 L1/L2/L3, §10.3) have a well-formed,
honest place to land into.

What it enforces, and why each rule exists:

* ``records`` is the results ledger. At Stage 0 it is EMPTY by construction —
  no corpus is read, so no number is a capability claim (ADR-0094). Every
  record that DOES appear must carry the ``record_contract.required_fields``.
  ``binding_hash`` + ``ingest_revision`` are mandatory because two records with
  the same ``corpus_release`` otherwise silently refer to different
  message-to-label maps as the adapters change (§2.4). ``transfer_verdict`` is
  mandatory because a cited number without its source-transfer token reads as a
  capability claim it has not earned (§10.8).
* ``permanent`` must retain ``forensic_realism = unobserved_by_construction``.
  That row does not clear: nobody reads the corpus in phase one, so its realism
  is unobserved by construction (ADR-0094 / §9 B2).
* ``deferred_rows`` declares the corpus-scored rows that cannot exist yet. Each
  is ``report_only`` and carries a null ``value`` (deferred, not measured). A
  NET-01 group must keep all three layers (L1/L2/L3) present together: no single
  number is a verdict, so a partial group is a shape error (§10.3).

It is Stage-0 report-only substrate and is deliberately NOT wired into
``make verify`` (that flip needs the corpus and is a later, funded step). Run it
by hand:

    python -m scripts.check_scoreboard            # validate shape (exit 1 if malformed)
    python -m scripts.check_scoreboard --report   # same report, always exit 0

Refs: ADR-0093, ADR-0094, design-note §2.4, §7, §10.3.
"""

from __future__ import annotations

import json
import pathlib
import sys

SCOREBOARD_PATH = pathlib.Path("corpus/scoreboard.json")

# Any scored record must carry these (§2.4). Kept in sync with the JSON's own
# record_contract, which this script also validates.
REQUIRED_RECORD_FIELDS = (
    "metric_id",
    "corpus_release",
    "binding_hash",
    "ingest_revision",
    "value",
    "mode",
    "transfer_verdict",
)
VALID_MODES = ("report_only", "gate")
# The forensic-realism row that must never leave the board (ADR-0094).
PERMANENT_FORENSIC = ("forensic_realism", "unobserved_by_construction")


def load(repo_root: pathlib.Path) -> dict:
    return json.loads((repo_root / SCOREBOARD_PATH).read_text(encoding="utf-8"))


def validate(board: dict) -> list[str]:
    """Structural violations as printable lines. Empty list == well-formed."""
    return [
        *_validate_header(board),
        *_validate_records(board.get("records")),
        *_validate_permanent(board.get("permanent")),
        *_validate_deferred(board.get("deferred_rows")),
    ]


def _validate_header(board: dict) -> list[str]:
    problems: list[str] = []
    if board.get("schema") != "kripos-scoreboard/v1":
        problems.append(
            f"[HARD] schema must be 'kripos-scoreboard/v1', got {board.get('schema')!r}"
        )
    contract = board.get("record_contract")
    if not isinstance(contract, dict):
        problems.append("[HARD] record_contract missing or not an object")
    elif list(contract.get("required_fields") or ()) != list(REQUIRED_RECORD_FIELDS):
        problems.append(
            "[HARD] record_contract.required_fields drifted from the §2.4 contract "
            f"{list(REQUIRED_RECORD_FIELDS)} (got {contract.get('required_fields')})"
        )
    return problems


def _validate_records(records: object) -> list[str]:
    if not isinstance(records, list):
        return ["[HARD] records must be a list"]
    problems: list[str] = []
    for i, rec in enumerate(records):
        missing = [f for f in REQUIRED_RECORD_FIELDS if f not in rec]
        if missing:
            problems.append(
                f"[HARD] records[{i}] ({rec.get('metric_id', '?')}) missing "
                f"required field(s): {', '.join(missing)}"
            )
        if rec.get("mode") not in VALID_MODES:
            problems.append(f"[HARD] records[{i}] mode {rec.get('mode')!r} not in {VALID_MODES}")
    return problems


def _validate_permanent(permanent: object) -> list[str]:
    if not isinstance(permanent, list):
        return ["[HARD] permanent must be a list"]
    metric, value = PERMANENT_FORENSIC
    has_forensic = any(
        row.get("metric_id") == metric and row.get("value") == value
        for row in permanent
        if isinstance(row, dict)
    )
    if not has_forensic:
        return [
            f"[HARD] permanent must retain {metric} = {value} (ADR-0094 / §9 B2); "
            "that row does not clear"
        ]
    return []


def _validate_deferred(deferred: object) -> list[str]:
    if not isinstance(deferred, list):
        return ["[HARD] deferred_rows must be a list"]
    problems: list[str] = []
    for group in deferred:
        problems.extend(_validate_deferred_group(group))
    return problems


def _validate_deferred_group(group: object) -> list[str]:
    if not isinstance(group, dict):
        return ["[HARD] deferred group is not an object"]
    name = group.get("group", "?")
    rows = group.get("rows")
    if not isinstance(rows, list) or not rows:
        return [f"[HARD] deferred group {name!r} has no rows"]
    problems: list[str] = []
    for row in rows:
        problems.extend(_validate_deferred_row(row, name))
    # "No single number is a verdict": a NET-01 group must keep all three
    # layers present together (§10.3).
    if name == "NET-01":
        problems.extend(_validate_net01_layers(rows))
    return problems


def _validate_deferred_row(row: dict, name: str) -> list[str]:
    problems: list[str] = []
    if row.get("mode") != "report_only":
        problems.append(
            f"[HARD] deferred row {row.get('metric_id')!r} in {name!r} must be "
            "report_only (never a silent gate/xfail, §10.3)"
        )
    if row.get("value") is not None:
        problems.append(
            f"[HARD] deferred row {row.get('metric_id')!r} in {name!r} carries a "
            "non-null value but is marked deferred — a deferred row is not measured"
        )
    return problems


def _validate_net01_layers(rows: list) -> list[str]:
    missing = {"L1", "L2", "L3"} - {row.get("layer") for row in rows}
    if missing:
        return [
            "[HARD] NET-01 group must keep all three layers together "
            f"(no single number is a verdict, §10.3); missing {sorted(missing)}"
        ]
    return []


def _print_report(board: dict) -> None:
    records = board.get("records", [])
    permanent = board.get("permanent", [])
    deferred = board.get("deferred_rows", [])
    print("\nscoreboard substrate (corpus/scoreboard.json):")
    print(f"  schema: {board.get('schema')}")
    print(f"  scored records: {len(records)} (Stage 0: empty by construction)")
    for row in permanent:
        print(f"  permanent: {row.get('metric_id')} = {row.get('value')} [{row.get('mode')}]")
    for group in deferred:
        rows = group.get("rows", [])
        print(f"  deferred group {group.get('group')}: {len(rows)} row(s), report-only")
        for row in rows:
            print(f"      {row.get('layer')} {row.get('metric_id')} — {row.get('status')}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    report_only = "--report" in argv
    repo_root = pathlib.Path.cwd()

    try:
        board = load(repo_root)
    except FileNotFoundError:
        print(f"[HARD] {SCOREBOARD_PATH} missing.")
        return 0 if report_only else 1
    except json.JSONDecodeError as exc:
        print(f"[HARD] {SCOREBOARD_PATH} is not valid JSON: {exc}")
        return 0 if report_only else 1

    problems = validate(board)
    for line in problems:
        print(line)
    _print_report(board)

    return 0 if report_only else (1 if problems else 0)


if __name__ == "__main__":
    sys.exit(main())
