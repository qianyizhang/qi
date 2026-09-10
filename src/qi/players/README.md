---
description: The pluggable player contract and a reading guide to the engine modules.
scope: player architecture and extension
status: stable
last_update: 2026-09-10
document_class: coordination
---

# Players: the learning surface

A **player** answers: “Given this game and budget, which move do I choose?”
The [glossary](../../../docs/glossary/ddd.md) owns the terminology. Search
explores continuations; an evaluator scores positions; a policy maps states to
action preferences/probabilities. Tactics and strategy describe play, not module
interfaces. Human players use the board; this package implements automated players.

Read these implementations in order:

| Module | What it teaches |
| :-- | :-- |
| [Random](random/README.md) | Seeded decisions and the legal-move boundary |
| [Alpha-beta](alphabeta/README.md) | Alternating perspectives, pruning, iterative deepening |
| [Quiescence](quiescence/README.md) | Looking beyond an exchange at the normal search horizon |
| [MCTS](mcts/README.md) | UCT exploration, random rollouts, value backup, and root visits |
| [Search components](components/README.md) | Ordering, positional scores, exchanges, extensions, and safe caching |
| [Combined recipes](enhanced/README.md) | Assemble and compare alpha-beta ingredients |
| [Quiescent MCTS](mcts_quiescence/README.md) | Budget tactical leaf work alongside simulations |
| [Learned policy](policy/README.md) | Board encoding, legal masking, and checkpoint-backed inference |

## One extension point

An implementation exports a `Player` descriptor with `PlayerInfo` and a
`select(game, config) -> Decision` callable. `core.py` defines the interface;
`catalog.py` explicitly registers implementations (`PLAYER`, or `PLAYERS` for recipes). There is no filesystem scan,
SDK dependency, class hierarchy requirement, or arbitrary executable loading.
The training teacher remains a separate role. The explicit Pikafish player
reuses its bounded UCI transport; selecting other players never adds teacher access.

Descriptors can expose an availability predicate and legacy checkpoint hook.
Named bindings resolve resources separately from algorithm registration. Catalog
metadata hashes configured bytes without loading models or starting engines.

```python
from qi.game import Game, legal_moves
from qi.players import Decision, Player, PlayerConfig, PlayerInfo


def select(game: Game, config: PlayerConfig) -> Decision:
    return Decision(legal_moves(game.board, game.turn)[0])


PLAYER = Player(
    PlayerInfo("first-legal", "first-legal-v1", "First legal", "A tiny example.", False),
    select,
)
```

To add a player:

1. Create a subpackage with `__init__.py`, a short README, and colocated tests.
2. Export its descriptor and add it to the explicit catalog.
3. Run `make check`; compare it with another player through `qi evaluate`.

The CLI (`qi players`) and HTTP (`GET /api/players`) expose catalog metadata. The
browser fetches that metadata; selection, arena, and evaluation dispatch through
the same catalog. Adding an implementation requires no consumer-specific branch.
IDs are stable configuration keys; versions identify algorithm semantics. Change
a version when changing decisions or budget semantics. Unknown IDs fail at lookup,
not when constructing the transport-neutral `PlayerConfig` record.

`choose()` is the public boundary: it rejects terminal games, dispatches the
player, validates move legality and budget diagnostics, then attaches full-state
hash, player version, seed, and measured elapsed time.
[`validation.py`](validation.py) owns pure legality, common budget, MCTS accounting,
root-visit/value, and search-counter checks for both `Decision` and `Choice`.
Live selection, arena evaluation and search evidence call it directly. It raises
`ValueError` at the first failed invariant with a specific reason; live selection
translates that to `GameError("invalid_player_result", ...)`. Callers retain
identity, timing, protocol and replay checks, including referee transition errors.
Optional statistics are checked only when present. Validation does not execute
players, load checkpoints, prove that recorded work occurred, or repair evidence.
The referee still owns
outcomes and transitions. Callers apply the result with the returned state hash.

## Shared mechanics without a framework

`common.py` holds the existing material evaluator, deterministic move ordering,
terminal score conversion, and node counter. Alpha-beta exposes a leaf
callback and immutable `SearchOptions`; [components](components/README.md) plug
into its search loop and budget. MCTS exposes both static and budgeted leaf callbacks. No search
value cache is keyed by board alone: repetition and the ply ceiling need history.

`Decision` reports total nodes, completed ordinary depth, score, and optional
quiescence diagnostics, MCTS/search statistics, root evaluation terms, model calls,
and checkpoint identity. `Choice` adds
provenance. Learned-policy encoding and inference budgets are documented in its
module; training stays in the [trainer](../learning/README.md).
See [runtime contracts](../../../docs/baselines.md)
for serialization, seeding, and evaluation limits.


## Named player bindings

Set `QI_PLAYERS_CONFIG` to a local JSON file. Relative resource paths resolve
against that file. IDs must be unique and differ from algorithm IDs and `human`.
For example (replace paths with your local resources):

```json
{
  "schema_version": 1,
  "players": [
    {"id": "trained-a", "label": "Trained A", "implementation": "policy", "checkpoint": "models/a.pt"},
    {"id": "trained-b", "label": "Trained B", "implementation": "policy", "checkpoint": "models/b.pt"},
    {"id": "pikafish-local", "label": "Pikafish", "implementation": "pikafish", "engine": "pikafish", "network": "pikafish.nnue", "threads": 1, "hash_mb": 16}
  ]
}
```

The catalog exposes each binding's implementation/version, label, resource
fingerprints and settings. A checkpoint selector is a named entry, not a browser
file picker. `bindings.py` hashes and pins resource bytes before each execution;
changed or missing resources fail explicitly. `policy/runtime.py` caches named
models by path and verified digest. The `QI_POLICY_CHECKPOINT` convenience entry
retains its existing process-pinned default behavior.

CLI `--player`, arena participant IDs, evaluation PlayerConfig kinds and HTTP
all use the same binding boundary. Two policy IDs may therefore use different
checkpoints in a paired evaluation. Match/evaluation output uses schema version
2 when participants have bindings; valid older version-1 evidence remains
readable. `config_data()` omits newly introduced default fields from legacy
identity payloads so older experiment job IDs and evaluation digests stay valid.
Saved evidence validation never resolves the current bindings or loads models.

The [Pikafish adapter](pikafish/README.md) requires an explicit named binding.
Its `engine` diagnostics preserve native reported nodes/depth (including
overshoot), score kind/bound/perspective and fixed threads/hash. qi counters stay
zero; native work is never treated as qi charged visits. Browser controls expose
native nodes/depth/timeout, while executable/network paths and threads/hash remain
in the server file. Optional resources are not installed automatically.
