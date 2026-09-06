#!/usr/bin/env python3
"""Runnable model for verification/examples/identity-and-history.md.

Three domain-free examples, each a gate or plan that must follow the
CONSUMER's identity rather than a proxy (total row count, file mtime,
"restart from zero"):

  1. history vs live   — an unavailable row with a valid successor passes;
                         a live unavailable row under a configured role fails;
                         a promised-but-undelivered identity fails separately.
  2. newest vs digest  — a snapshot with a newer mtime but the wrong digest
                         is rejected; the consumer's digest key wins.
  3. incremental plan  — unchanged units are reused, changed units are
                         recomputed, progress after a retry never regresses.

Usage:
  python3 identity_and_history.py             # all three examples, exit 0
  python3 identity_and_history.py --plant X   # re-run with a planted defect,
                                              # expect a named red and exit 1
    X in: count-all | newest-mtime | restart-at-zero | weak-supersedes

Stdlib only. No database, no warmer, no product code — the point is the
shape of the verdicts, which a reader ports to their own store and gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

WEAK_PRODUCERS = {"unavailable", "floor"}  # results the real producer outranks


# ---------------------------------------------------------------------------
# Example 1 — history vs live vs promised
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Row:
    scope: str
    revision: int
    status: str  # current | superseded | stale
    producer: str  # "model" or a WEAK_PRODUCERS member


def consumer_selects(rows: list[Row]) -> dict[str, Row]:
    """THE consumer's selection rule: per scope, the highest-revision row whose
    status is 'current'. The gate must use this function, not its own."""
    chosen: dict[str, Row] = {}
    for row in rows:
        if row.status != "current":
            continue
        if row.scope not in chosen or row.revision > chosen[row.scope].revision:
            chosen[row.scope] = row
    return chosen


def gate_unavailable(
    rows: list[Row], promised_scopes: set[str], role: str, *, plant: str | None = None
) -> dict:
    """Return the receipt; raise AssertionError with the consumer's numbers."""
    selected = consumer_selects(rows)
    unavailable_total = sum(1 for r in rows if r.producer == "unavailable")
    live = sorted(s for s, r in selected.items() if r.producer == "unavailable")
    superseded_in_practice = unavailable_total - len(live)
    promised_undelivered = sorted(promised_scopes - set(selected))
    receipt = {
        "role": role,
        "unavailable_total": unavailable_total,
        "unavailable_live": len(live),
        "superseded_in_practice": superseded_in_practice,
        "promised_undelivered": len(promised_undelivered),
    }
    if role == "fake":
        receipt["deliberately_unavailable"] = unavailable_total
        return receipt  # a different evaluation type — reported, never rejected
    if plant == "count-all":
        if unavailable_total:
            raise AssertionError(f"configured role left unavailable artifacts: {unavailable_total}")
        return receipt
    if live:
        raise AssertionError(
            f"configured role {role!r} left LIVE unavailable artifacts: "
            f"live={len(live)} scopes={live} (history superseded_in_practice={superseded_in_practice})"
        )
    if promised_undelivered:
        raise AssertionError(
            f"configured role {role!r} promised but never delivered: {promised_undelivered}"
        )
    return receipt


def example_1(plant: str | None) -> None:
    rows = [
        Row("s1", 1, "superseded", "unavailable"),  # history: valid successor below
        Row("s1", 2, "current", "model"),
        Row("s2", 1, "superseded", "unavailable"),
        Row("s2", 2, "current", "model"),
        Row("s3", 1, "current", "model"),
    ]
    promised = {"s1", "s2", "s3"}

    # (a) historical rows with valid successors: gate must PASS, counts shown
    receipt = gate_unavailable(rows, promised, "model", plant=plant)
    assert receipt["unavailable_total"] == 2 and receipt["unavailable_live"] == 0, receipt
    assert receipt["superseded_in_practice"] == 2, receipt
    print("1a history-with-successor   PASS ", json.dumps(receipt))

    # (b) a LIVE unavailable row: gate must FAIL and name the live count
    live_rows = rows + [Row("s4", 1, "current", "unavailable")]
    try:
        gate_unavailable(live_rows, promised | {"s4"}, "model", plant=plant)
    except AssertionError as exc:
        assert "live=1" in str(exc) and "s4" in str(exc), f"wrong message: {exc}"
        print("1b live-unavailable         FAIL ", str(exc))
    else:
        raise AssertionError("false green: live unavailable row passed the gate")

    # (c) promised but never delivered: its own verdict
    try:
        gate_unavailable(rows, promised | {"s9"}, "model", plant=plant)
    except AssertionError as exc:
        assert "never delivered" in str(exc) and "s9" in str(exc), f"wrong message: {exc}"
        print("1c promised-undelivered     FAIL ", str(exc))
    else:
        raise AssertionError("false green: promised identity with no row passed the gate")

    # (d) deliberate fake: reported, not rejected — a different evaluation type
    receipt = gate_unavailable(live_rows, promised | {"s4"}, "fake", plant=plant)
    assert receipt["deliberately_unavailable"] == 3, receipt
    print("1d fake-role                PASS ", json.dumps(receipt))


# ---------------------------------------------------------------------------
# Example 2 — newest mtime vs the consumer's digest key
# ---------------------------------------------------------------------------


def digest_of(inputs: dict) -> str:
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:12]


def consumer_load(store: Path, inputs: dict) -> dict:
    """What the serving path does: recompute the key from inputs, load that file."""
    path = store / f"v1-{digest_of(inputs)}.json"
    if not path.is_file():
        raise AssertionError(
            f"snapshot is not what the consumer would compute: missing digest={digest_of(inputs)}"
        )
    return json.loads(path.read_text())


def gate_snapshot(store: Path, inputs: dict, *, plant: str | None = None) -> dict:
    if plant == "newest-mtime":
        newest = max(store.glob("v1-*.json"), key=lambda p: p.stat().st_mtime)
        return json.loads(newest.read_text())
    return consumer_load(store, inputs)


def example_2(plant: str | None) -> None:
    inputs = {"sources": ["a", "b"], "model": "m1"}
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp)
        good = store / f"v1-{digest_of(inputs)}.json"
        good.write_text(json.dumps({"items": 226, "digest": digest_of(inputs)}))
        decoy = store / "v1-3dbf19deadbe.json"  # mid-index leftover, wrong key
        decoy.write_text(json.dumps({"items": 225, "digest": "3dbf19deadbe"}))
        # a copy reordered mtimes: the decoy is now NEWER than the completed one
        import os

        os.utime(good, (1_700_000_000, 1_700_000_000))
        os.utime(decoy, (1_700_000_100, 1_700_000_100))

        chosen = gate_snapshot(store, inputs, plant=plant)
        assert chosen["digest"] == digest_of(inputs), (
            f"gate chose the newer decoy {chosen['digest']} over the consumer's key "
            f"{digest_of(inputs)} (items {chosen['items']} vs 226)"
        )
        print("2a digest-keyed              PASS  chosen", chosen)

        # the key the consumer would compute is absent: reject, never fall back to newest
        good.unlink()
        try:
            gate_snapshot(store, inputs, plant=plant)
        except AssertionError as exc:
            assert "missing digest" in str(exc), f"wrong message: {exc}"
            print("2b missing-key               FAIL ", str(exc))
        else:
            raise AssertionError("false green: gate fell back to the newest file")


# ---------------------------------------------------------------------------
# Example 3 — incremental plan: identity diff, exact precedence, progress
# ---------------------------------------------------------------------------


@dataclass
class Receipt:
    completed: int = 0
    total: int = 0
    attempts: int = 0

    def set_progress(self, completed: int, total: int) -> None:
        if completed < self.completed:
            raise ValueError(f"cannot regress progress {self.completed} -> {completed}")
        self.completed, self.total = completed, total


@dataclass
class Store:
    results: dict[str, tuple[str, str]] = field(default_factory=dict)  # identity -> (producer, value)
    receipt: Receipt = field(default_factory=Receipt)
    expensive_calls: list[str] = field(default_factory=list)

    def publish(self, identity: str, producer: str, value: str, *, plant: str | None) -> None:
        held = self.results.get(identity)
        if held and held[0] not in WEAK_PRODUCERS and producer in WEAK_PRODUCERS:
            if plant != "weak-supersedes":
                return  # exact precedence: a weaker result never replaces a stronger one
        self.results[identity] = (producer, value)


def prepare(inputs: dict[str, str]) -> dict[str, str]:
    """identity -> input digest. Identity is (unit, digest-of-input)."""
    return {f"{unit}:{digest_of({'v': value})}": value for unit, value in inputs.items()}


def run_attempt(store: Store, inputs: dict[str, str], *, plant: str | None) -> None:
    identities = prepare(inputs)
    pending = [i for i in identities if i not in store.results]  # exact hits are reused
    base = 0 if plant == "restart-at-zero" else store.receipt.completed
    store.receipt.attempts += 1
    store.receipt.set_progress(base, base + len(pending))
    for identity in pending:
        store.expensive_calls.append(identity)  # the model / expensive step
        store.publish(identity, "model", identities[identity].upper(), plant=plant)
        store.receipt.set_progress(store.receipt.completed + 1, store.receipt.total)
    # retire identities the plan no longer desires (never the exact hits)
    for identity in list(store.results):
        if identity not in identities:
            del store.results[identity]


def example_3(plant: str | None) -> None:
    store = Store()
    inputs = {"a": "x", "b": "y", "c": "z"}
    run_attempt(store, inputs, plant=plant)
    assert store.receipt.completed == 3 and store.receipt.total == 3
    first_calls = list(store.expensive_calls)
    print("3a first attempt             PASS  progress", store.receipt)

    # inputs move mid-plan: b changes, d arrives, a and c are unchanged
    inputs = {"a": "x", "b": "y2", "c": "z", "d": "w"}
    run_attempt(store, inputs, plant=plant)
    calls_second = store.expensive_calls[len(first_calls) :]
    unchanged = {i for i in prepare({"a": "x", "c": "z"})}
    assert not (unchanged & set(calls_second)), f"unchanged identity recomputed: {calls_second}"
    assert any(i.startswith("b:") for i in calls_second), "changed unit was not recomputed"
    assert any(i.startswith("d:") for i in calls_second), "new unit was not computed"
    assert store.receipt.completed == 5 and store.receipt.total == 5, store.receipt
    print("3b identity diff             PASS  recomputed", calls_second)

    # a weaker producer (floor/unavailable) arrives for an exact current identity
    b_identity = next(i for i in store.results if i.startswith("b:"))
    store.publish(b_identity, "floor", "?", plant=plant)
    assert store.results[b_identity][0] == "model", (
        f"weak result superseded a stronger current one: {store.results[b_identity]}"
    )
    print("3c exact precedence          PASS ", store.results[b_identity])

    # a retry (new attempt on the same receipt) must start from the stored progress
    before = store.receipt.completed
    run_attempt(store, inputs, plant=plant)
    assert store.receipt.completed >= before, store.receipt
    assert store.expensive_calls[len(first_calls) + len(calls_second) :] == [], (
        "retry replayed already-checkpointed identities"
    )
    print("3d progress after retry      PASS  progress", store.receipt)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--plant",
        choices=["count-all", "newest-mtime", "restart-at-zero", "weak-supersedes"],
        help="re-run with a planted defect; the matching example must go red",
    )
    args = parser.parse_args()
    try:
        example_1(args.plant)
        example_2(args.plant)
        example_3(args.plant)
    except (AssertionError, ValueError) as exc:
        print(f"RED ({args.plant or 'no plant'}): {exc}")
        return 1
    print("ok: all three examples green" + (f" despite plant={args.plant}" if args.plant else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
