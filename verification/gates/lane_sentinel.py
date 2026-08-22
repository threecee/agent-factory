"""Lane sentinel: the continuously-updated, report-first progress file (OPERATIONS §8).

A lane writes its current state to a small JSON sentinel *as it goes*, not only at the end, so a
force-collected, crashed, or un-woken lane always leaves current state on disk. The sentinel makes
"is this lane stalled?" a mechanical freshness query rather than an operator judgment call: a
lander or monitor reads the sentinel and, when a ``working`` lane's last update exceeds a budget,
is told to *artifact-check then nudge* before declaring the lane dead — the exact wave-13
missed-wakeup weak link the mrinal adoption points at.

Contract fields (what a sentinel must carry):

  lane           the lane name
  status         one of STATUSES: working | blocked | parked | done | failed
  leg            the current step ("verify running", "leg 3 of 6")
  last_artifact  the last durable output — a commit SHA, a pushed branch, a written file
  suite          the test/gate state ("pregate: green; full: running")
  spend          token / dollar spend if the lane is funded, else null
  branch         the lane branch
  head_sha       the lane head commit
  note           a short freeform note (why it parked, what it is waiting on)
  updated_at     ISO-8601 UTC, restamped on every write (the freshness clock)

CLI:

    python -m scripts.lane_sentinel update --lane mech --status working --leg "build helper" \
        --last-artifact abc1234 --suite "pregate: green" --dir "$SCRATCH"
    python -m scripts.lane_sentinel read  --lane mech --dir "$SCRATCH"
    python -m scripts.lane_sentinel check --lane mech --dir "$SCRATCH" --max-age-min 20

``check`` exit codes (a monitor branches on these):
  0  no action now  — working+fresh, or a terminal-clean done/parked
  2  no sentinel     — the lane never checked in
  3  working+STALE   — exceeds the budget: artifact-check then nudge before declaring stalled
  4  attention       — status is blocked or failed (needs the operator regardless of age)

Refs: docs/design-notes/2026-07-24_eksterne-fabrikk-kilder.md (mrinal entry, candidate
adoption #1 continuous progress file, #2 wakeup-as-watchdog); docs/OPERATIONS.md §8; ADR-0097.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

STATUSES = ("working", "blocked", "parked", "done", "failed")
# Only a lane that believes it is still working can be "stalled"; the other states already made a
# clean report and are age-exempt for staleness (blocked/failed still flag operator attention).
_LIVE = frozenset({"working"})
_ATTENTION = frozenset({"blocked", "failed"})
_TERMINAL_OK = frozenset({"parked", "done"})

SCHEMA = 1
_ISO = "%Y-%m-%dT%H:%M:%SZ"

# The optional contract fields an update may set (lane/status are always required, handled apart).
_FIELDS = ("leg", "last_artifact", "suite", "spend", "branch", "head_sha", "note")


def _now() -> dt.datetime:
    """Current UTC time. Indirected so tests can pin the freshness clock."""
    return dt.datetime.now(dt.UTC)


def sentinel_path(lane: str, directory: str | os.PathLike[str] | None = None) -> pathlib.Path:
    """``<dir>/<lane>.sentinel.json``. ``dir`` defaults to $LANE_SENTINEL_DIR or the cwd."""
    base = directory if directory is not None else os.environ.get("LANE_SENTINEL_DIR", ".")
    return pathlib.Path(base) / f"{lane}.sentinel.json"


def _fmt(moment: dt.datetime) -> str:
    return moment.astimezone(dt.UTC).strftime(_ISO)


def _parse(stamp: str) -> dt.datetime:
    return dt.datetime.strptime(stamp, _ISO).replace(tzinfo=dt.UTC)


def update_sentinel(
    path: str | os.PathLike[str],
    *,
    lane: str,
    status: str,
    now: dt.datetime | None = None,
    **fields: str | None,
) -> dict:
    """Create-or-merge the sentinel at ``path`` and restamp ``updated_at``.

    An update merges: fields left ``None`` keep their previous value, so a partial heartbeat
    (only ``suite`` changed) does not wipe the ``leg`` set earlier. Unknown ``status`` raises."""
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}; expected one of {', '.join(STATUSES)}")
    unexpected = set(fields) - set(_FIELDS)
    if unexpected:
        raise TypeError(f"unexpected sentinel field(s): {', '.join(sorted(unexpected))}")

    path = pathlib.Path(path)
    data: dict = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))

    data["schema"] = SCHEMA
    data["lane"] = lane
    data["status"] = status
    for field in _FIELDS:
        value = fields.get(field)
        if value is not None:
            data[field] = value
        else:
            data.setdefault(field, None)
    data["updated_at"] = _fmt(now or _now())

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def read_sentinel(path: str | os.PathLike[str]) -> dict:
    """Load the sentinel JSON, or raise ``FileNotFoundError`` if the lane never checked in."""
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def age_minutes(data: dict, now: dt.datetime | None = None) -> float:
    """Wall-clock minutes since ``updated_at``."""
    delta = (now or _now()) - _parse(data["updated_at"])
    return delta.total_seconds() / 60.0


def check_freshness(
    data: dict, max_age_min: float, now: dt.datetime | None = None
) -> tuple[str, str]:
    """Return ``(verdict, message)`` for a present sentinel.

    verdict is one of: ``fresh`` (working, within budget), ``stale`` (working, over budget —
    artifact-check then nudge), ``attention`` (blocked/failed), ``terminal`` (parked/done)."""
    lane = data.get("lane", "?")
    status = data.get("status", "?")
    leg = data.get("leg") or "?"
    age = age_minutes(data, now)
    where = f"leg='{leg}', last update {age:.0f}m ago"

    if status in _ATTENTION:
        return "attention", (
            f"[SENTINEL] lane {lane} status={status} — needs the operator ({where}). "
            f"note: {data.get('note') or '—'}"
        )
    if status in _TERMINAL_OK:
        return "terminal", (
            f"[SENTINEL] lane {lane} status={status} (terminal); {where}; not treated as stalled."
        )
    if status in _LIVE and age > max_age_min:
        return "stale", (
            f"[SENTINEL] lane {lane} STALE: last update {age:.0f}m ago exceeds "
            f"the {max_age_min:.0f}m budget (status={status}, {where}). "
            "Artifact-check then nudge before declaring stalled."
        )
    return "fresh", (
        f"[SENTINEL] lane {lane} FRESH: updated {age:.0f}m ago within the {max_age_min:.0f}m "
        f"budget (status={status}, leg='{leg}')."
    )


def render_sentinel(data: dict) -> str:
    """A human-legible rendering of a sentinel, for ``read`` and for a crashed-lane triage."""
    lines = [f"lane: {data.get('lane', '?')}", f"status: {data.get('status', '?')}"]
    for field in ("leg", "last_artifact", "suite", "spend", "branch", "head_sha", "note"):
        value = data.get(field)
        if value:
            lines.append(f"{field}: {value}")
    lines.append(f"updated_at: {data.get('updated_at', '?')}")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lane_sentinel", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _locate(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--file", help="explicit sentinel path (overrides --lane/--dir)")
        sp.add_argument("--lane", help="lane name (with --dir, forms <dir>/<lane>.sentinel.json)")
        sp.add_argument("--dir", help="sentinel directory (default $LANE_SENTINEL_DIR or cwd)")

    up = sub.add_parser("update", help="create or merge the sentinel and restamp updated_at")
    _locate(up)
    up.add_argument("--status", required=True, choices=STATUSES)
    for field in _FIELDS:
        up.add_argument(f"--{field.replace('_', '-')}", dest=field, default=None)

    rd = sub.add_parser("read", help="print the sentinel in human-legible form")
    _locate(rd)

    ck = sub.add_parser("check", help="freshness/status check for a lander or monitor")
    _locate(ck)
    ck.add_argument("--max-age-min", type=float, default=20.0)
    return parser


def _resolve(args: argparse.Namespace) -> pathlib.Path:
    if args.file:
        return pathlib.Path(args.file)
    if not args.lane:
        raise SystemExit("lane_sentinel: need --file, or --lane (with optional --dir)")
    return sentinel_path(args.lane, args.dir)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    path = _resolve(args)

    if args.cmd == "update":
        fields = {field: getattr(args, field) for field in _FIELDS}
        data = update_sentinel(path, lane=args.lane or "?", status=args.status, **fields)
        print(f"[SENTINEL] wrote {path} (status={data['status']}, updated_at={data['updated_at']})")
        return 0

    if args.cmd == "read":
        if not path.exists():
            print(f"[SENTINEL] no sentinel at {path}")
            return 2
        print(render_sentinel(read_sentinel(path)))
        return 0

    # check
    lane = args.lane or (path.stem.split(".")[0])
    if not path.exists():
        print(f"[SENTINEL] lane {lane}: no sentinel at {path} — lane never checked in.")
        return 2
    verdict, message = check_freshness(read_sentinel(path), args.max_age_min, now=_now())
    print(message)
    return {"fresh": 0, "terminal": 0, "stale": 3, "attention": 4}[verdict]


if __name__ == "__main__":
    sys.exit(main())
