"""Commit-msg git hook (verification/protections.md §1.2, mechanism M-10): the decision-record
trailer on source commits, HARD; the subject form, WARN.

The tracked shim ``verification/protections/githooks/commit-msg`` feeds the proposed message
to the dispatcher as event ``GitCommitMsg``. Two legs, each with its own switch:

* ``commit-refs`` (HARD): when the staged diff touches ``FACTORY_GUARD_SOURCE_PREFIX``
  (default ``src/``; comma-separated prefixes) the message must carry the decision-record
  trailer (``FACTORY_GUARD_TRAILER_RE``, default ``^Refs: (ADR-\\d{4})``) and every referenced
  record must exist under ``FACTORY_GUARD_DECISIONS_DIR`` (default ``docs/decisions``) in
  ``HEAD`` or as staged Markdown in the same commit — an untracked file and a claimed number
  are dangling references until the record is carried by git (the
  three are §8 parameters of harness/guards.md). Merges
  (``MERGE_HEAD`` present, or an amended merge commit) and subjects starting ``Revert "``,
  ``Merge `` (this covers the host's ``Merge pull request`` commit), ``fixup! `` or
  ``squash! `` are exempt — the boarded or reverted commits carry the trailer. The touched
  files are the index against ``HEAD``; when nothing is staged against ``HEAD`` yet git is
  committing, the commit is an ``--amend`` (or ``--allow-empty``) and carries ``HEAD``'s own
  diff, so the index is measured against ``HEAD~1`` instead — ``git commit --amend -m`` cannot
  launder the trailer away. An amend of the root commit measures the whole index.
* ``commit-subject`` (WARN, context only): the subject should read
  ``<type>(<scope>): <imperative>``; it becomes a refusal only by a reviewed diff to the
  operations doc after one train.

Switches: ``FACTORY_GUARD_ALLOW=commit-refs`` or ``=commit-subject`` silences one leg —
the leg answers a «switched off» verdict under its own id and the dispatcher logs the use;
``FACTORY_GUARD_ALLOW=commit-msg`` (the module's id) silences both legs, as for any rule.

A hook runs on local commits only: a merge commit the host writes for a pull request never
passes here, and a range scan over history (a trailer or identity gate) must exempt it as
this module does, or the first verify after a pull-request landing goes red
(protections.md §1.2).
"""

from __future__ import annotations

import pathlib
import re
from collections.abc import Mapping
from dataclasses import dataclass

from guards._common import ALLOW, FalsificationCase, GuardContext, Verdict, context_note, deny, git, payload_cwd

ID = "commit-msg"
REFS_ID = "commit-refs"
SUBJECT_ID = "commit-subject"
EVENTS = frozenset({"GitCommitMsg"})
MATCHER = None

SOURCE_PREFIX_VAR = "FACTORY_GUARD_SOURCE_PREFIX"
TRAILER_RE_VAR = "FACTORY_GUARD_TRAILER_RE"
DECISIONS_DIR_VAR = "FACTORY_GUARD_DECISIONS_DIR"
DEFAULT_SOURCE_PREFIX = "src/"
DEFAULT_TRAILER_RE = r"^Refs: (ADR-\d{4})"
DEFAULT_DECISIONS_DIR = "docs/decisions"

SWITCHED_OFF = "switched off"  # the dispatcher's marker for a logged switch use
_SUBJECT_RE = re.compile(r"^[a-z][a-z0-9-]*(\([^)]+\))?!?: \S")
_EXEMPT_RE = re.compile(r'^(Revert "|Merge |fixup! |squash! )')
_DIGITS_RE = re.compile(r"(\d{3,})")
AMEND_NOTE = "; nothing is staged against HEAD, so this is an --amend (or --allow-empty) and the diff is measured against HEAD~1"


def message_of(payload: Mapping[str, object]) -> str:
    info = payload.get("git")
    message = info.get("message") if isinstance(info, Mapping) else None
    return message if isinstance(message, str) else ""


def subject_of(message: str) -> str:
    for line in message.splitlines():
        if line.strip() and not line.startswith("#"):
            return line.strip()
    return ""


def source_prefixes(environ: Mapping[str, str]) -> tuple[str, ...]:
    raw = environ.get(SOURCE_PREFIX_VAR) or DEFAULT_SOURCE_PREFIX
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def trailer_pattern(environ: Mapping[str, str]) -> re.Pattern[str]:
    raw = environ.get(TRAILER_RE_VAR) or DEFAULT_TRAILER_RE
    try:
        return re.compile(raw, re.M)
    except re.error:
        return re.compile(DEFAULT_TRAILER_RE, re.M)


def decisions_dir(environ: Mapping[str, str]) -> str:
    return (environ.get(DECISIONS_DIR_VAR) or DEFAULT_DECISIONS_DIR).rstrip("/")


@dataclass(frozen=True)
class StagedDiff:
    files: list[str]
    amend: bool = False


def staged_diff(context: GuardContext, cwd: pathlib.Path) -> StagedDiff:
    code, listing = git(context, cwd, "diff", "--cached", "--name-only", "--diff-filter=ACMRD")
    files = listing.splitlines() if code == 0 else []
    if files:
        return StagedDiff(files)
    code, _ = git(context, cwd, "rev-parse", "-q", "--verify", "HEAD")
    if code != 0:
        return StagedDiff([])  # an empty root commit
    code, parent = git(context, cwd, "rev-parse", "-q", "--verify", "HEAD~1")
    if code == 0:
        code, listing = git(context, cwd, "diff", "--cached", "--name-only", "--diff-filter=ACMRD", parent)
    else:  # amending the root commit: everything in the index is what it carries
        code, listing = git(context, cwd, "ls-files", "--cached")
    return StagedDiff(listing.splitlines() if code == 0 else [], amend=True)


def merge_in_progress(context: GuardContext, cwd: pathlib.Path) -> bool:
    return git(context, cwd, "rev-parse", "-q", "--verify", "MERGE_HEAD")[0] == 0


def head_is_merge(context: GuardContext, cwd: pathlib.Path) -> bool:
    return git(context, cwd, "rev-parse", "-q", "--verify", "HEAD^2")[0] == 0


def record_ids(message: str, pattern: re.Pattern[str]) -> list[str]:
    """The record identifiers the trailer lines name (the pattern's first group, else the match)."""
    ids: list[str] = []
    for match in pattern.finditer(message):
        ids.append(match.group(1) if match.groups() else match.group(0))
    return ids


def _record_path(path: str, directory: str, number: str) -> bool:
    prefix = f"{directory}/{number}"
    return path.endswith(".md") and (path == f"{prefix}.md" or path.startswith(f"{prefix}-"))


def record_exists(context: GuardContext, cwd: pathlib.Path, directory: str, record: str, staged: list[str]) -> bool:
    digits = _DIGITS_RE.search(record)
    number = digits.group(1) if digits else record
    for path in staged:
        if _record_path(path, directory, number) and git(context, cwd, "cat-file", "-e", f":{path}")[0] == 0:
            return True
    code, listing = git(context, cwd, "ls-tree", "-r", "--name-only", "HEAD", "--", directory)
    return code == 0 and any(_record_path(path, directory, number) for path in listing.splitlines())


def _exempt(context: GuardContext, cwd: pathlib.Path, message: str, amend: bool) -> bool:
    if _EXEMPT_RE.match(subject_of(message)) or merge_in_progress(context, cwd):
        return True
    return amend and head_is_merge(context, cwd)


def _switched(context: GuardContext, leg: str, verdict: Verdict | None) -> Verdict | None:
    """A leg-level switch: the finding stands but the leg is off — answered as a switched-off
    verdict under the leg's id so the dispatcher logs the switch use (harness/guards.md §4)."""
    if verdict is None or not context.switched_off(leg):
        return verdict
    return Verdict("allow", leg, SWITCHED_OFF)


def refs_verdict(context: GuardContext, cwd: pathlib.Path, message: str, diff: StagedDiff) -> Verdict | None:
    return _switched(context, REFS_ID, _refs_finding(context, cwd, message, diff))


def _refs_finding(context: GuardContext, cwd: pathlib.Path, message: str, diff: StagedDiff) -> Verdict | None:
    prefixes = source_prefixes(context.environ)
    source = [path for path in diff.files if path.startswith(prefixes)]
    if not source or _exempt(context, cwd, message, diff.amend):
        return None
    pattern = trailer_pattern(context.environ)
    trailer = context.environ.get(TRAILER_RE_VAR) or DEFAULT_TRAILER_RE
    ids = record_ids(message, pattern)
    if not ids:
        note = AMEND_NOTE if diff.amend else ""
        return deny(
            REFS_ID,
            f"GUARD commit-refs: the commit touches {', '.join(prefixes)} ({len(source)} file(s), e.g. "
            f"{source[0]}{note}) without a «{trailer}» trailer (planning/adr-and-numbers.md). Fix: add the "
            "trailer line at the end of the message (blank line before the trailers) — git commit --amend, "
            "or a new -m",
        )
    directory = decisions_dir(context.environ)
    missing = [record for record in ids if not record_exists(context, cwd, directory, record, diff.files)]
    if missing:
        return deny(
            REFS_ID,
            f"GUARD commit-refs: «{missing[0]}» names a decision record that does not exist under {directory}/ "
            "(a claimed number is a dangling reference until its file exists). Fix: reference a landed record, "
            f"or commit {directory}/<number>-<slug>.md in the same commit",
        )
    return None


def subject_verdict(context: GuardContext, message: str) -> Verdict | None:
    return _switched(context, SUBJECT_ID, _subject_finding(message))


def _subject_finding(message: str) -> Verdict | None:
    subject = subject_of(message)
    if not subject or _SUBJECT_RE.match(subject) or _EXEMPT_RE.match(subject):
        return None
    return context_note(
        SUBJECT_ID,
        f"GUARD commit-subject (warn): subject «{subject[:72]}» should read <type>(<scope>): <imperative> "
        f"(planning/lane-brief-template.md). Switch: FACTORY_GUARD_ALLOW={SUBJECT_ID}.",
    )


def check(payload: Mapping[str, object], context: GuardContext) -> Verdict:
    message = message_of(payload)
    if not message.strip():
        return ALLOW
    cwd = pathlib.Path(payload_cwd(payload) or ".").resolve()
    diff = staged_diff(context, cwd)
    return refs_verdict(context, cwd, message, diff) or subject_verdict(context, message) or ALLOW


def commit_msg_payload(cwd: pathlib.Path, message: str) -> dict[str, object]:
    return {
        "hook_event_name": "GitCommitMsg",
        "cwd": str(cwd),
        "session_id": "falsify",
        "git": {"hook": "commit-msg", "args": [str(cwd / ".git" / "COMMIT_EDITMSG")], "message": message},
    }


GREEN_MESSAGE = "feat(guards): add the rule\n\nRefs: ADR-0097\n"


def falsification_cases(workdir: pathlib.Path) -> list[FalsificationCase]:
    from guards.rules._commit_fixtures import commit_repo

    def case(name: str, expect: str, needle: str, message: str, *, env: dict[str, str] | None = None, **repo) -> FalsificationCase:
        root = commit_repo(workdir, name, **repo)
        return FalsificationCase(name, "GitCommitMsg", commit_msg_payload(root, message), expect, needle, env or {})  # type: ignore[arg-type]

    return [
        case("src-without-trailer", "deny", "without a «^Refs: (ADR-\\d{4})» trailer", "feat(x): change src\n"),
        case("src-with-trailer-and-record", "allow", "", GREEN_MESSAGE),
        case("src-with-dangling-record", "deny", "names a decision record that does not exist", "feat(x): change src\n\nRefs: ADR-9999\n"),
        case("src-with-record-in-same-commit", "allow", "", "feat(x): change src\n\nRefs: ADR-9999\n", extra_staged={"docs/decisions/9999-new.md": "# new\n"}),
        case("src-with-untracked-record", "deny", "names a decision record that does not exist", "feat(x): change src\n\nRefs: ADR-9999\n", extra_untracked={"docs/decisions/9999-new.md": "# untracked\n"}),
        case("src-with-staged-non-markdown-record", "deny", "names a decision record that does not exist", "feat(x): change src\n\nRefs: ADR-9999\n", extra_staged={"docs/decisions/9999-placeholder.txt": "not an ADR\n"}),
        case("docs-only-without-trailer", "allow", "", "docs(x): fix text\n", staged_src=False),
        case("merge-in-progress-exempt", "allow", "", "train(t-1): board alpha\n", merge=True),
        case("merge-pull-request-subject-exempt", "allow", "", "Merge pull request #7 from origin/train/t-1\n"),
        case("amend-of-src-commit-drops-trailer", "deny", "the diff is measured against HEAD~1", "chore(x): reword without refs\n", head_src=True, stage=False),
        case("amend-of-src-commit-keeps-trailer", "allow", "", "chore(x): reword\n\nRefs: ADR-0097\n", head_src=True, stage=False),
        case("amend-of-docs-commit-needs-no-trailer", "allow", "", "docs(x): reword\n", stage=False),
        case("revert-exempt", "allow", "", 'Revert "feat(x): change src"\n'),
        case("subject-form-warn", "context", "GUARD commit-subject (warn)", "Fix things in src\n\nRefs: ADR-0097\n"),
        case("subject-switch", "allow", "", "Fix things in src\n\nRefs: ADR-0097\n", env={"FACTORY_GUARD_ALLOW": SUBJECT_ID}),
        case("refs-switch", "allow", "", "feat(x): change src\n", env={"FACTORY_GUARD_ALLOW": REFS_ID}),
        case("custom-prefix-and-trailer", "deny", "touches lib/", "feat(x): change lib\n", env={SOURCE_PREFIX_VAR: "lib/", TRAILER_RE_VAR: r"^Decision: (DR-\d{3})"}, extra_staged={"lib/y.py": "Y = 1\n"}, staged_src=False),
    ]
