"""M-21 change-kind guard (harness/guards.md §7).

On a landing-shaped ``PreToolUse`` command, the rule reads the train ledger's
declared ``kind:`` value and the receipt-bound ``BASE..HEAD`` path list, then
passes those paths to ``FACTORY_GUARD_KIND_CMD``. A delivered risk kind absent
from the declaration is refused; a declared risk kind absent from the delivery
is returned as context so the lander records the fall. ``docs-only`` is the
empty risk envelope, which makes the two falsification directions asymmetric.

An unbound classifier is silent. Missing inputs, a red classifier, or invalid
classifier output fail open with context; the existing landing rule owns hard
receipt and ledger validity.
"""

from __future__ import annotations

import pathlib
import re
import shlex
import subprocess

from guards._common import (
    ALLOW,
    FalsificationCase,
    GuardContext,
    Verdict,
    child_environ,
    command_of,
    context_note,
    current_branch,
    deny,
    git,
    payload_cwd,
    read_key_values,
)
from guards.rules import landing

ID = "kind"
EVENTS = frozenset({"PreToolUse"})
MATCHER = "Bash"
KIND_CMD_VAR = "FACTORY_GUARD_KIND_CMD"

KINDS = ("docs-only", "mechanical", "source", "record", "boundary")
RISK_KINDS = frozenset(set(KINDS) - {"docs-only"})
_KIND_LINE_RE = re.compile(r"^\s*kind:\s*(.+?)\s*(?:→|->)\s*(.+?)\s*$", re.M | re.I)


def _kind_set(value: str) -> frozenset[str] | None:
    parts = frozenset(part.strip() for part in value.split(",") if part.strip())
    return parts if parts and parts <= set(KINDS) else None


def _format(kinds: frozenset[str] | set[str]) -> str:
    return ", ".join(kind for kind in KINDS if kind in kinds)


def _kind_line(
    ledger_text: str,
) -> tuple[frozenset[str], frozenset[str]] | None:
    match = _KIND_LINE_RE.search(ledger_text)
    if not match:
        return None
    declared = _kind_set(match.group(1))
    recorded = _kind_set(match.group(2))
    return (declared, recorded) if declared is not None and recorded is not None else None


def _classifier(
    context: GuardContext, cwd: pathlib.Path, command: str, paths: list[str]
) -> tuple[int, str, str]:
    try:
        result = context.run(
            ["/bin/sh", "-c", f"{command} \"$@\"", "kind-classifier", *paths],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
            env=child_environ(context.environ),
        )
    except (OSError, subprocess.SubprocessError) as error:
        return 127, "", str(error)
    return result.returncode, result.stdout or "", result.stderr or ""


def _note(message: str) -> Verdict:
    return context_note(ID, f"GUARD kind: {message}")


def _check_landing(
    context: GuardContext, command: str, candidate: landing.Landing, cwd: pathlib.Path
) -> Verdict:
    branch = current_branch(context, cwd)
    train = landing.train_of(branch)
    if train is None:
        return ALLOW
    ledger_path = landing.ledger_path(context, cwd, train)
    try:
        ledger_text = ledger_path.read_text(encoding="utf-8")
    except OSError:
        return ALLOW  # the landing rule owns the hard missing-ledger refusal
    kind_line = _kind_line(ledger_text)
    if kind_line is None:
        return _note(
            f"the bound classifier could not be compared because {ledger_path} has no valid "
            "«kind: <declared>→<derived>» line; let the landing check continue. Fix: copy the "
            "brief's Kind value into the ledger and re-run the landing command"
        )
    declared, recorded = kind_line
    artifacts = landing.artifacts_dir(command, context, ledger_text)
    receipt = landing.newest_receipt(artifacts, train) if artifacts and artifacts.is_dir() else None
    if receipt is None:
        return ALLOW  # the landing rule owns the hard missing-receipt refusal
    values = read_key_values(receipt)
    base = values.get("BASE")
    code, head = git(context, cwd, "rev-parse", "HEAD")
    if not base or code != 0 or not head:
        return ALLOW  # the landing rule owns malformed receipt and non-git refusals
    code, listing = git(context, cwd, "diff", "--name-only", f"{base}..{head}")
    if code != 0:
        return _note(
            f"git could not derive the receipt-bound path list for {base[:8]}..{head[:8]} and "
            "let the landing check continue. Fix: repair the train repository and re-run the landing command"
        )
    classifier = context.environ.get(KIND_CMD_VAR)
    assert classifier is not None
    code, stdout, stderr = _classifier(context, cwd, classifier, listing.splitlines())
    if code != 0:
        detail = " ".join(stderr.split())[-240:] or "no diagnostic"
        return _note(
            f"classifier «{classifier}» exited {code} ({detail}) and let the landing check "
            f"continue. Fix: make {KIND_CMD_VAR} executable over repository-relative paths"
        )
    derived_parts = [line.strip() for line in stdout.splitlines() if line.strip()]
    derived = _kind_set(",".join(derived_parts))
    if derived is None:
        rendered = ", ".join(derived_parts) or "<empty>"
        return _note(
            f"classifier «{classifier}» printed invalid kinds «{rendered}» and let the landing "
            f"check continue. Fix: print only {', '.join(KINDS)}, one per line"
        )
    declared_risk = declared & RISK_KINDS
    derived_risk = derived & RISK_KINDS
    rose = derived_risk - declared_risk
    fell = declared_risk - derived_risk
    if rose:
        if recorded == derived:
            return ALLOW
        return deny(
            ID,
            f"GUARD kind: declared kind {_format(declared)} rose to {_format(derived)} over "
            f"{base[:8]}..{head[:8]}. Fix: run the {_format(rose)} legs selected by the "
            "derived diff, record the rise in the landing summary, update the ledger's kind "
            "line, and re-run the landing command",
        )
    if fell:
        if recorded == derived:
            return ALLOW
        return _note(
            f"delivered kind fell from {_format(declared)} to {_format(derived)}; record "
            f"«kind: {_format(declared)}→{_format(derived)}» and an O-<n> reason in the ledger; "
            "the landing command was not refused"
        )
    if recorded != derived:
        return _note(
            f"the ledger records {_format(recorded)} but the classifier derived "
            f"{_format(derived)}; record «kind: {_format(declared)}→{_format(derived)}» and "
            "re-run the landing command"
        )
    return ALLOW


def check(payload: dict[str, object], context: GuardContext) -> Verdict:
    if not context.environ.get(KIND_CMD_VAR):
        return ALLOW
    command = command_of(payload)
    first_note: Verdict | None = None
    for candidate in landing.find_landings(command):
        cwd = landing._landing_cwd(candidate, command, payload_cwd(payload))
        if candidate.kind == "create":
            continue
        if candidate.kind == "push" and not landing._is_default_destination(context, candidate, cwd):
            continue
        verdict = _check_landing(context, command, candidate, cwd)
        if verdict.kind == "deny":
            return verdict
        if verdict.kind == "context" and first_note is None:
            first_note = verdict
    return first_note or ALLOW


def falsification_cases(workdir: pathlib.Path) -> list[FalsificationCase]:
    from guards.rules import _landing_fixtures as fx

    classifier = workdir / "classify-kind"
    classifier.write_text(
        "#!/bin/sh\n"
        "[ \"${KIND_EXIT:-0}\" -eq 0 ] || exit \"$KIND_EXIT\"\n"
        "printf '%s\\n' \"${KIND_OUTPUT:-source}\"\n",
        encoding="utf-8",
    )
    classifier.chmod(0o755)
    classifier_cmd = shlex.quote(str(classifier))

    def ledger_for(declared: str, recorded: str | None = None) -> str:
        recorded = recorded or declared
        return fx.direct_push_ledger(fx.LEDGER).replace(
            "local-verify: skipped (no host in the fixture)\n",
            f"local-verify: skipped (no host in the fixture)\nkind: {declared}→{recorded}\n",
        )

    def case(
        name: str,
        expect: str,
        needle: str,
        declared: str,
        output: str,
        **extra: str,
    ) -> FalsificationCase:
        tree = fx.case_tree(workdir, name, ledger=ledger_for(declared))
        return fx._case(
            name,
            expect,
            needle,
            tree,
            env={KIND_CMD_VAR: classifier_cmd, "KIND_OUTPUT": output, **extra},
        )

    rise = case("docs-only-to-source", "deny", "declared kind docs-only rose to source", "docs-only", "source")
    fall = case("source-to-docs-only", "context", "delivered kind fell from source to docs-only", "source", "docs-only")
    equal = case("source-stays-source", "allow", "", "source", "source")
    invalid = case("invalid-classifier-output", "context", "printed invalid kinds", "source", "unknown")
    failed = case("classifier-failure", "context", "exited 7", "source", "source", KIND_EXIT="7")
    acknowledged_tree = fx.case_tree(
        workdir, "acknowledged-rise", ledger=ledger_for("docs-only", "source")
    )
    acknowledged = fx._case(
        "acknowledged-rise",
        "allow",
        "",
        acknowledged_tree,
        env={KIND_CMD_VAR: classifier_cmd, "KIND_OUTPUT": "source"},
    )
    unbound_tree = fx.case_tree(workdir, "unbound", ledger=ledger_for("source"))
    unbound = fx._case("unbound-classifier", "allow", "", unbound_tree)
    return [rise, fall, acknowledged, equal, invalid, failed, unbound]
