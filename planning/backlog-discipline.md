# Backlog discipline — teeth, not prose

The backlog file (or board bodies, if you keep everything on the board) is
enforced by a gate (`check_backlog.py`), not by good intentions:

- **Cited-or-stamped:** every planning document (spec, plan) must either be
  cited from a backlog row or carry a terminal `Status:` (Implemented / Done /
  Superseded / Withdrawn / Historical). An orphaned spec fails the build.
- **Closing evidence:** a row claiming DONE must cite the commit SHA or PR
  that closed it. "Done because I remember doing it" fails the build.
- **Shipped-but-open advisories:** the gate flags open rows that merged
  commits name — the nudge to flip status honestly.
- Never stamp a terminal status on work that is not terminal to silence the
  gate; cite it from a row instead. The gate exists to make the planning
  surface honest, and it will catch you lying to it. (It did.)
