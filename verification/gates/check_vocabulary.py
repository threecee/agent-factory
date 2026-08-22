"""Forbidden-vocabulary lint — catches stale court/hard-line framing that a path
checker cannot see. Rules live in docs/decisions/CONSTITUTION.md. Deliberate
mentions (negations/definitions) are exempted with a trailing [allow-term] marker.
"""

from __future__ import annotations

import pathlib
import re
import sys

CONSTITUTION = pathlib.Path("docs/decisions/CONSTITUTION.md")
_SCAN = ["src", "AGENTS.md", "docs/ARCHITECTURE.md"]
_UI_SCAN = pathlib.Path("frontend/src")
_TEXT_EXTS = {".py", ".html", ".jinja", ".jinja2", ".css", ".js", ".ts", ".md"}
_SKIP_DIRS = {"__pycache__", "node_modules", "dist", ".venv"}
_ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|", re.MULTILINE)
_UI_RULES = [
    (r"Batch-avvis(?: fullført|…)|Angre hele batchen|Kunne ikke[^\n]*batch", "samlet avvisning"),
    (r"\bsemantisk recall\b", "Mer som dette"),
    (r"(?:estimert |lav |høy |· )konfidens|lavkonfidens", "sikkerhet / lav sikkerhet"),
    (r"\bKI-(?:forslag|vurdering|generert)\b", "forslag / vurdering / beskrivelse"),
    (r"\bForeslå tittel med KI\b|\bIngen modell tilgjengelig\b", "plain draft wording"),
    (r">\s*Term(?:er)?\b|aria-label=[\"']Term", "kodeord"),
    (r"\bAdmin \(innsyn\)|\bAdmin ser\b", "administrator"),
    (r"Agent \$\{turn\.agentId\}", "assistant wording"),
    (
        r'(?:data-screen-label|aria-label|label):?\s*=\s*["\'](?:Gjennomgang(?:skø)?|Leksikon)["\']'
        r'|\blabel:\s*["\'](?:Gjennomgang|Leksikon)["\']'
        r"|<h[1-6][^>]*>\s*(?:Gjennomgang(?:skø)?|Leksikon)\s*</h[1-6]>",
        "Funn / Kodeord",
    ),
]


def _without_code_comments(text: str) -> str:
    """Remove TS/JS comments before checking rendered string literals/JSX text."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"(^|\s)//.*$", r"\1", text, flags=re.MULTILINE)


def load_rules(path: pathlib.Path = CONSTITUTION) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in _ROW_RE.finditer(path.read_text(encoding="utf-8"))]


def banned_hits(text: str, rules: list[tuple[str, str]]) -> list[str]:
    hits = []
    for line in text.splitlines():
        if "[allow-term]" in line:
            continue
        for banned, use in rules:
            if re.search(banned, line, re.IGNORECASE):
                hits.append(f"{banned!r} -> {use}")
    return hits


def check_vocabulary(repo_root: pathlib.Path | None = None) -> list[str]:
    repo_root = repo_root or pathlib.Path.cwd()
    rules = load_rules(repo_root / CONSTITUTION)
    findings: list[str] = []
    targets: list[pathlib.Path] = []
    for entry in _SCAN:
        p = repo_root / entry
        if p.is_dir():
            targets += [
                f
                for f in p.rglob("*")
                if f.is_file()
                and f.suffix.lower() in _TEXT_EXTS
                and not any(part in _SKIP_DIRS for part in f.parts)
            ]
        elif p.exists():
            targets.append(p)
    for f in targets:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for hit in banned_hits(text, rules):
            findings.append(f"{f.relative_to(repo_root)}: {hit}")
    ui_root = repo_root / _UI_SCAN
    if ui_root.is_dir():
        for f in ui_root.rglob("*.tsx"):
            if f.name.endswith((".test.tsx", ".stories.tsx")):
                continue
            text = _without_code_comments(f.read_text(encoding="utf-8", errors="ignore"))
            for hit in banned_hits(text, _UI_RULES):
                findings.append(f"{f.relative_to(repo_root)}: {hit}")
    return findings


def main() -> int:
    findings = check_vocabulary()
    for f in findings:
        print(f"[framing] {f}")
    print(f"\n{len(findings)} stale-framing finding(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
