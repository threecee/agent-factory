"""Pre-commit git hook (verification/protections.md §1.3, mechanism M-10): the identity git
will actually write.

The tracked shim ``verification/protections/githooks/pre-commit`` runs the dispatcher with
event ``GitPreCommit``. One leg ships, ``commit-identity`` (HARD): the author and committer
e-mail git will write — ``git var GIT_AUTHOR_IDENT`` / ``GIT_COMMITTER_IDENT``, which honour
the environment (``GIT_AUTHOR_EMAIL``, ``GIT_COMMITTER_EMAIL``, ``EMAIL``, ``--author``)
before ``user.email`` — must be one of the declared identities in ``FACTORY_GUARD_GIT_EMAIL``
(comma-separated; a §8 parameter of harness/guards.md). The identity is declared, never
guessed: with the variable unset the leg checks nothing and says so on every commit (a
context WARN — an unbound parameter is visible, never silent). A config-only check would let
an environment override through; ``git var`` reads what git will write.

A second leg is described, not shipped: ``commit-secrets`` materialises the STAGED blobs
(``git show :<path>``, never the working tree) into a shadow tree and scans them with the
repository's secret scanner against its config and baseline, restricted to what this commit
would add; a new finding refuses the commit with the redacted location, and a missing or
crashing scanner is a loud WARN that lets the commit through — the verify gate over the
committed history stays fail-closed, the hook is its early warning. An installer adds it as a
rule module when the repository has a scanner and a baseline (protections.md §1.3).

A hook runs on local commits only; a pull-request merge commit the host writes carries the
host's web-flow committer and never passes here — a history scan over identities must exempt
it (protections.md §1.3).
"""

from __future__ import annotations

import pathlib
import re
from collections.abc import Mapping

from guards._common import ALLOW, FalsificationCase, GuardContext, Verdict, context_note, deny, git, payload_cwd

ID = "commit-identity"
EVENTS = frozenset({"GitPreCommit"})
MATCHER = None
EMAIL_VAR = "FACTORY_GUARD_GIT_EMAIL"
IDENT_VARS: tuple[tuple[str, str], ...] = (("author", "GIT_AUTHOR_IDENT"), ("committer", "GIT_COMMITTER_IDENT"))
IDENT_ENV: tuple[str, ...] = ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL", "EMAIL")
_IDENT_EMAIL_RE = re.compile(r"<([^>]*)>")


def declared_emails(environ: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(part.strip() for part in environ.get(EMAIL_VAR, "").split(",") if part.strip())


def effective_identities(context: GuardContext, cwd: pathlib.Path) -> dict[str, str]:
    """The e-mail git would write per role (``git var``: environment, then config, then the
    host fallback). An unresolvable identity reads as ``""``."""
    found: dict[str, str] = {}
    for role, var in IDENT_VARS:
        code, ident = git(context, cwd, "var", var)
        match = _IDENT_EMAIL_RE.search(ident) if code == 0 else None
        found[role] = match.group(1).strip() if match else ""
    return found


def _fix(context: GuardContext, cwd: pathlib.Path, role: str, declared: tuple[str, ...]) -> str:
    code, configured = git(context, cwd, "config", "--get", "user.email")
    if code == 0 and configured in declared:
        return (
            f"user.email is already declared; the {role} identity comes from the environment "
            f"({'/'.join(IDENT_ENV)} or --author) — unset {' '.join(IDENT_ENV)}"
        )
    return f"git config user.email {declared[0]}"


def check(payload: Mapping[str, object], context: GuardContext) -> Verdict:
    declared = declared_emails(context.environ)
    if not declared:
        return context_note(
            ID,
            f"GUARD commit-identity (warn): identity not declared ({EMAIL_VAR} unset); nothing checked. "
            f"Declare it in the operations doc and the hook environment (verification/protections.md §1.3).",
        )
    cwd = pathlib.Path(payload_cwd(payload) or ".").resolve()
    wrong = {role: email for role, email in effective_identities(context, cwd).items() if email not in declared}
    if not wrong:
        return ALLOW
    role, email = next(iter(wrong.items()))
    return deny(
        ID,
        f"GUARD commit-identity: the identity git will write is «{email or '(unset)'}» ({role}, git var), not the "
        f"declared «{', '.join(declared)}» (verification/protections.md §1.3). Fix: {_fix(context, cwd, role, declared)}",
    )


def pre_commit_payload(cwd: pathlib.Path) -> dict[str, object]:
    return {"hook_event_name": "GitPreCommit", "cwd": str(cwd), "session_id": "falsify", "git": {"hook": "pre-commit", "args": []}}


def falsification_cases(workdir: pathlib.Path) -> list[FalsificationCase]:
    from guards.rules._commit_fixtures import DECLARED_EMAIL, commit_repo

    def case(name: str, expect: str, needle: str, *, env: dict[str, str] | None = None, **repo) -> FalsificationCase:
        root = commit_repo(workdir, name, **repo)
        merged = {EMAIL_VAR: DECLARED_EMAIL, **(env or {})}
        return FalsificationCase(name, "GitPreCommit", pre_commit_payload(root), expect, needle, merged)  # type: ignore[arg-type]

    return [
        case("wrong-config-identity", "deny", "the identity git will write is «wrong@example.invalid»", email="wrong@example.invalid"),
        case("declared-identity", "allow", ""),
        case("environment-overrides-declared-config", "deny", "«employer@example.invalid» (author, git var)", env={"GIT_AUTHOR_EMAIL": "employer@example.invalid"}),
        case("committer-environment-override", "deny", "(committer, git var)", env={"GIT_COMMITTER_EMAIL": "employer@example.invalid"}),
        case("declaration-unset-is-a-warn", "context", "identity not declared", env={EMAIL_VAR: ""}, email="anyone@example.invalid"),
        case("identity-switch", "allow", "", email="wrong@example.invalid", env={"FACTORY_GUARD_ALLOW": ID}),
        case("second-declared-identity", "allow", "", email="second@example.invalid", env={EMAIL_VAR: f"{DECLARED_EMAIL},second@example.invalid"}),
    ]
