#!/usr/bin/env python3
"""Hook entry for every factory guard: one entry per event; all rules live in the guards
package (``harness/guards/``); this file only routes (harness/guards.md §9).

Usage from a harness settings file: ``python3 <this file> <event>``. Works from wherever the
two directories are copied together (``harness/adapters`` + ``harness/guards``, or
``scripts/adapters`` + ``scripts/guards``); ``FACTORY_GUARD_DIR`` points elsewhere if needed.
"""

import os
import pathlib
import sys

GUARDS_DIR = pathlib.Path(
    os.environ.get("FACTORY_GUARD_DIR") or pathlib.Path(__file__).resolve().parent.parent / "guards"
).resolve()
sys.path.insert(0, str(GUARDS_DIR.parent))

from guards.guard_dispatch import main  # noqa: E402

raise SystemExit(main(sys.argv[1:]))
