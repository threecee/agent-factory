#!/usr/bin/env python3
"""Parse Codex JSON events or the plain final ``tokens used`` line into cost keys."""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Any, Iterable

sys.dont_write_bytecode = True

INTEGER_KEYS = {
    "tokens_in": ("input_tokens", "inputTokens"),
    "tokens_out": ("output_tokens", "outputTokens"),
    "cached_tokens": ("cached_input_tokens", "cached_tokens", "cachedInputTokens"),
}


def objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from objects(nested)


def first_value(items: Iterable[dict[str, Any]], names: tuple[str, ...]) -> Any:
    for item in items:
        for name in names:
            if name in item:
                return item[name]
    return None


def parse_json_lines(lines: list[str]) -> dict[str, str] | None:
    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            events.append(value)
    usage_events = [event for event in events if "usage" in event or str(event.get("type", "")).endswith("completed")]
    if not usage_events:
        return None

    totals = {key: 0 for key in INTEGER_KEYS}
    known = {key: False for key in INTEGER_KEYS}
    for event in usage_events:
        nested = list(objects(event))
        for output_key, input_keys in INTEGER_KEYS.items():
            value = first_value(nested, input_keys)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[output_key] += value
                known[output_key] = True
    all_objects = list(objects(events))
    model = first_value(all_objects, ("model", "model_name", "modelName"))
    effort = first_value(all_objects, ("effort", "reasoning_effort", "reasoningEffort"))
    result = {key: str(totals[key]) if known[key] else "unknown" for key in INTEGER_KEYS}
    result.update(
        requests=str(len([event for event in usage_events if "usage" in event]) or len(usage_events)),
        model=str(model) if model else "unknown",
        effort=str(effort) if effort else "unknown",
        wall_s="unknown",
        source="codex_usage.py",
    )
    return result


def parse_plain(text: str) -> dict[str, str] | None:
    matches = re.findall(r"(?im)^\s*tokens used\s*:?\s*([0-9][0-9,]*)\s*$", text)
    if not matches:
        return None
    total = matches[-1].replace(",", "")
    return {
        "tokens_in": "unknown",
        "tokens_out": "unknown",
        "cached_tokens": "unknown",
        "requests": "1",
        "model": "unknown",
        "effort": "unknown",
        "wall_s": "unknown",
        "source": "codex_usage.py",
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: codex_usage.py <run-log>", file=sys.stderr)
        return 2
    path = pathlib.Path(args[0])
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"codex_usage: cannot read {path}: {exc}", file=sys.stderr)
        return 2
    result = parse_json_lines(text.splitlines()) or parse_plain(text)
    if result is None:
        result = {
            "tokens_in": "unknown",
            "tokens_out": "unknown",
            "cached_tokens": "unknown",
            "requests": "unknown",
            "model": "unknown",
            "effort": "unknown",
            "wall_s": "unknown",
            "source": "unavailable",
        }
    for key in ("tokens_in", "tokens_out", "cached_tokens", "requests", "model", "effort", "wall_s", "source"):
        print(f"{key}={result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
