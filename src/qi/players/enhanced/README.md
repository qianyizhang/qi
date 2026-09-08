---
description: Named alpha-beta recipes assembled from reusable components.
scope: alpha-beta recipes
status: stable
last_update: 2026-09-08
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
