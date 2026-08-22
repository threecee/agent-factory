"""Release-bundle build-input stamp support (ADR-0099).

``frontend/dist`` is a local build artifact, not a committed verify gate.
``compute_stamp`` and ``write_stamp`` are used by the release-bundle builder to
bind the built assets to their frontend inputs before the SRI manifest is made.

Mechanics: hash the frontend BUILD INPUTS (every file under frontend/src/ plus
package.json, pnpm-lock.yaml, vite.config.ts and the vite HTML entry points)
into one stable digest (sha256 over the sorted "path NUL sha256(file)" lines)
and compare it against frontend/dist/.build-inputs.sha256 when the standalone
diagnostic CLI is used. Rebuilding needs node and happens in the connected build
environment; the air-gap box consumes only the completed release bundle.

Rebuild ritual on failure (run from the repo root). ORDER MATTERS — stamp
first, manifest LAST: ``--write`` writes the stamp INTO frontend/dist, and
SRI-MANIFEST.json hashes every file in dist including ``.build-inputs.sha256``.
Running the manifest before the stamp yields a manifest that omits the stamp,
which is itself a HARD failure of the SRI gate:

    cd frontend && pnpm run build && cd ..
    python -m scripts.mirror_shell_css
    python -m scripts.check_dist_fresh --write
    python -m scripts.frontend_dist_manifest
    # make release-bundle performs this complete sequence

    python -m scripts.check_dist_fresh            # verify, exit 1 on stale
    python -m scripts.check_dist_fresh --write    # regenerate the stamp
"""

from __future__ import annotations

import hashlib
import pathlib
import sys

STAMP = pathlib.Path("frontend/dist/.build-inputs.sha256")
INPUT_TREES = ("frontend/src",)
INPUT_FILES = (
    "frontend/package.json",
    "frontend/pnpm-lock.yaml",
    "frontend/vite.config.ts",
    "frontend/index.html",
    "frontend/intel.html",
    "frontend/admin.html",
)


def _is_test_file(name: str) -> bool:
    """Vitest test/spec files (``include: src/**/*.test.ts(x)``). They are NOT
    build inputs: ``vite build`` never bundles them, so a test-only edit must
    not bump the dist stamp (which would fail this gate on a change that cannot
    alter the built bundle). Matches the ``.test.`` / ``.spec.`` convention."""
    return ".test." in name or ".spec." in name


def input_files(repo_root: pathlib.Path) -> list[pathlib.Path]:
    """All build-input files, sorted by repo-relative posix path. Dotfiles
    (editor droppings like .DS_Store) and vitest test files are excluded so the
    stamp is stable and tracks only what actually feeds ``vite build``."""
    out: list[pathlib.Path] = []
    for tree in INPUT_TREES:
        root = repo_root / tree
        if root.is_dir():
            out.extend(
                p
                for p in root.rglob("*")
                if p.is_file()
                and not any(part.startswith(".") for part in p.relative_to(root).parts)
                and not _is_test_file(p.name)
            )
    for f in INPUT_FILES:
        p = repo_root / f
        if p.is_file():
            out.append(p)
    return sorted(out, key=lambda p: p.relative_to(repo_root).as_posix())


def compute_stamp(repo_root: pathlib.Path) -> str:
    """One digest over (path, content-hash) of every build input. Adding,
    removing, renaming or editing any input changes the digest."""
    h = hashlib.sha256()
    for p in input_files(repo_root):
        rel = p.relative_to(repo_root).as_posix()
        fh = hashlib.sha256(p.read_bytes()).hexdigest()
        h.update(f"{rel}\0{fh}\n".encode())
    return h.hexdigest()


def read_stamp(repo_root: pathlib.Path) -> str | None:
    path = repo_root / STAMP
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def write_stamp(repo_root: pathlib.Path) -> str:
    digest = compute_stamp(repo_root)
    path = repo_root / STAMP
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(digest + "\n", encoding="utf-8")
    return digest


def is_fresh(repo_root: pathlib.Path) -> bool:
    stamp = read_stamp(repo_root)
    return stamp is not None and stamp == compute_stamp(repo_root)


_REBUILD_HELP = """\
frontend/dist is STALE: the build inputs (frontend/src + package.json +
pnpm-lock.yaml + vite config + HTML entry points) changed after this local dist
was stamped. Build the production artifact in the connected environment:

    make release-bundle

The release builder writes the stamp before SRI-MANIFEST.json, so the manifest
covers .build-inputs.sha256. The bundle, not frontend/dist, is deployed."""


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_root = pathlib.Path.cwd()

    if "--write" in argv:
        digest = write_stamp(repo_root)
        print(f"wrote {STAMP} ({digest[:16]}..., {len(input_files(repo_root))} input files)")
        return 0

    stamp = read_stamp(repo_root)
    current = compute_stamp(repo_root)
    if stamp is None:
        print(f"[HARD] dist-fresh: missing stamp {STAMP}.")
        print(_REBUILD_HELP)
        return 1
    if stamp != current:
        print(f"[HARD] dist-fresh: stamp {stamp[:16]}... != current inputs {current[:16]}...")
        print(_REBUILD_HELP)
        return 1
    print(f"dist-fresh: OK ({current[:16]}..., {len(input_files(repo_root))} input files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
