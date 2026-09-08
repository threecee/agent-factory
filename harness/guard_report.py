#!/usr/bin/env python3
"""Summarize denials, switch use, and recurring anti-patterns in a guard event log."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import pathlib
import re
import sys
from typing import Iterable

sys.dont_write_bytecode = True

# Operators extend this one table. Expressions match the flattened message column from
# factory-events.log; names are stable report identifiers.
ANTI_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("verdict-pipe", re.compile(r"(?i)(verdict|gate).*(pipe|piped|\|\s*(tail|head|grep|tee))")),
    ("gate-plus-push", re.compile(r"(?i)gate.*(?:then|;|&&).*\bgit\s+push\b")),
    ("self-matching-kill", re.compile(r"(?i)\bpgrep\s+-f\b.*(?:itself|kill)|text-match.*kill")),
    ("stale-canary", re.compile(r"(?i)(?:stale|expired).*(?:quota[- ]?canary)|quota[- ]?canary.*(?:stale|expired)")),
    ("raw-cli-outside-launcher", re.compile(r"(?i)\braw\b.*\b(?:codex|claude|agent)\b.*\b(?:exec|run)\b.*(?:outside|without).*(?:launch|wrapper)|outside\s+launch_lane")),
    ("no-justification", re.compile(r"(?i)(?:missing|no|without).*(?:justification|reason)")),
    ("idle-violation", re.compile(r"(?i)(?:not idle|idle (?:precondition|contract|violation)|machine is not idle)")),
    ("stale-build", re.compile(r"(?i)(?:stale|out[- ]of[- ]date).*(?:build|bundle)|(?:build|bundle).*stale")),
    ("board-unverified", re.compile(r"(?i)board.*(?:unverified|not verified|verification missing)")),
    ("unbounded-read", re.compile(r"(?i)(?:unbounded|unlimited).*(?:read|context)|(?:read|context).*unbounded")),
)


def parse_time(value: str) -> dt.datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = dt.datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def read_rows(path: pathlib.Path) -> list[dict[str, str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SystemExit(f"guard_report: cannot read {path}: {exc}") from exc
    rows: list[dict[str, str]] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        fields = line.split("\t", 5)
        if len(fields) != 6:
            print(f"guard_report: ignored malformed row {number} in {path}", file=sys.stderr)
            continue
        timestamp, session, event, kind, rule, message = fields
        try:
            parse_time(timestamp)
        except ValueError:
            print(f"guard_report: ignored row {number} with invalid timestamp", file=sys.stderr)
            continue
        rows.append(
            {
                "timestamp": timestamp,
                "session": session,
                "event": event,
                "kind": kind,
                "rule": rule,
                "message": message,
            }
        )
    return rows


def span(rows: Iterable[dict[str, str]]) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: parse_time(row["timestamp"]))
    return {
        "count": len(ordered),
        "first": ordered[0]["timestamp"],
        "last": ordered[-1]["timestamp"],
        "newest_message": ordered[-1]["message"],
    }


def looping_denials(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for row in rows:
        if row["kind"] == "deny":
            groups[row["message"]].append(row)
    matched: list[dict[str, str]] = []
    for same_message in groups.values():
        ordered = sorted(same_message, key=lambda row: parse_time(row["timestamp"]))
        for index in range(len(ordered) - 2):
            if (parse_time(ordered[index + 2]["timestamp"]) - parse_time(ordered[index]["timestamp"])).total_seconds() <= 600:
                matched.extend(ordered)
                break
    return matched


def build_report(rows: list[dict[str, str]], *, session: str | None, since: str | None) -> dict[str, object]:
    if session is not None:
        rows = [row for row in rows if row["session"] == session]
    if since is not None:
        threshold = parse_time(since)
        rows = [row for row in rows if parse_time(row["timestamp"]) >= threshold]

    denied: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    switches: list[dict[str, str]] = []
    for row in rows:
        if row["kind"] == "deny":
            denied[row["rule"]].append(row)
        elif row["kind"] == "allow-switch":
            switches.append(row)

    patterns: dict[str, dict[str, object]] = {}
    denial_rows = [row for row in rows if row["kind"] == "deny"]
    for name, expression in ANTI_PATTERNS:
        hits = [row for row in denial_rows if expression.search(row["message"])]
        if hits:
            patterns[name] = span(hits)
    loops = looping_denials(rows)
    if loops:
        loop_span = span(loops)
        loop_span["count"] = len({row["message"] for row in loops})
        patterns["looping-denial"] = loop_span

    return {
        "session": session,
        "since": since,
        "denials": {rule: span(values) for rule, values in sorted(denied.items())},
        "switches": switches,
        "anti_patterns": patterns,
    }


def markdown(data: dict[str, object]) -> str:
    lines = ["# Guard anti-pattern report", "", "## Denials per rule", "", "| Rule | Count | First | Last | Newest message |", "|---|---:|---|---|---|"]
    denials = data["denials"]
    assert isinstance(denials, dict)
    for rule, item in denials.items():
        assert isinstance(item, dict)
        message = str(item["newest_message"]).replace("|", "\\|")
        lines.append(f"| {rule} | {item['count']} | {item['first']} | {item['last']} | {message} |")
    if not denials:
        lines.append("| none | 0 | — | — | — |")

    lines += ["", "## Switches used", "", "| Time | Rule | Source |", "|---|---|---|"]
    switches = data["switches"]
    assert isinstance(switches, list)
    for item in switches:
        lines.append(f"| {item['timestamp']} | {item['rule']} | {item['message'].replace('|', '\\|')} |")
    if not switches:
        lines.append("| — | none | — |")

    lines += ["", "## Named anti-patterns", "", "| Anti-pattern | Count | First | Last | Newest message |", "|---|---:|---|---|---|"]
    patterns = data["anti_patterns"]
    assert isinstance(patterns, dict)
    for name, item in patterns.items():
        assert isinstance(item, dict)
        message = str(item["newest_message"]).replace("|", "\\|")
        lines.append(f"| {name} | {item['count']} | {item['first']} | {item['last']} | {message} |")
    if not patterns:
        lines.append("| none | 0 | — | — | — |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--session")
    selector.add_argument("--since", help="ISO-8601 timestamp")
    parser.add_argument("--log", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    log = args.log or pathlib.Path(os.environ.get("FACTORY_GUARD_STATE_DIR", ".factory-guard")) / "factory-events.log"
    try:
        if args.since:
            parse_time(args.since)
    except ValueError as exc:
        parser.error(f"invalid --since value: {exc}")
    data = build_report(read_rows(log), session=args.session, since=args.since)
    if args.as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(markdown(data), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
