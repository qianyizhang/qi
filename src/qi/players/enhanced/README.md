---
description: Named alpha-beta recipes assembled from reusable components.
scope: alpha-beta recipes
status: stable
last_update: 2026-09-15
document_class: coordination
---

# Alpha-beta recipes

This package exports `PLAYERS`: explicit descriptors assembled by `recipe()` from
[search components](../components/README.md). It contains no copied search loop.
The catalog registers these descriptors once for CLI, HTTP, arena, and browser.

| ID | Ingredients beyond baseline alpha-beta |
| :-- | :-- |
| `alphabeta-ordered` | Previous-best, killer, and history ordering |
| `alphabeta-positional` | Handcrafted positional evaluator |
| `alphabeta-see` | Move ordering with static exchange estimates |
| `alphabeta-checks` | Up to two check extensions per path |
| `alphabeta-tt` | A 2048-entry history-aware transposition table |
| `alphabeta-enhanced` | All five above, plus positional quiescence leaves |
| `alphabeta-lean` | Positional quiescence, ordering and TT; no SEE or check extensions |
| `alphabeta-pvs` | Lean recipe plus principal variation search |

Each version is its ID plus `-v1`. Suggested browser budget: 512 nodes, depth two.
The original `alphabeta` and `quiescence` remain separate reference players.
For controlled comparisons, change one ingredient and set explicit equal budgets:

```bash
uv run qi new > game.json
uv run qi choose --state game.json --player alphabeta-ordered --depth 2 --nodes 512
uv run qi choose --state game.json --player alphabeta-enhanced --depth 2 --nodes 2048
uv run qi evaluate --corpus data/evaluation/openings-v1.json \
  --player-a alphabeta-enhanced --player-b quiescence --nodes 512 --depth 2 --seed 7
```

SEE adds work; positional mobility adds computation per leaf; extensions and
quiescence make some branches longer. A combined player can complete fewer
iterations and be weaker at a small budget. The names describe ingredients,
not verified strength. Tests exercise component combinations against minimax,
per-decision isolation, budget interruption, and every registered recipe.

The lean/PVS variants are experimental controls in
[AB-EVAL-006](../../../../records/work-items/items/AB-EVAL-006-enhanced-potential.md).
PVS searches the first ordered move with the full alpha-beta window, then probes
later moves with a one-point window. A probe that improves alpha without reaching
beta gets a full re-search. Every probe and re-search shares the hard node budget;
an unfinished iteration cannot replace the previous completed result. Removing
extensions does not remove quiescence's complete legal check evasions.

The [September 15 study](../../../../records/reports/2026-09-15-enhanced-alpha-beta.md)
completed 72 games. PVS at 1024 visits beat enhanced at 128 visits 8–0, but lost
all 16 follow-up games against each capped Pikafish profile. The equal-budget
screen found no PVS strength advantage; these recipes remain experimental.
