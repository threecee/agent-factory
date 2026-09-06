"""BACKLOG.md truthfulness + drift check (ADR-0090, backlog-as-index).

Varde keeps `docs/design-notes/` as the DESIGN source of truth and `docs/BACKLOG.md` as the
single canonical STATUS/PRIORITY INDEX over it (ADR-0090): rather than adopting an off-repo
tracker (GitHub Projects, Jira, ...), which would split the source of truth across two systems
and reintroduce the exact drift the software-factory gates elsewhere exist to prevent. This
script is the machine check that keeps the index honest, in the same two-tier shape as
check_module_coverage.py (ADR-0089): HARD legs that are always correct and cheap, and an
ADVISORY tier that is a report, never a gate.

HARD leg 1 checks that a row's references POINT SOMEWHERE. HARD legs 2 and 3 check that a row's
CLAIMS ABOUT ITSELF ARE TRUE -- the gap a 2026-07-25 audit found, when five Now/Next rows were
describing work that had already shipped and every gate passed green throughout, because this
file had no status logic in it at all.

HARD leg 1 (dangling links -- always right, exit 1 on failure):
Every backtick-quoted `docs/....md` path cited anywhere in docs/BACKLOG.md must exist as a real
file in the tree, and every `ADR-NNNN` reference cited in docs/BACKLOG.md must name an ADR that
actually exists under docs/decisions/ (reusing check_traceability.iter_adr_paths -- the same
forward parse the ADR<->code gate already trusts). A BACKLOG row that cites a note or ADR that
is not there is always wrong: a renamed file, a typo'd ADR number, a row that outlived the thing
it pointed at. There is no legitimate reason for this half to ever be red.

HARD leg 2 (closing evidence -- a DONE row must prove it):
A row whose Status column makes a CLOSING claim (DONE / SHIPPED / MERGED / LANDED / COMPLETE --
but NOT the file's own "PARTLY CLOSED", which is by construction a partial claim) must cite
closing evidence that resolves against real git history: a commit SHA that is an ancestor of
main, or a PR number whose merge commit is reachable from main. This is HARD rather than
ratcheted because the measurement said it could be: when it was written, exactly TWO rows in a
61-row file carried a closing status and both had real verifiable evidence available, so a
ratchet baseline would have been an empty file. Everything genuinely DONE in a git repository
was done BY A COMMIT, so the requirement is always satisfiable and needs no escape hatch.

Evidence reachable from HEAD but not yet from main PASSES, with a printed note. That is
deliberate: the natural moment to mark a row DONE is inside the PR that finishes it, and
demanding main-ancestry at that moment would force a follow-up PR -- which is exactly the delay
that produced the stale rows this leg exists to prevent. The SHA becomes a main ancestor when
the PR merges, and survives because this repo merges rather than squashes.

HARD leg 3 (row `code:` anchors -- optional, but validated when present):
A row MAY carry `code:` anchors naming the code it governs, in the same `path::symbol` shape as
an ADR's `code:` front-matter and validated by literally the same function
(check_traceability.anchor_problem). If a row HAS anchors they must resolve; anchors are NOT
mandatory. Most rows are prose about intent and cannot honestly name code yet, and mandating one
per row would produce fake anchors, which is worse than none. The measurement backs the opt-in:
BACKLOG.md cites 103 backticked path-like tokens of which 46 do not resolve, because the file
legitimately uses shorthand (`timeline/build.py`, `api_v1.py`) rather than repo-relative paths.
Hard-validating every backticked token would fail on day one against 46 non-defects; an explicit
marker separates "I am naming a file precisely" from "I am gesturing at one".

HARD leg 4 (ADR number registry):
Every numbered ADR file must have an active allocation in docs/decisions/NUMBERS.md.
Duplicate allocations and missing active claims fail the gate. A claimed tree
number owned by another branch is printed as a warning and does not affect exit.

HARD leg 5 (planning-doc cited-or-flagged -- BL-LINT-A, ADVISORY->HARD 2026-07-28):
Every doc under docs/specs/, docs/plans/, docs/superpowers/specs/ and docs/superpowers/plans/
must be cited by a docs/BACKLOG.md row OR carry a terminal `Status:`
(Implemented/Done/Superseded/Withdrawn/Historical). docs/eval-proposals/ is excluded (transient
by convention, ADR-0077). This leg was built fail-closed-capable but wired ADVISORY while ~105
historical planning docs went unstamped -- see ADVISORY (c) below for why the stamping could not
be done in bulk. The one-time truth sweep (branch docs/planning-truth-sweep) stamped or cited
every one, so a ratchet baseline would now be empty and the leg is in the exit code.

ADVISORY tier (reports -- never affect the exit code):
(a) Every committed design note (docs/design-notes/*.md) that carries a forward-looking section
    SHOULD have at least one BACKLOG.md row citing it by filename. Backfilling is a
    human-reviewed incremental sweep (the "worklist, not a big-bang" posture
    check_module_coverage.py takes for its ungated-module ratchet), never a compliance exercise.
(b) SHIPPED-BUT-OPEN: a row whose ID is named by a commit reachable from main that touches code
    outside docs/, while the row itself carries no closing status. This is the INVERSE of HARD
    leg 2 and the direction that catches a row lying by staying open: BL-GJUX-A9 shipped in
    commit ffd3c48 ("... (BL-GJUX-A9)") and sat READY TO PLAN for days afterwards. Advisory
    because one commit naming a row is not proof the whole row is finished -- several commits may
    be needed and only a human can say when it is done. Its reach is limited by convention rather
    than by mechanism: it sees only rows whose commits name them. The complete fix is a
    `Backlog: BL-XXXX` commit trailer mirroring the `Refs: ADR-NNNN` trailer that already ties
    commits to ADRs (check_traceability.refs_trailers); this leg reads one today if present.
(c) SPECS/PLANS cited-or-flagged (BL-LINT-A) -- GRADUATED to HARD leg 5 on 2026-07-28; kept here
    for the rationale. The coverage advisory (a) once scanned only docs/design-notes/ (one
    hardcoded, non-recursive root), so docs/specs/, docs/plans/, docs/superpowers/specs/ and
    docs/superpowers/plans/ were structurally invisible. Those directories exist to DESCRIBE
    work, so their rule is stricter than the keyword heuristic: every doc must be cited by a
    BACKLOG row OR carry a terminal `Status:` (Implemented/Done/Superseded/Withdrawn/Historical).
    The heuristic is dropped for them because approved specs state what the system WILL BE
    ("Outcome", "Scope") and never trip Neste/Senere. docs/eval-proposals/ is excluded (transient
    by convention, ADR-0077).

    The leg was built FAIL-CLOSED-CAPABLE and wired ADVISORY until the one-time stamping of the
    ~105 historical docs the BL-LINT-A row scoped, because that stamping could not be done in
    bulk: an uncited doc is NOT necessarily historical
    (docs/specs/2026-07-08_multi-gb-ingestion-design.md was uncited with a Status of "Not built"),
    so a blanket `Status: Historical` would manufacture the very false claim these legs exist to
    catch. The docs/planning-truth-sweep did the per-doc classification instead -- Historical for
    the pre-ADR-0090 corpus, Implemented/Superseded where the work verifiably shipped or was
    ratified into an ADR, and a BACKLOG citation for the docs that describe still-live work -- so
    the leg is now in the exit code (HARD leg 5).

    python -m scripts.check_backlog             # hard legs (exit reflects them) + advisory report
    python -m scripts.check_backlog --report     # same output, always exit 0 (report-only mode)

Refs: ADR-0090
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
from typing import NamedTuple

from scripts import check_traceability
from scripts.check_migration_heads import (
    NUMBERS_PATH,
    _duplicate_problems,
    _missing_claim_message,
    _registry_warnings,
    landed_claim_problems,
    migration_registry_counts,
    parse_number_registry,
)

BACKLOG_PATH = pathlib.Path("docs/BACKLOG.md")
DESIGN_NOTES_DIR = pathlib.Path("docs/design-notes")
ADR_DIR = pathlib.Path("docs/decisions")
_ACTIVE_REGISTRY_STATUSES = {"claimed", "landed"}

# Scan roots for the coverage advisory (BL-LINT-A). Each root carries a POLICY:
#   HEURISTIC        -- a note is reported only when it has a forward-looking keyword section
#                       (Neste/Senere/Next/...) AND no BACKLOG row cites it. Right for
#                       design-notes, which use those words and mostly carry no Status field.
#   CITED_OR_FLAGGED -- every doc must be cited by a BACKLOG row OR carry a terminal Status.
#                       Right for specs/plans, which exist to describe work and whose approved
#                       members state what the system WILL BE and so never trip the heuristic.
# docs/eval-proposals/ is deliberately NOT a root: it is transient by convention (ADR-0077,
# each proposal is deleted on promotion) and gates nothing.
HEURISTIC = "heuristic"
CITED_OR_FLAGGED = "cited_or_flagged"


class ScanRoot(NamedTuple):
    path: pathlib.Path
    policy: str


SCAN_ROOTS: tuple[ScanRoot, ...] = (
    ScanRoot(DESIGN_NOTES_DIR, HEURISTIC),
    ScanRoot(pathlib.Path("docs/specs"), CITED_OR_FLAGGED),
    ScanRoot(pathlib.Path("docs/plans"), CITED_OR_FLAGGED),
    ScanRoot(pathlib.Path("docs/superpowers/specs"), CITED_OR_FLAGGED),
    ScanRoot(pathlib.Path("docs/superpowers/plans"), CITED_OR_FLAGGED),
)

# A terminal Status exempts a cited-or-flagged doc: it describes settled work and needs no live
# BACKLOG row. Fail-closed -- draft / approved / ready / "godkjent design" are NOT terminal, so
# a missing or in-progress status is a finding. The value is matched as a whole word, so
# "Superseded by ADR-0095" counts.
_TERMINAL_STATUSES = frozenset({"implemented", "done", "superseded", "withdrawn", "historical"})
# A `Status:` line: frontmatter `status:`, a bold `**Status:**`, or a blockquoted `> Status:`.
# The rest of the line after the colon is the status value.
_STATUS_LINE_RE = re.compile(
    r"^[>\s]*\*{0,2}\s*status\s*\*{0,2}\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE
)

_DOC_LINK_RE = re.compile(r"`(docs/[\w./-]+\.md)`")
_ADR_REF_RE = re.compile(r"ADR-(\d{3,4})")

# The forward-looking vocabulary named in the process decision: a heading (any level) or a
# bold lead-in line naming one of these words marks a note's "forward-looking section". Word
# boundaries matter: Norwegian words like "flater"/"relaterte" contain "later" as a bare
# substring and must NOT match.
_FORWARD_KEYWORDS = r"(?:neste|senere|next|later|follow-?up|oppfølging|deferred|pending)"
_FORWARD_HEADER_RE = re.compile(
    rf"^#{{1,6}}[ \t].*\b{_FORWARD_KEYWORDS}\b", re.IGNORECASE | re.MULTILINE
)
_FORWARD_BOLD_RE = re.compile(
    rf"^[ \t]*\*\*[^*\n]*\b{_FORWARD_KEYWORDS}\b[^*\n]*\*\*", re.IGNORECASE | re.MULTILINE
)

# A canonical backlog row is a markdown TABLE row -- the shape docs/BACKLOG.md documents under
# "Canonical backlog row format". Prose bullets elsewhere in the file are deliberately out of
# scope: they are historical narrative, not the format new work is recorded in.
_TABLE_SEP_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_ROW_ID_RE = re.compile(r"^`?([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)`?$")

# A CLOSING status claim. "CLOSED" counts, but not the file's own "PARTLY CLOSED", which is an
# explicit partial claim. Case-insensitive, so a lowercase "done" cannot slip past.
_CLOSING_RE = re.compile(
    r"\b(?:DONE|SHIPPED|MERGED|LANDED|COMPLETED?|(?<!PARTLY )CLOSED)\b", re.IGNORECASE
)
# An explicitly PARTIAL claim. Not a closing claim (so leg 2 does not demand evidence for the
# whole row), but it does mean shipped commits naming the row are expected, not a finding.
_PARTIAL_RE = re.compile(r"\bPARTLY\b", re.IGNORECASE)

_PR_RE = re.compile(r"#(\d{1,6})\b")
_SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b")

# `code:` anchors on a row. The marker is BOLD (`**code:**`) precisely so it cannot collide with
# ordinary prose: rows legitimately write "re-verified against harness code: `run_all.py`", and
# a bare `code:` marker read that as an anchor declaration. Bolding makes the declaration
# deliberate, and it reads as a label in the rendered table.
_CODE_ANCHOR_RE = re.compile(r"\*\*code:\*\*\s*((?:`[^`\n]+`\s*,?\s*)+)")
_BACKTICKED_RE = re.compile(r"`([^`\n]+)`")
_ANCHOR_SHAPE_RE = re.compile(r"^[A-Za-z0-9_./-]+\.[A-Za-z0-9]+(?:::[A-Za-z_][A-Za-z0-9_]*)?$")

# Ref candidates for "is this in the shipped history", in preference order. A CI checkout may
# hold only the remote-tracking ref; verify.yml uses fetch-depth: 0, so one of these resolves.
_MAIN_REF_CANDIDATES = ("main", "origin/main", "refs/remotes/origin/main")


class Row(NamedTuple):
    """One canonical backlog table row."""

    row_id: str
    status: str
    text: str
    line: int


def _read(repo_root: pathlib.Path, rel: pathlib.Path) -> str:
    return (repo_root / rel).read_text(encoding="utf-8")


def doc_links(text: str) -> list[str]:
    """Every backtick-quoted repo-relative `docs/....md` path cited in `text`, deduped+sorted."""
    return sorted(set(_DOC_LINK_RE.findall(text)))


def adr_refs(text: str) -> list[str]:
    """Every `ADR-NNNN` id cited in `text`, normalised to 4 digits, deduped+sorted."""
    return sorted({f"ADR-{int(n):04d}" for n in _ADR_REF_RE.findall(text)})


def strip_fences(text: str) -> str:
    """Remove fenced Markdown code blocks, including their delimiter lines."""
    kept: list[str] = []
    fence: tuple[str, int] | None = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence is None and marker:
            fence = (marker.group(1)[0], len(marker.group(1)))
        elif fence and re.match(rf"^\s*{re.escape(fence[0])}{{{fence[1]},}}\s*$", line):
            fence = None
        elif fence is None:
            kept.append(line)
    return "".join(kept)


def known_adr_ids(repo_root: pathlib.Path) -> set[str]:
    """ADR ids that exist under docs/decisions/, keyed by each filename's numeric prefix (the
    same normalisation check_traceability uses for its own ADR-NNNN backref scan)."""
    ids: set[str] = set()
    for path in check_traceability.iter_adr_paths(repo_root / ADR_DIR):
        m = re.match(r"(\d{3,4})", path.name)
        if m:
            ids.add(f"ADR-{int(m.group(1)):04d}")
    return ids


def docs_adr_reference_problems(
    repo_root: pathlib.Path | None = None,
) -> tuple[list[str], int, int]:
    """Dangling ADR refs in Markdown under docs/** except BACKLOG, plus scan counts."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    known = known_adr_ids(repo_root)
    problems: list[str] = []
    file_count = 0
    citation_count = 0
    for path in sorted(repo_root.glob("docs/**/*.md")):
        rel = path.relative_to(repo_root)
        if rel in {BACKLOG_PATH, NUMBERS_PATH}:
            continue
        file_count += 1
        text = strip_fences(path.read_text(encoding="utf-8"))
        refs = adr_refs(text)
        citation_count += len(refs)
        for adr_id in refs:
            if adr_id not in known:
                problems.append(
                    f"dangling ADR reference: {adr_id} cited in {rel} but no such ADR "
                    f"under {ADR_DIR}"
                )
    return problems, file_count, citation_count


def dangling_links(repo_root: pathlib.Path | None = None) -> list[str]:
    """HARD leg 1: BACKLOG.md doc/ADR references that don't resolve. Empty list = clean."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    text = _read(repo_root, BACKLOG_PATH)
    problems: list[str] = []
    for rel in doc_links(text):
        if not (repo_root / rel).is_file():
            problems.append(f"dangling doc link: `{rel}` cited in {BACKLOG_PATH} but no such file")
    known = known_adr_ids(repo_root)
    for adr_id in adr_refs(text):
        if adr_id not in known:
            problems.append(
                f"dangling ADR reference: {adr_id} cited in {BACKLOG_PATH} but no such ADR "
                f"under {ADR_DIR}"
            )
    return problems


def _adr_files(repo_root: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    files: list[tuple[str, pathlib.Path]] = []
    for path in check_traceability.iter_adr_paths(repo_root / ADR_DIR):
        match = re.match(r"(\d{3,4})", path.name)
        if match:
            files.append((f"{int(match.group(1)):04d}", path.relative_to(repo_root)))
    return files


def adr_registry_problems(repo_root: pathlib.Path | None = None) -> list[str]:
    """Hard ADR registry findings. Future claims without tree files are valid."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    try:
        rows = parse_number_registry(repo_root)
    except FileNotFoundError:
        return [f"missing required number allocation ledger: {NUMBERS_PATH}"]
    problems = _duplicate_problems(rows, "adr")
    active = {
        row.number for row in rows if row.kind == "adr" and row.status in _ACTIVE_REGISTRY_STATUSES
    }
    tree_files = _adr_files(repo_root)
    for number, path in tree_files:
        if number not in active:
            problems.append(_missing_claim_message("adr", number, path))
    # The drift leg (M-8, deviation two in gates/README.md): a claimed ADR number whose file
    # is already on the default branch must be flipped; silent on a lane branch.
    problems += landed_claim_problems(repo_root, rows, "adr", tree_files)
    return problems


def adr_registry_warnings(repo_root: pathlib.Path | None = None) -> list[str]:
    """Non-failing cross-branch ownership warnings for ADR claims."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    try:
        rows = parse_number_registry(repo_root)
    except FileNotFoundError:
        return []
    return _registry_warnings(
        repo_root, rows, "adr", {number for number, _path in _adr_files(repo_root)}
    )


def adr_registry_counts(repo_root: pathlib.Path | None = None) -> tuple[int, int]:
    """(active registered ADR numbers, numbered ADR files checked)."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    try:
        rows = parse_number_registry(repo_root)
    except FileNotFoundError:
        rows = []
    registered = {
        row.number for row in rows if row.kind == "adr" and row.status in _ACTIVE_REGISTRY_STATUSES
    }
    return len(registered), len(_adr_files(repo_root))


# ---------------------------------------------------------------------------
# Row parsing (shared by both new HARD legs and the shipped-but-open advisory)
# ---------------------------------------------------------------------------


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _row_columns(header: list[str]) -> tuple[int, int] | None:
    """(id column, status column) for a qualifying table header, else None.

    A table qualifies when its header carries both an `...ID` column (the file uses `ID` and
    `Theme ID`) and a `Status` column.
    """
    id_col = next((n for n, h in enumerate(header) if h.lower().endswith("id")), None)
    status_col = next((n for n, h in enumerate(header) if h.lower() == "status"), None)
    if id_col is None or status_col is None:
        return None
    return id_col, status_col


def _parse_row(line: str, lineno: int, columns: tuple[int, int]) -> Row | None:
    """One table body line as a Row, or None if its id cell is not an id-shaped token
    (`BL-V3-ADR`, `CORPUS-00`, `THEME-UXEVAL`), backticked or not."""
    id_col, status_col = columns
    cells = _cells(line)
    if len(cells) <= max(id_col, status_col):
        return None
    m = _ROW_ID_RE.match(cells[id_col])
    return Row(m.group(1), cells[status_col], line, lineno) if m else None


def iter_rows(text: str) -> list[Row]:
    """Every canonical backlog table row in `text`."""
    lines = text.splitlines()
    rows: list[Row] = []
    i = 0
    while i < len(lines) - 1:
        if not (lines[i].lstrip().startswith("|") and _TABLE_SEP_RE.match(lines[i + 1])):
            i += 1
            continue
        columns = _row_columns(_cells(lines[i]))
        j = i + 2
        while j < len(lines) and lines[j].lstrip().startswith("|"):
            row = _parse_row(lines[j], j + 1, columns) if columns else None
            if row is not None:
                rows.append(row)
            j += 1
        i = j
    return rows


def closing_rows(text: str) -> list[Row]:
    """Every row whose Status column makes a closing claim."""
    return [row for row in iter_rows(text) if is_closing_status(row.status)]


def duplicate_row_id_problems(text: str) -> list[str]:
    """The duplicate-id leg (agent-factory deviation three, 2026-09; verify-portfolio.md
    "Legs that bring lane-green closer to train-green"; mechanism M-17a): one canonical row
    per backlog id.

    Two rows with the same id let a status flip land on one copy while the other keeps
    asserting the opposite; the link-graph legs never saw it. The canonical id form is the
    parser's own (`_ROW_ID_RE`): a cell that does not match it is not a row and is not
    counted here — the shape the file declares is the shape this leg enforces.
    """
    lines_by_id: dict[str, list[int]] = {}
    for row in iter_rows(text):
        lines_by_id.setdefault(row.row_id, []).append(row.line)
    return [
        f"duplicate backlog row id `{row_id}` appears {len(lines)} times "
        f"(lines {', '.join(str(line) for line in lines)}); one row per id — merge the "
        "copies or retire the stale one"
        for row_id, lines in lines_by_id.items()
        if len(lines) > 1
    ]


def is_closing_status(status: str) -> bool:
    """True if the Status cell makes a closing claim (see _CLOSING_RE)."""
    return bool(_CLOSING_RE.search(status))


def code_anchors(row_text: str) -> list[str]:
    """The `path[::symbol]` anchors a row declares after a bold `**code:**` marker, in order.

    Only path-shaped backticked entries count, so a marker followed by prose yields nothing
    rather than a spurious anchor.
    """
    out: list[str] = []
    for group in _CODE_ANCHOR_RE.findall(row_text):
        for entry in _BACKTICKED_RE.findall(group):
            entry = entry.strip()
            if _ANCHOR_SHAPE_RE.match(entry):
                out.append(entry)
    return out


# ---------------------------------------------------------------------------
# git plumbing
# ---------------------------------------------------------------------------


def _git(repo_root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args], capture_output=True, text=True, check=False
    )


def resolve_main_ref(repo_root: pathlib.Path) -> str | None:
    """The first of main / origin/main / refs/remotes/origin/main that resolves, or None."""
    for ref in _MAIN_REF_CANDIDATES:
        if _git(repo_root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode == 0:
            return ref
    return None


def _commit_exists(repo_root: pathlib.Path, sha: str) -> bool:
    return _git(repo_root, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def _is_ancestor(repo_root: pathlib.Path, sha: str, ref: str) -> bool:
    return _git(repo_root, "merge-base", "--is-ancestor", sha, ref).returncode == 0


def merged_pr_numbers(repo_root: pathlib.Path, ref: str) -> set[int]:
    """PR numbers whose merge is reachable from `ref`, read from commit SUBJECTS only.

    GitHub writes `Merge pull request #N from ...` for a merge commit and a trailing `(#N)` for
    a squash. A bare `#N` in a commit BODY is deliberately NOT accepted: bodies routinely cite
    PRs that are still open (this repo's own history discusses #250 in commits that predate its
    merge), so scanning them would let an unmerged PR stand as proof of merge.
    """
    out = _git(repo_root, "log", ref, "--format=%s")
    numbers: set[int] = set()
    for subject in out.stdout.splitlines():
        m = re.match(r"Merge pull request #(\d+)", subject)
        if m:
            numbers.add(int(m.group(1)))
        m = re.search(r"\(#(\d+)\)\s*$", subject)
        if m:
            numbers.add(int(m.group(1)))
    return numbers


# ---------------------------------------------------------------------------
# HARD leg 2: closing evidence
# ---------------------------------------------------------------------------


def _sha_evidence(
    repo_root: pathlib.Path, row_text: str, main_ref: str | None, has_head: bool
) -> tuple[str | None, str | None, list[str], list[str]]:
    """(accepted sha, in-flight sha, rejection reasons, hex tokens that are not commits).

    A hex-shaped token that is not a commit object never rejects a row on its own: prose can
    look like a SHA, and a candidate that resolves to nothing can only fail to HELP, never
    accuse. It is still carried out, because a row that cites a WRONG sha must not be told it
    "cites no SHA at all" — that message describes a different row than the one in front of the
    reader, and sends them to add a citation they already added.
    """
    accepted: str | None = None
    in_flight: str | None = None
    tried: list[str] = []
    unresolved: list[str] = []
    for sha in dict.fromkeys(_SHA_RE.findall(row_text)):
        if not _commit_exists(repo_root, sha):
            unresolved.append(sha)
            continue
        if main_ref and _is_ancestor(repo_root, sha, main_ref):
            return sha, in_flight, tried, unresolved
        if has_head and _is_ancestor(repo_root, sha, "HEAD"):
            in_flight = in_flight or sha
        else:
            tried.append(f"commit {sha} is reachable from neither main nor HEAD")
    return accepted, in_flight, tried, unresolved


def _pr_evidence(row_text: str, merged_prs: set[int]) -> tuple[str | None, list[str]]:
    """(accepted PR number, rejection reasons) for the PR numbers a row cites."""
    tried: list[str] = []
    for pr in dict.fromkeys(_PR_RE.findall(row_text)):
        if int(pr) in merged_prs:
            return pr, tried
        tried.append(f"PR #{pr} has no merge commit reachable from main")
    return None, tried


def _no_evidence_detail(tried: list[str], unresolved: list[str]) -> str:
    """Why a closing row proved nothing, phrased so it cannot misdescribe the row itself."""
    if tried:
        return "; ".join(tried)
    if unresolved:
        return (
            f"the hex token(s) it cites ({', '.join(unresolved)}) are not commits in this "
            "repository"
        )
    return "it cites no commit SHA or PR number at all"


def _row_verdict(
    repo_root: pathlib.Path,
    row: Row,
    main_ref: str | None,
    has_head: bool,
    merged_prs: set[int],
) -> tuple[str | None, str | None]:
    """(problem, note) for ONE closing row — at most one of each, both None if it is proven."""
    accepted, in_flight, tried, unresolved = _sha_evidence(repo_root, row.text, main_ref, has_head)
    if accepted is None:
        accepted, pr_tried = _pr_evidence(row.text, merged_prs)
        tried += pr_tried
    if accepted is None and in_flight is not None:
        return None, (
            f"[note] {row.row_id} (line {row.line}) is marked closed on IN-FLIGHT evidence: "
            f"commit {in_flight} is on HEAD but not yet an ancestor of main. It becomes one "
            "when this branch merges."
        )
    if accepted is None:
        detail = _no_evidence_detail(tried, unresolved)
        return (
            f"unproven closing claim: {row.row_id} (line {row.line}) has Status "
            f"{row.status!r} but no closing evidence that resolves — {detail}. Cite the "
            "commit that closed it (`git log -1 --format=%h -- <path>`) or the merged PR "
            "number, or change the Status."
        ), None
    return None, None


def closing_evidence(
    repo_root: pathlib.Path | None = None,
) -> tuple[list[str], list[str], list[Row]]:
    """HARD leg 2. Returns (problems, notes, rows-claiming-a-closing-status).

    `problems` fail the build. `notes` record evidence that resolves against HEAD but is not yet
    an ancestor of main (in-flight work marked DONE inside the PR that finishes it), plus a
    single loud skip line if no git history is available at all.
    """
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    rows = closing_rows(_read(repo_root, BACKLOG_PATH))
    problems: list[str] = []
    notes: list[str] = []
    if not rows:
        return problems, notes, rows

    main_ref = resolve_main_ref(repo_root)
    has_head = _git(repo_root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}").returncode == 0
    if main_ref is None and not has_head:
        notes.append(
            f"[skip] closing-evidence leg: no git history under {repo_root} (no main, no "
            f"origin/main, no HEAD) — {len(rows)} closing claim(s) were NOT verified."
        )
        return problems, notes, rows

    merged_prs = merged_pr_numbers(repo_root, main_ref) if main_ref else set()

    for row in rows:
        problem, note = _row_verdict(repo_root, row, main_ref, has_head, merged_prs)
        if problem is not None:
            problems.append(problem)
        if note is not None:
            notes.append(note)
    return problems, notes, rows


# ---------------------------------------------------------------------------
# HARD leg 3: row code anchors
# ---------------------------------------------------------------------------


def anchor_problems(repo_root: pathlib.Path | None = None) -> tuple[list[str], int, int]:
    """HARD leg 3. Returns (problems, rows-carrying-anchors, total-anchor-count).

    Anchors are optional. Every anchor a row DOES declare is validated by
    check_traceability.anchor_problem — the same function that validates an ADR's `code:`
    front-matter, so the two cannot drift into meaning different things.
    """
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    problems: list[str] = []
    anchored_rows = 0
    total = 0
    for row in iter_rows(_read(repo_root, BACKLOG_PATH)):
        anchors = code_anchors(row.text)
        if not anchors:
            continue
        anchored_rows += 1
        total += len(anchors)
        for entry in anchors:
            problem = check_traceability.anchor_problem(repo_root, entry)
            if problem is not None:
                kind, detail = problem
                problems.append(
                    f"dangling row anchor ({kind}): {row.row_id} (line {row.line}) declares "
                    f"code: {detail}"
                )
    return problems, anchored_rows, total


# ---------------------------------------------------------------------------
# ADVISORY (a): design-note coverage
# ---------------------------------------------------------------------------


def has_forward_section(text: str) -> bool:
    """True if `text` carries a forward-looking heading or bold lead-in line (Neste/Senere/
    Next/Later/follow-up/deferred/pending) -- the mechanical proxy for "has open follow-up"."""
    return bool(_FORWARD_HEADER_RE.search(text) or _FORWARD_BOLD_RE.search(text))


def iter_design_notes(repo_root: pathlib.Path) -> list[pathlib.Path]:
    root = repo_root / DESIGN_NOTES_DIR
    if not root.exists():
        return []
    return sorted(root.glob("*.md"))


def notes_with_forward_work(repo_root: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in iter_design_notes(repo_root) if has_forward_section(p.read_text("utf-8"))]


def is_indexed(note: pathlib.Path, backlog_text: str) -> bool:
    """A note counts as indexed if some BACKLOG.md row cites its filename directly."""
    return note.name in backlog_text


def coverage_report(repo_root: pathlib.Path | None = None) -> tuple[list[str], int, int]:
    """(uncovered note repo-relative paths, notes-with-forward-work count, total note count).

    Returns full repo-relative paths (not bare filenames), so the caller prints where the note
    actually lives rather than a hardcoded `docs/design-notes/` prefix -- the prefix bug
    BL-LINT-A names, which would misreport any future heuristic root.
    """
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    backlog_text = _read(repo_root, BACKLOG_PATH)
    forward = notes_with_forward_work(repo_root)
    uncovered = sorted(
        str(p.relative_to(repo_root)) for p in forward if not is_indexed(p, backlog_text)
    )
    return uncovered, len(forward), len(iter_design_notes(repo_root))


# ---------------------------------------------------------------------------
# ADVISORY (c): specs/plans cited-or-flagged (BL-LINT-A)
# ---------------------------------------------------------------------------


def terminal_status(text: str) -> str | None:
    """The terminal Status keyword a doc declares (one of _TERMINAL_STATUSES), or None.

    Scans every `Status:` line for a terminal keyword as a whole word, so
    `Status: Superseded by ADR-0095` counts but `status: draft`, `Status: ready-for-execution`
    and `Status: **Godkjent design**` do not. Callers pass fenced-stripped text so a plan's
    `status_code=422` / `status: Mapped[str]` code snippets cannot read as a document status.
    """
    for match in _STATUS_LINE_RE.finditer(text):
        value = match.group(1).lower()
        for keyword in _TERMINAL_STATUSES:
            if re.search(rf"\b{keyword}\b", value):
                return keyword
    return None


def cited_or_flagged_problems(
    repo_root: pathlib.Path | None = None,
) -> tuple[list[str], int, int]:
    """HARD leg 5 (BL-LINT-A). Returns (findings, docs scanned, docs exempt-by-terminal-Status).

    For each CITED_OR_FLAGGED scan root, a doc that is neither cited by a docs/BACKLOG.md row
    nor carrying a terminal Status is a finding. Fail-closed by construction (an uncited,
    non-terminal doc is a finding); wired into the exit code by the caller as of 2026-07-28,
    once the docs/planning-truth-sweep stamped or cited the historical corpus -- see HARD leg 5
    and ADVISORY (c) in the module docstring.
    """
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    backlog_text = _read(repo_root, BACKLOG_PATH)
    findings: list[str] = []
    scanned = 0
    flagged = 0
    for root in SCAN_ROOTS:
        if root.policy != CITED_OR_FLAGGED:
            continue
        base = repo_root / root.path
        if not base.is_dir():
            continue
        for path in sorted(base.glob("*.md")):
            scanned += 1
            if path.name in backlog_text:
                continue
            if terminal_status(strip_fences(path.read_text(encoding="utf-8"))) is not None:
                flagged += 1
                continue
            rel = path.relative_to(repo_root)
            findings.append(
                f"uncited planning doc with no terminal Status: {rel} -- cite it from a "
                f"{BACKLOG_PATH} row, or stamp a terminal `Status:` "
                f"(Implemented/Done/Superseded/Withdrawn/Historical)"
            )
    return findings, scanned, flagged


# ---------------------------------------------------------------------------
# ADVISORY (b): shipped-but-open
# ---------------------------------------------------------------------------


def _ships_code(repo_root: pathlib.Path, sha: str) -> bool:
    """True if `sha` changes a file outside docs/ AND does not edit the index itself."""
    files = [
        line
        for line in _git(
            repo_root, "diff-tree", "--no-commit-id", "--name-only", "-r", sha
        ).stdout.splitlines()
        if line
    ]
    return str(BACKLOG_PATH) not in files and any(not f.startswith("docs/") for f in files)


def implementing_commits(
    repo_root: pathlib.Path, row_ids: list[str], ref: str
) -> dict[str, list[tuple[str, str]]]:
    """row id -> [(short sha, subject)] for commits reachable from `ref` that NAME the row, change
    a file outside docs/, and do NOT themselves edit this index.

    Both conditions are what keep this from being noise, and both were measured rather than
    guessed. Outside-docs/ drops pure documentation commits. Not-editing-BACKLOG.md drops index
    maintenance: the commit that CREATED this gate (4decb1d) names three rows it was adding and
    also touches scripts/, which read as three false "shipped" claims until the condition was
    added. It is also the sharper signal — a commit that ships a row's work while leaving the
    index untouched is precisely the event that leaves a row stale.
    """
    if not row_ids:
        return {}
    id_re = re.compile(r"\b(" + "|".join(re.escape(i) for i in row_ids) + r")\b")
    log = _git(repo_root, "log", ref, "--format=%H%x1f%s%x1f%B%x1e")
    found: dict[str, list[tuple[str, str]]] = {}
    qualifies: dict[str, bool] = {}
    for record in log.stdout.split("\x1e"):
        if not record.strip():
            continue
        parts = record.strip("\n").split("\x1f")
        sha, subject, body = (parts + ["", ""])[:3]
        hits = set(id_re.findall(f"{subject}\n{body}"))
        if not hits:
            continue
        if sha not in qualifies:
            qualifies[sha] = _ships_code(repo_root, sha)
        if not qualifies[sha]:
            continue
        for row_id in hits:
            found.setdefault(row_id, []).append((sha[:8], subject))
    return found


def shipped_but_open(repo_root: pathlib.Path | None = None) -> list[str]:
    """ADVISORY (b): rows a merged code commit names, that are still marked as open work."""
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    main_ref = resolve_main_ref(repo_root)
    if main_ref is None:
        return []
    rows = iter_rows(_read(repo_root, BACKLOG_PATH))
    # A PARTLY-* row already says some of its work shipped, so a commit naming it is expected
    # rather than a finding; only rows claiming to be wholly open can be stale in this sense.
    open_rows = {
        r.row_id: r
        for r in rows
        if not is_closing_status(r.status) and not _PARTIAL_RE.search(r.status)
    }
    found = implementing_commits(repo_root, sorted(open_rows), main_ref)
    out: list[str] = []
    for row_id in sorted(found):
        row = open_rows[row_id]
        sha, subject = found[row_id][0]
        extra = f" (+{len(found[row_id]) - 1} more)" if len(found[row_id]) > 1 else ""
        out.append(
            f"shipped but still open: {row_id} (line {row.line}) has Status {row.status!r}, but "
            f"{sha} on main names it and changes code outside docs/{extra}: {subject}"
        )
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    report_only = "--report" in argv
    repo_root = pathlib.Path.cwd()

    problems = dangling_links(repo_root)
    # The duplicate-id leg (M-17a) runs before the closing-evidence leg: a status flip that
    # landed on one of two copies is found by the id, not by the evidence.
    problems += duplicate_row_id_problems(_read(repo_root, BACKLOG_PATH))
    evidence_problems, evidence_notes, closing_rows = closing_evidence(repo_root)
    problems += evidence_problems
    anchor_findings, anchored_rows, anchor_count = anchor_problems(repo_root)
    problems += anchor_findings
    # Counted separately from the BACKLOG-scoped legs above, and folded in only
    # after: these findings are in OTHER files, so rolling them into the same
    # total would make the summary line below claim they are in BACKLOG.md.
    backlog_scoped_count = len(problems)
    docs_adr_problems, docs_file_count, docs_citation_count = docs_adr_reference_problems(repo_root)
    problems += docs_adr_problems
    registry_problems = adr_registry_problems(repo_root)
    problems += registry_problems
    # HARD leg 5 (BL-LINT-A). Flipped from ADVISORY to the exit code on 2026-07-28, once the
    # planning-truth-sweep stamped or cited the historical corpus. Like the docs-ADR leg these
    # findings live in OTHER files, so they fold in only after backlog_scoped_count is
    # snapshotted -- the "finding(s) in BACKLOG.md" summary must not count them.
    planning_findings, planning_scanned, planning_flagged = cited_or_flagged_problems(repo_root)
    problems += planning_findings
    for p in problems:
        print(f"[HARD] {p}")
    for warning in adr_registry_warnings(repo_root):
        print(f"[WARN] {warning}")
    for note in evidence_notes:
        print(note)

    uncovered, forward_count, total_count = coverage_report(repo_root)
    for rel in uncovered:
        print(f"[ADVISORY] design note not yet indexed in {BACKLOG_PATH}: {rel}")
    stale = shipped_but_open(repo_root)
    for line in stale:
        print(f"[ADVISORY] {line}")

    migration_registered, migration_checked = migration_registry_counts(repo_root)
    adr_registered, adr_checked = adr_registry_counts(repo_root)
    print(
        f"\nbacklog hard legs: {backlog_scoped_count} finding(s) in {BACKLOG_PATH}; "
        f"{len(closing_rows)} row(s) claim a closing status, {anchored_rows} row(s) carry "
        f"{anchor_count} code anchor(s)."
        f"\ndocs ADR references: {docs_citation_count} citation(s) across "
        f"{docs_file_count} Markdown file(s) under docs/** excluding {BACKLOG_PATH}; "
        f"{len(docs_adr_problems)} dangling."
        f"\nnumber registry: {migration_registered} migration / {adr_registered} adr number(s) "
        f"registered; {migration_checked} migration / {adr_checked} adr tree file(s) checked; "
        f"{len(registry_problems)} problem(s)."
        f"\nbacklog coverage: {forward_count} of {total_count} committed design notes carry a "
        f"forward-looking section; {len(uncovered)} not yet cited by a {BACKLOG_PATH} row; "
        f"{len(stale)} open row(s) named by a merged code commit."
        f"\nplanning docs (specs/plans cited-or-flagged): {planning_scanned} scanned, "
        f"{planning_flagged} exempt via terminal Status, {len(planning_findings)} neither cited "
        f"nor stamped (HARD -- fails the build; the BL-LINT-A stamping sweep landed 2026-07-28)."
    )
    return 0 if report_only else (1 if problems else 0)


if __name__ == "__main__":
    sys.exit(main())
