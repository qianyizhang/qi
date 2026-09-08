---
description: Setup and usage for the local qi Xiangqi game.
scope: project setup
status: stable
last_update: 2026-09-08
document_class: coordination
---

# qi

A local Xiangqi board for pass-and-play or games against pluggable local
opponents, with a Python referee, structured CLI, and portable save/replay.
Fixed evaluation batches and local Pikafish analysis support future learning work.

## Setup and play

Use Python 3.12, uv, and Node 22.12+ (verified here with Node 25.9).

```bash
make install
make check
make play
```

Open http://127.0.0.1:8000 in your browser. Share the board in pass-and-play, or
select a computer opponent and your color. The computer moves automatically on
its turn; failed requests expose a Retry opponent button.
Select a piece, then a highlighted destination. Keyboard users can focus a
square and press Enter or Space. Flip the board as desired.

Export a game to keep it; import validates the full history before replacing the
board. The browser does not autosave: refreshing starts a new game. Move-history
buttons inspect past positions without changing the live game; return to the
latest move to continue. New game offers an export opportunity before reset.

`uv run qi play --port 8001` uses another local port after `make web-build`.
The server binds to localhost. Remote multiplayer is outside this slice.

## CLI

Commands emit JSON. Snapshots are inputs to subsequent commands:

```bash
uv run qi new > game.json
uv run qi inspect --state game.json
uv run qi legal --state game.json
# Copy state_hash from inspect into HASH below.
uv run qi apply --state game.json --move b2e2 --expected-state-hash HASH > next.json
uv run qi replay --state next.json --ply 0
```

Write output to a different file from the input: shell redirection truncates an
output file before the command reads it. Errors go to stderr with nonzero status.

[Interface](docs/interface.md) owns coordinates and interchange. The HTTP schema
is served at http://127.0.0.1:8000/docs. Python, CLI, and HTTP share the same referee.
Imported snapshots start from the standard position; arbitrary setup/FEN editing
is not supported in this slice.

## Players

```bash
uv run qi players
uv run qi choose --state game.json --player alphabeta --nodes 128 --depth 2
uv run qi match --red alphabeta --black random --seed 7 > match.json
```

[Player modules and walkthroughs](src/qi/players/README.md) explain how to build
and add an implementation. [Search components](src/qi/players/components/README.md)
explain move ordering, positional evaluation, exchanges, check extensions, and
history-aware caching, with selectable single-feature and combined recipes.
[Baseline contracts](docs/baselines.md) explain search budgets, deterministic
seeds, opening snapshots, and match records. Matches run through the existing
referee. Extract a match record's nested `snapshot` to import it into the browser.
The browser discovers the player catalog and uses its suggested budgets with a
fixed seed. Original alpha-beta uses 128 nodes; quiescence uses 512. Switching opponents
keeps the current game; replay pauses computer moves until you return to live play.

Evaluate the fixed opening corpus (both player colors, with replayable games):

```bash
mkdir -p artifacts
uv run qi evaluate --corpus data/evaluation/openings-v1.json --seed 7 > artifacts/evaluation.json
```

See [baseline and evaluation contracts](docs/baselines.md) for seed pairing,
budget interpretation, and the limits of this small evaluation corpus.

Try **MCTS · UCT** in the browser opponent menu, then expand **Last computer move**
to inspect root visits and estimated returns. The [MCTS guide](src/qi/players/mcts/README.md)
explains the algorithm and its replaceable leaf evaluator. For CLI experiments:

```bash
uv run qi choose --state game.json --player mcts --nodes 512 --rollout-plies 8 --seed 7
```

Try **Alpha-beta · combined** or **MCTS · quiescence leaves** in the same menu.
Expand **Last computer move** for search work and positional score terms. To
combine ingredients yourself, start with the [composition example](src/qi/players/components/README.md).

```bash
uv run qi choose --state game.json --player alphabeta-enhanced --nodes 2048 --depth 2
uv run qi choose --state game.json --player mcts-quiescence --nodes 512 --rollout-plies 8
```

For local Pikafish analysis, see [teacher setup](docs/teacher.md). Engine and
weights remain optional local artifacts; default checks need neither.

To train the first local policy, follow the [teacher-imitation walkthrough](src/qi/learning/README.md).
It covers a bounded CPU run, checkpoint reload, held-out agreement, and arena
comparison. Set `QI_POLICY_CHECKPOINT` to expose the trained player in CLI and
browser play. `make test-learning` runs the optional hermetic learning checks.

## Rules and verification

[xiangqi-training-v1](docs/xiangqi-training-v1.md) includes king safety, legal
movement, and losses on checkmate or stalemate. Threefold repetition and 300
plies produce automatic draws; ordinary terminal outcomes take precedence.
Repeated checking/chasing has no special penalty. These are training rules,
not competitive adjudication.

`make check` runs Ruff, documentation validation, TypeScript/format checks,
Python and browser request-lifecycle unit tests, and a production browser build. `make format` applies formatting;
`make authoring-check` is a separate advisory writing check.

Browser integration tests run the production board against a local server on port
18765, with Chromium at desktop and mobile widths:

```bash
cd web
npx playwright install chromium
npm run test:e2e
```

This separate lane tests opponent turns, explicit retries, replay/export/import,
terminal states, and late responses during new-game/replay cancellation. Default
`make check` requires no browser download or listening server.

An optional independent movement check uses pyffish 0.0.90 in a separate environment:

```bash
uv venv /tmp/qi-reference
uv pip install --python /tmp/qi-reference/bin/python pyffish==0.0.90
PYTHONPATH=src /tmp/qi-reference/bin/python scripts/check_reference.py
```

This compares sampled legal moves, not repetition/chasing adjudication.
The normal checks need no external engine, model, GPU, or service.

## Direction and governance

[Project plan](docs/project.md) owns staged scope; [documentation index](docs/index.md)
routes authorities. [The playable work item](records/work-items/items/AB-GAME-001-playable-xiangqi.md)
records this slice's verification.

Copier adopted local repo-kit commit `8ac840f4a3b1`; `.copier-answers.yml` records
its baseline. Shared rules and skills remain kit-managed. Use `governance-sync`
when updating; project bindings and application code belong to qi.

## Search experiments

Plan bounded recipe comparisons, preserve partial runs, and inspect local HTML
reports with optional explored-search trees. See the
[experiment guide](src/qi/experiments/README.md) for preview, run, verify, report,
and selected-decision inspection commands.
