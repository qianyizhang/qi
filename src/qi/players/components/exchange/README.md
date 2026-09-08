---
description: A Xiangqi-aware static exchange heuristic for move ordering.
scope: static exchange evaluation
status: stable
last_update: 2026-09-08
document_class: coordination
---

# SEE: what might this capture really win?

**Static exchange evaluation** estimates a capture followed by recaptures on the
same square. For example, the opening cannon capture `b2b9` wins a 400-point horse,
then loses the 450-point cannon to `a9b9`: estimated net gain **-50**.

`estimate(board, side, move, budget)` applies the initial legal capture, finds the
least valuable legal recapturer, and repeats on that square. Each side may stop
its exchange estimate: `max(0, captured_value - reply)`. Recapture legality is
recomputed after every move, so changing cannon screens, horse legs, and king pins
matter. Equal-value attackers use coordinate order. Quiet moves return zero.

This is an approximation: it follows one least-valuable recapture sequence,
ignores threats elsewhere, and optional stopping is not a legal pass while in
check. Therefore it **only orders moves**, never prunes a move or declares an
outcome. `alphabeta-see` uses it to put estimated losing captures last.

Every simulated capture charges one shared node before moving; interrupted
analysis aborts the current search iteration. `see_nodes` includes all such work.
Legal move generation is comparatively expensive, so this readable implementation
can cost more than the pruning it enables. Tests cover the opening exchange,
a disappearing cannon screen, pinned recapturers, illegal input, and hard limits.
