#!/usr/bin/env python3
"""Apply the default-branch ruleset (verification/protections.md §2, mechanism M-11) —
idempotent create/update through ``gh api``; dry run by default.

The payload is ``verification/ci/ruleset-main.json.example`` (edit a copy for another branch
name): deletion refused, non-fast-forward refused, the required status ``local-verify`` on
the exact commit with the strict up-to-date policy ON, no bypass actor — and no pull-request
rule and no review rule, which is what admits BOTH landing modes (a pull-request merge with
the status, or a direct push carrying it; verification/landing-modes.md §3).

    python3 verification/protections/bootstrap_ruleset.py                     # dry run: list + plan, nothing written
    python3 verification/protections/bootstrap_ruleset.py --apply             # POST (create) or PUT (update) the plan
    python3 verification/protections/bootstrap_ruleset.py --check [--strict]  # exit 1 on drift; offline exit 0 (2 with --strict)
    python3 verification/protections/bootstrap_ruleset.py --apply --enforcement evaluate   # the logged escape, one landing
    options: --file <payload.json> --repo <owner>/<name> --enforcement active|evaluate|disabled

The plan compares the normalized ruleset (name, target, enforcement, bypass actors,
conditions, rules — ids and host defaults such as ``do_not_enforce_on_create=false`` dropped)
with what the host holds, and prints one line per ruleset:
``[ruleset] <name>: create|update (id N)|unchanged — target=… enforcement=… rules=… bypass=0``.
It never deletes a ruleset. A 403 or an "upgrade" answer prints the paid-plan hint
(rulesets on a private user-owned repository need a paid plan: make the repository public,
move it to an organisation, or use the classic protection fallback in
``verification/ci/README.md``). After ``--apply`` it prints the repository-settings command
(merge commits only, delete-branch-on-merge) for the owner to run — it does not run it.

Never run by the lane that wrote the payload: the lander applies it once, records the date in
train-plan §5 and falsifies it in a throwaway repository (falsification.md rule 16). ``main(argv,
run=…)`` is the seam the package test uses with a fake ``gh``.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_FILE = HERE.parents[0] / "ci" / "ruleset-main.json.example"
ENFORCEMENTS = ("active", "evaluate", "disabled")
_COMPARED_KEYS = ("name", "target", "enforcement", "bypass_actors", "conditions", "rules")
SETTINGS_COMMAND = (
    "gh api -X PATCH repos/{owner}/{repo} -F allow_squash_merge=false -F allow_rebase_merge=false "
    "-F allow_merge_commit=true -F delete_branch_on_merge=true"
)
Runner = Callable[[list[str], str | None], "subprocess.CompletedProcess[str]"]


class Offline(RuntimeError):
    """``gh`` missing, unauthenticated, or the network failed — nothing verified."""


def load_payload(path: pathlib.Path, enforcement: str | None) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "name" not in data or "rules" not in data:
        raise ValueError(f"{path} is not a ruleset payload (needs name, target, rules)")
    if enforcement:
        data["enforcement"] = enforcement
    data.setdefault("bypass_actors", [])
    return data


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _clean(item)
            for key, item in value.items()
            if item is not None and not (key == "do_not_enforce_on_create" and item is False)
        }
    if isinstance(value, list):
        return [_clean(item) for item in value]
    return value


def normalize(ruleset: Mapping[str, Any]) -> dict[str, Any]:
    picked = {key: ruleset.get(key) for key in _COMPARED_KEYS if key in ruleset}
    picked.setdefault("bypass_actors", [])
    picked["bypass_actors"] = [
        {k: actor.get(k) for k in ("actor_id", "actor_type", "bypass_mode")} for actor in picked["bypass_actors"] or []
    ]
    return _clean(picked)


@dataclass(frozen=True)
class Action:
    kind: str  # create | update | unchanged
    ruleset: dict[str, Any]
    existing_id: int | None = None

    @property
    def name(self) -> str:
        return str(self.ruleset["name"])

    def line(self) -> str:
        rules = ", ".join(rule["type"] for rule in self.ruleset["rules"])
        target = f" (id {self.existing_id})" if self.existing_id is not None else ""
        return (
            f"[ruleset] {self.name}: {self.kind}{target} — target={self.ruleset.get('target')} "
            f"enforcement={self.ruleset.get('enforcement')} rules={rules} bypass={len(self.ruleset.get('bypass_actors') or [])}"
        )


def _gh(args: list[str], input_text: str | None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(["gh", *args], input=input_text, capture_output=True, text=True, check=False, timeout=60)
    except FileNotFoundError:
        return subprocess.CompletedProcess(["gh", *args], 127, "", "gh: command not found")
    except subprocess.SubprocessError as error:
        return subprocess.CompletedProcess(["gh", *args], 1, "", str(error))


def _api(run: Runner, args: list[str], body: Mapping[str, Any] | None = None) -> Any:
    command = ["api", *args]
    payload = None
    if body is not None:
        command += ["--input", "-"]
        payload = json.dumps(body)
    result = run(command, payload)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        lowered = detail.lower()
        if result.returncode == 127 or "not logged in" in lowered or "could not resolve" in lowered or "network" in lowered or "connect" in lowered:
            raise Offline(detail[:200] or "gh unavailable")
        hint = ""
        if "403" in detail or "pgrade" in detail:
            hint = (
                " — rulesets on a private user-owned repository need a paid plan: make the repository "
                "public, move it to an organisation, or apply the classic protection fallback (verification/ci/README.md)"
            )
        raise RuntimeError(f"gh {' '.join(command[:3])} failed: {detail[:300]}{hint}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def _rulesets_path(repo: str | None) -> str:
    return f"repos/{repo}/rulesets" if repo else "repos/{owner}/{repo}/rulesets"


def list_rulesets(run: Runner, repo: str | None) -> list[dict[str, Any]]:
    listing = _api(run, [_rulesets_path(repo), "--paginate"])
    return list(listing) if isinstance(listing, list) else []


def get_ruleset(run: Runner, repo: str | None, ruleset_id: int) -> dict[str, Any]:
    return dict(_api(run, [f"{_rulesets_path(repo)}/{ruleset_id}"]) or {})


def plan(run: Runner, repo: str | None, desired: dict[str, Any]) -> Action:
    existing = {str(row.get("name")): row for row in list_rulesets(run, repo)}
    row = existing.get(str(desired["name"]))
    if row is None:
        return Action("create", desired)
    current = get_ruleset(run, repo, int(row["id"]))
    kind = "unchanged" if normalize(current) == normalize(desired) else "update"
    return Action(kind, desired, int(row["id"]))


def apply(run: Runner, repo: str | None, action: Action) -> str:
    if action.kind == "create":
        created = _api(run, ["-X", "POST", _rulesets_path(repo)], action.ruleset) or {}
        return f"created {action.name} (id {created.get('id', '?')})"
    if action.kind == "update":
        _api(run, ["-X", "PUT", f"{_rulesets_path(repo)}/{action.existing_id}"], action.ruleset)
        return f"updated {action.name} (id {action.existing_id})"
    return f"unchanged {action.name} (id {action.existing_id})"


def main(argv: list[str] | None = None, run: Runner = _gh) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--file", type=pathlib.Path, default=DEFAULT_FILE)
    parser.add_argument("--repo", default=None, help="<owner>/<name>; default: the current directory's remote")
    parser.add_argument("--apply", action="store_true", help="write the plan (else dry run)")
    parser.add_argument("--check", action="store_true", help="exit 1 when the host drifts from the payload")
    parser.add_argument("--strict", action="store_true", help="with --check: offline is exit 2, not 0")
    parser.add_argument("--enforcement", choices=ENFORCEMENTS, default=None)
    args = parser.parse_args(argv)
    try:
        desired = load_payload(args.file, args.enforcement)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"[RULESET] payload unreadable: {error}", file=sys.stderr)
        return 1
    if args.enforcement == "evaluate":
        print("[ruleset] enforcement evaluate is the logged escape for ONE landing: the ledger carries the O-entry and active is restored right after (verification/landing-modes.md §3)")
    try:
        action = plan(run, args.repo, desired)
        print(action.line())
        if args.check:
            if action.kind == "unchanged":
                print(f"[ruleset] {action.name}: verified against the host")
                return 0
            print(f"[RULESET] {action.name}: drift — the host would need {action.kind}; run --apply after a dry run", file=sys.stderr)
            return 1
        if not args.apply:
            print("[ruleset] dry-run: nothing written (--apply to write)")
            return 0
        print(f"[ruleset] {apply(run, args.repo, action)}")
        print(f"[ruleset] now run the repository-settings command yourself (merge commits only, delete branch on merge): {SETTINGS_COMMAND}")
    except Offline as error:
        print(f"[ruleset] not verified (offline: {error})")
        return 2 if (args.check and args.strict) else 0
    except RuntimeError as error:
        print(f"[RULESET] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
