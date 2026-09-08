---
description: Transparent handcrafted positional score terms.
scope: positional evaluation
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Positional evaluation: more than counting pieces

Equal material can hide very different positions. `breakdown(game)` returns four
signed terms; `evaluate(game)` sums them. Positive favors the side to move.

| Term | This implementation |
| :-- | :-- |
| Material | Existing piece values and crossed-soldier bonus |
| Placement | Relative-rank advancement and central-file bonuses for horses, chariots, cannons, and soldiers |
| Mobility | Two points per difference in legal-move counts |
| King safety | Six points per nearby guard/elephant, minus twelve per attacked square in the king's neighboring palace zone |

Placement uses simple formulas in `placement()` rather than an opaque table.
Mobility asks the referee about each side's legal moves. The king-zone term uses
geometric attacks, including pinned attackers; it is a rough pressure estimate.
All coefficients are hand-set and untuned. Terminal values come from the referee
before this evaluator runs in search.

Try `alphabeta-positional`. Its browser details show the four **root, before-move**
terms from the computer's perspective; they do not explain each component of a
minimax score several moves later. The combined recipe also uses these terms at
quiescence leaves. Tests cover initial balance, central horse preference, color
rotation symmetry, and perspective reversal.
