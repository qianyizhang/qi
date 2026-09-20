---
description: Independent Xiangqi contracts, referee operations, and Python reference implementation.
scope: game package
status: stable
last_update: 2026-09-21
document_class: coordination
---

# Game package

`qi-game` is a uv workspace member, imported as `qi_game`. It owns
[xiangqi-training-v1](../../docs/xiangqi-training-v1.md) execution and replay
interchange. Its only runtime dependency is Pydantic; its own development group
declares pytest and Hypothesis. It has no application, player, ML or transport
dependencies.

| Module | Responsibility |
| --- | --- |
| `core.py` | Ruleset identity, sides, outcomes and `GameError`. |
| `contracts.py` | Validated `Snapshot`, `Position` and `Result` data. |
| `referee.py` | Structural `Referee` protocol: inspect a snapshot and apply a guarded action. |
| `reference.py` | Readable Python rules, immutable `Game`, replay, and `PythonReferee`. |

Importing contracts or the protocol does not import the reference implementation,
build rule tables, or load any players. `__init__.py` has no eager exports.
The protocol deals in replay data, so a backend can use a different internal
state representation. It has no per-node callbacks, process model or RPC schema.

```python
from qi_game.contracts import Snapshot
from qi_game.referee import Referee
from qi_game.reference import PythonReferee

referee: Referee = PythonReferee()
snapshot = Snapshot()
position = referee.inspect(snapshot)
next_position = referee.apply(snapshot, "b2e2", position.state_hash)
assert snapshot.moves == []
```

The backend validates the full history before operating. Ordered legal moves,
state hashes, adjudication and error precedence follow the named ruleset.
Both successful and failed operations leave the input unchanged. Results are
fresh data objects; mutating one must not affect subsequent inspections.

The application uses this boundary for CLI inspect/legal/apply/replay and HTTP
new/inspect/apply, final player moves and session inspection. HTTP accepts an
explicit backend through `create_app(referee=...)`; normal composition selects
`PythonReferee`. Player search, match generation, data validation and session
history validation still use the Python reference directly. Backend injection
does **not** replace those loops. Native batched trajectories and player sessions
remain later slices under [the architecture decisions](../../records/work-items/items/AB-ARCH-001-modular-runtime.md).

Python research code that needs the reference representation explicitly uses
`restore(snapshot)` or `replay(tuple_of_moves)` from `qi_game.reference`. Snapshot
is data only. Old `qi.game`, game-type exports from `qi.protocol`, and
`Snapshot.game()` were removed; internal callers are migrated directly.
Saved JSON, hashes and evidence interpretations are unchanged. New execution
provenance includes package source and manifest changes.

## Development and verification

The repository lock resolves supported packages together. Use `uv sync --locked`
at the repository root for normal development. A standalone incompatible study
needs its own excluded project and lock, rather than adding conflicting versions
to this workspace. Package boundaries are not independent release promises.

From the repository root:

```bash
# Fast package checks in the development environment, without the app conftest.
uv run --locked --package qi-game pytest --confcutdir packages/qi-game packages/qi-game/src
# Build sdist -> wheel; test outside the checkout in a fresh dependency-only venv.
make test-game
# App, CLI/HTTP, evidence, frontend and game checks together.
make check
```

`make test-game` and its CI lane check the actual installed wheel with only this
package's declared runtime/test closure. They verify that qi, FastAPI, Torch and
other application dependencies are absent. Tests block forbidden imports and
require schema imports to leave the referee unloaded. A shared workspace venv
alone is not an isolation check.

The frozen `src/qi_game/fixtures/referee-v1.json` was captured before extraction
at commit `58e6143` and records hashes of its source files. It covers ten replay
positions, including a 300-ply trajectory and repetition, plus two synthetic
terminal diagrams. These diagrams test outcome precedence; they do not extend
the replay-only Snapshot format. Existing geometry-oracle and rule tests moved
with the implementation. Preserve the frozen expected values when refactoring.
