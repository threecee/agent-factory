"""Number-provenance scanner, report mode (design-note §2.4, §7 Stage 0).

A number on a product surface reads as a capability claim whether or not it has
earned one. The earlier idea — scan all of ``docs/`` and flag bare numbers —
had inverted polarity: it drowned in ~370 legitimate literature citations. §2.4
inverts it. Scan a NARROW claim surface (the places a number is read as a
product/behaviour claim) and require a POSITIVE annotation:

    [measured: <metric_id>; transfer: <verdict>]

inline with the number. ``metric_id`` ties the number to a scoreboard record
(``corpus/scoreboard.json``); ``verdict`` is that record's ``transfer_verdict``
token (§10.8) — an imported foreign-research ratio is ``source_transfer_risk``,
a genuinely corpus-measured value is ``measured_in_corpus``. A number without
the annotation is *bare*: unclear whether it is measured, imported, or invented.

Narrow surface (§2.4): ``PRODUCT.md``, ``README.md``, ``frontend/src``,
``docs/decisions``, ``config/models.yaml``.

This is Stage-0 substrate and ships in REPORT mode: it lists bare numbers and
always exits 0. It is NOT wired into ``make verify`` — flipping it to a gate is
a later step that first needs the claim surface annotated, and would be a
Makefile change this lane does not make. The ``--gate`` flag exists for that
future flip but is not invoked anywhere yet.

    python -m scripts.check_number_provenance          # report bare numbers, exit 0
    python -m scripts.check_number_provenance --gate   # exit 1 if any bare number (future)

Refs: design-note §2.4, §7, §10.8.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

# The narrow claim surface (§2.4). Directories are scanned recursively for the
# suffixes in SCAN_SUFFIXES; files are scanned as-is.
CLAIM_SURFACE: tuple[str, ...] = (
    "PRODUCT.md",
    "README.md",
    "frontend/src",
    "docs/decisions",
    "config/models.yaml",
)
SCAN_SUFFIXES = (".md", ".ts", ".tsx", ".js", ".jsx", ".yaml", ".yml")
# Test/spec/mock files are scaffolding, not the product claim surface: an
# assertion echoing UI copy ("viser 2 av 4") is not a capability claim. Excluded
# so the scanner reports numbers a reader would take as a claim, per §2.4.
_EXCLUDE_MARKERS = (".test.", ".spec.", "/__tests__/", "/__mocks__/", ".stories.")

# A positive annotation: [measured: <metric_id>; transfer: <verdict>].
ANNOTATION_RE = re.compile(
    r"\[measured:\s*(?P<metric>[A-Za-z0-9_@.\-]+)\s*;\s*transfer:\s*(?P<verdict>[a-z_]+)\s*\]"
)

# Claim-shaped numbers. Deliberately narrow: a percentage, an "N of M"/"N av M"
# fraction, an "Nx" multiplier, or a number adjacent to a retrieval-metric word.
# Bare integers and version strings are NOT claims and are not flagged.
_METRIC_WORD = r"(?:recall|precision|accuracy|auroc|aurc|auc|f1|ndcg|kendall|spearman|rho|tau)"
CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Percentage, but not a URL-encoded octet: the leading digit must not be
    # preceded by '%' or a word char (rules out "%201%2F…" and "c1%3A"), and the
    # '%' must not be followed by a word char.
    re.compile(r"(?<![%\w])\d+(?:[.,]\d+)?\s*%(?!\w)"),
    re.compile(r"\b\d{1,3}\s+(?:of|av)\s+\d{1,3}\b"),
    re.compile(r"\b\d+(?:[.,]\d+)?x\b"),
    # A metric word bound to a value: an @k form (recall@1, hit@k, MRR@10) or a
    # nearby DECIMAL (tau ≈ 0.9, precision 0.75). A metric word near a bare
    # integer is almost always an ADR reference ("recall not precision, ADR-0002")
    # and is deliberately NOT a claim.
    re.compile(_METRIC_WORD + r"@\S", re.IGNORECASE),
    re.compile(_METRIC_WORD + r"[^\n]{0,12}?\d+[.,]\d+", re.IGNORECASE),
)

# A CSS length (width: 50%, translateX(-50%), flex-basis: 33%) is not a claim.
# Stage-0 heuristic to keep frontend/src signal honest, not a full parser.
_CSS_CONTEXT_RE = re.compile(
    r"(?:width|height|top|left|right|bottom|margin|padding|flex|basis|gap|inset|"
    r"translate|translatex|translatey|scale|opacity|size|radius|offset|min|max)"
    r"[^\n]{0,20}?\d+(?:[.,]\d+)?\s*%",
    re.IGNORECASE,
)

FALLBACK_VERDICTS = (
    "measured_in_corpus",
    "source_transfer_risk",
    "unobserved_by_construction",
    "unrecoverable_from_corpus",
    "synthetic_only",
)


def declared_verdicts(repo_root: pathlib.Path) -> tuple[str, ...]:
    """The transfer-verdict token set, read from the scoreboard if present."""
    path = repo_root / "corpus" / "scoreboard.json"
    try:
        board = json.loads(path.read_text(encoding="utf-8"))
        tokens = board["record_contract"]["transfer_verdicts"]
        if isinstance(tokens, list) and tokens:
            return tuple(tokens)
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        pass
    return FALLBACK_VERDICTS


def _iter_files(repo_root: pathlib.Path) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for entry in CLAIM_SURFACE:
        p = repo_root / entry
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(
                f
                for f in sorted(p.rglob("*"))
                if f.is_file()
                and f.suffix in SCAN_SUFFIXES
                and not any(m in f.as_posix() for m in _EXCLUDE_MARKERS)
            )
    return files


def _annotation_ok(line: str, verdicts: tuple[str, ...]) -> bool:
    """True if the line carries a well-formed annotation with a known verdict."""
    return any(m.group("verdict") in verdicts for m in ANNOTATION_RE.finditer(line))


def _is_claim_line(line: str) -> bool:
    stripped = line
    # Drop CSS-length percentages so a stylesheet does not read as a claim.
    stripped = _CSS_CONTEXT_RE.sub("", stripped)
    return any(pat.search(stripped) for pat in CLAIM_PATTERNS)


def scan(repo_root: pathlib.Path) -> list[tuple[pathlib.Path, int, str]]:
    """Bare claim lines as (path, line_number, text). Report order is file order."""
    verdicts = declared_verdicts(repo_root)
    bare: list[tuple[pathlib.Path, int, str]] = []
    for path in _iter_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            if _is_claim_line(line) and not _annotation_ok(line, verdicts):
                bare.append((path.relative_to(repo_root), n, line.strip()))
    return bare


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    gate = "--gate" in argv
    repo_root = pathlib.Path.cwd()

    bare = scan(repo_root)
    print("\nnumber-provenance (narrow claim surface, §2.4):")
    print(f"  surface: {', '.join(CLAIM_SURFACE)}")
    print(f"  bare numeric claims (no [measured: …; transfer: …] annotation): {len(bare)}")

    by_file: dict[pathlib.Path, list[tuple[int, str]]] = {}
    for path, n, text in bare:
        by_file.setdefault(path, []).append((n, text))
    cap = 15
    for path, hits in by_file.items():
        print(f"  {path}: {len(hits)} bare")
        for n, text in hits[:cap]:
            snippet = text if len(text) <= 100 else text[:97] + "..."
            print(f"      {n}: {snippet}")
        if len(hits) > cap:
            print(f"      … {len(hits) - cap} more")

    if gate:
        return 1 if bare else 0
    print("  (report mode — always exit 0; Stage-0 posture per §7)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
