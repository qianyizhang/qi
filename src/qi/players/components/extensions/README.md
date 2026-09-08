---
description: Bounded extra search depth for checked positions.
scope: check extensions
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Check extensions: spend depth on forced replies

A checked player must answer the check, so stopping the ordinary search there can
hide an important continuation. `CheckExtensions(limit).apply(game, depth, remaining)`
adds one ply and consumes one allowance when the side to move is checked.

The allowance is an integer passed down each path. Siblings receive the same
parent remainder; one branch cannot spend another's depth. A position consumes
at most one extension on entry. The component permits 0–4 extra plies per path;
`alphabeta-checks` and the combined recipe use two.

All visited positions still consume the shared node budget. `completed_depth`
reports the ordinary iteration depth. Diagnostics count extension events across
all attempted work and the largest allowance spent along a path. Quiescence is a
separate frontier mechanism: its check evasions can continue beyond this ordinary
extension allowance, under the same global budget.

Tests compare against an exhaustive minimax oracle with the same path allowance
and check that siblings, quiet positions, and hard node limits behave correctly.
