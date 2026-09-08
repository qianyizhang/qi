---
description: An educational guide to the original material alpha-beta player.
scope: alpha-beta player
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Alpha-beta player

ID: `alphabeta`. Version: `alphabeta-material-v1`.

Imagine trying each legal move, then asking what the opponent would do in reply.
This player uses **negamax**: a position good for the opponent is bad for us, so
scores change sign when the turn changes. Terminal scores come from the referee;
nonterminal leaves use material plus a crossed-soldier bonus.

**Alpha-beta pruning** skips branches that cannot improve the current result.
Captures are tried first to help establish useful bounds. It produces the same
completed-depth result as exhaustive minimax for this evaluator and ordering.

**Iterative deepening** completes depth 1, then 2, and so on under one shared node
budget. Work spent on an unfinished iteration still counts, but cannot replace
the last completed move. If no iteration finishes, the deterministic first ordered
move is returned with depth zero and no score. This is an explicit fallback.

The normal leaf callback simply evaluates material. This creates a horizon:
if a cannon takes a horse at the final searched ply, the evaluator can celebrate
the horse without seeing the rook that takes the cannon next. The separate
[quiescence player](../quiescence/README.md) changes that leaf callback while
preserving this original baseline for comparison.

Start with `Search.visit()` and `search()` in `__init__.py`; the terminal,
budget, mate, and exhaustive-oracle tests are in `test_alphabeta.py`.
`common.py` in the parent package owns the evaluator and node counter.

```bash
uv run qi choose --state game.json --player alphabeta --depth 2 --nodes 128
```

[Parent contract and extension guide](../README.md).
