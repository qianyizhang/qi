---
description: Previous-best, killer, and history move ordering.
scope: move ordering
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Move ordering: find useful bounds sooner

Alpha-beta can stop exploring replies after proving that a branch cannot improve
its bound. Trying promising moves first can reach that proof with fewer visits.
The completed minimax score stays the same; ties and interrupted searches can
choose different moves.

`MoveOrdering.moves(game, ply, budget, preferred)` returns every legal move once:
previous-best hint first, captures next, then two recent quiet **killer moves**
that caused cutoffs at this ply, then quiet moves ranked by **history**. History
is a side-and-move score incremented by depth squared after quiet cutoffs, capped
at one million. Coordinates break ties. Memory lasts one decision, including its
iterative-deepening passes. “History” here is ordering experience, separate from
the referee's repetition history.

With `use_exchange=True`, [SEE](../exchange/README.md) moves estimated losing
captures behind quiet moves. Captures within a group prefer valuable victims and
cheap attackers. SEE consumes the shared budget; ordinary sorting does not.

`cutoff()` updates only quiet-move memory. The alpha-beta loop supplies completed
previous-best moves; no move is pruned by this component. Try `alphabeta-ordered`
or `alphabeta-see`. Tests cover complete legal coverage, priorities, memory, and
poisoned captures; the recipe tests compare completed scores with exhaustive minimax.
