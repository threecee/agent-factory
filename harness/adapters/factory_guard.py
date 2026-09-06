#!/usr/bin/env python3
"""Hook entry for every factory guard: one entry per event; all rules live in the guards
package (``harness/guards/``); this file only routes (harness/guards.md §9).

Usage from a harness settings file: ``python3 <this file> <event>``. Works from wherever the
two directories are copied together (``harness/adapters`` + ``harness/guards``, or
``scripts/adapters`` + ``scripts/guards``); ``FACTORY_GUARD_DIR`` points at the package when
it lives elsewhere — the package directory must keep the name ``guards``.
"""

import os
import pathlib
import sys


def main(argv: list[str]) -> int:
    sys.dont_write_bytecode = True  # a hook never leaves __pycache__ in the tree it guards
    guards_dir = pathlib.Path(
        os.environ.get("FACTORY_GUARD_DIR")
        or pathlib.Path(__file__).resolve().parent.parent / "guards"
    ).resolve()
    sys.path.insert(0, str(guards_dir.parent))
    from guards.guard_dispatch import main as dispatch_main

    return dispatch_main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
