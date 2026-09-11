---
description: Setup and usage for the local qi Xiangqi game.
scope: project setup
status: stable
last_update: 2026-09-10
document_class: coordination
---

# qi

A local Xiangqi learning lab for play, experiment reports and shared reference,
with a Python referee, structured CLI, and portable saved sessions and replay.
Fixed evaluation batches, local Pikafish supervision and optional policy training
support bounded learning experiments.

## Setup and play

Use Python 3.12, uv, and Node 22.12+ (verified here with Node 25.9).

```bash
make install
make check
make play
```

Open http://127.0.0.1:8000. Home connects **Play**, **Data**, **Learn**, **Experiments**, and **Reference**.
In Play, select Red and Black independently: Human, a search player, a trained
checkpoint, or configured Pikafish. Set each player's applicable limits, then
use Resume for automatic turns or Step for one computer move. Pause to change
future settings, then choose Apply settings. Select a piece and highlighted destination; keyboard users can
press Enter or Space. Flip the board as desired.

The active session saves locally after accepted moves and settings changes.
Refresh, navigation away from Play, and replay pause automatic play. Restore
always requires Resume; changed or missing resources require explicit selection.
Export a session to preserve player/configuration history, or export a portable
game-only snapshot. Import validates full history before replacement.

Experiments searches registered findings across teacher, learning, search, data
and performance work. Its recorded search runs also provide interactive reports
and bounded traces for compatible decisions. Export offline HTML or Markdown;
add authored commentary in the run's optional narrative.md.
Reference contains the shared bilingual glossary. See the
[interface guide](docs/interface.md) for persistence, API and job contracts.

`uv run qi play --port 8001` uses another local port after `make web-build`.
The server binds to localhost. Remote multiplayer is outside this slice.

## CLI

To check a small teacher-free CPU training run after installing the learning extra:

```bash
uv sync --locked --extra learning
uv run --locked --extra learning qi learn reference --output artifacts/reference-v1
```

This uses a bundled synthetic fixture and writes fresh training artifacts plus
`verification.json`. It checks workflow consistency against a macOS CPU baseline;
it does not measure playing strength. See the [reference guide](src/qi/learning/README.md#reference-reproduction)
for tolerances and the clean-package check.

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
The browser discovers capability-specific controls from the player catalog.
[Named bindings](src/qi/players/README.md#named-player-bindings) let each side use
its own checkpoint or engine. Settings changes preserve earlier move evidence;
returning from replay waits for explicit Resume.

Evaluate the fixed opening corpus (both player colors, with replayable games):

```bash
mkdir -p artifacts
uv run qi evaluate --corpus data/evaluation/openings-v1.json --seed 7 > artifacts/evaluation.json
```

See [baseline and evaluation contracts](docs/baselines.md) for seed pairing,
budget interpretation, and the limits of this small evaluation corpus.
For a versioned spec, saved evidence, and scores that can be recomputed later,
see the [performance evaluation protocol](docs/evaluation.md).

Try **MCTS · UCT** in the Red or Black player selector, then expand **Last computer move**
to inspect root visits and estimated returns. The [MCTS guide](src/qi/players/mcts/README.md)
explains the algorithm and its replaceable leaf evaluator. For CLI experiments:

```bash
uv run qi choose --state game.json --player mcts --nodes 512 --rollout-plies 8 --seed 7
```

Try **Alpha-beta · combined** or **MCTS · quiescence leaves** in the same selector.
Expand **Last computer move** for search work and positional score terms. To
combine ingredients yourself, start with the [composition example](src/qi/players/components/README.md).

```bash
uv run qi choose --state game.json --player alphabeta-enhanced --nodes 2048 --depth 2
uv run qi choose --state game.json --player mcts-quiescence --nodes 512 --rollout-plies 8
```

For local Pikafish analysis, see [teacher setup](docs/teacher.md). Engine and
weights remain optional local artifacts; default checks need neither.

Prepare a frozen dataset from a saved recipe:

```bash
uv run qi data prepare --config data/experiments/learning/preparation-two-mode-v1.json \
  --output artifacts/learning/my-prepared-data
```

The [Training Data guide](src/qi/training_data/README.md#commands-and-partial-work)
owns generation modes, teacher supervision, pinned inputs and partial-work behavior.
To train a local policy, follow the [teacher-imitation walkthrough](src/qi/learning/README.md).
For repeatable comparisons, use `qi learn run --config <recipe.json> --preview`,
then add `--output <fresh-directory>` to execute. Saved configs can be copied and
edited; the [recipe and evidence guide](data/experiments/learning/README.md) links retained inputs.
Use the shared [experiment catalog](#experiment-recall) to recall findings.
It covers a bounded CPU run, checkpoint reload, held-out agreement, and arena
comparison. Set `QI_POLICY_CHECKPOINT` to expose the trained player in CLI and
browser play. The walkthrough also covers fixed-split data-size experiments and
explicit `--device mps` training. `make test-learning` runs CPU learning checks;
`make test-learning-mps` explicitly checks Metal training and CPU checkpoint reload.

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
its full-kit baseline. The retention rules (`doc`, `governance`, `python`) and
`doc-hygiene-audit`, `handoff`, and `governance-sync` skill cores were selectively
synced from repo-kit `0a51b52`; the backlog lifecycle was reconciled locally.
Shared rules and skills remain kit-managed. Use `governance-sync` when updating;
project bindings and application code belong to qi.

## Experiment recall

The shared browser **Experiments** page searches registered teacher, learning,
search, data and performance studies, with findings, conditions, decisions and
evidence availability. The CLI reads the same catalog:

```bash
uv run qi experiment search "teacher quality"
uv run qi experiment show teacher-budget-20260909
```

Use the [method](docs/experiments.md) before proposing a new comparison and the
[recording commands](src/qi/experiments/README.md#shared-catalog-and-recording) to
append findings to their owning records. Unregistered work remains outside catalog
coverage; native search replay and trace viewers are available below the catalog.

## Search experiments

Plan bounded recipe comparisons, preserve partial runs, and inspect local HTML
reports with optional explored-search trees. See the
[experiment guide](src/qi/experiments/README.md) for preview, run, verify, report,
and selected-decision inspection commands.

## Review generated games

Open **Data** in the local lab to inspect generated collections, compare phase
coverage and batch counts, audit train/validation input overlap, and replay saved
games with teacher analyses. Keep a browser review shortlist with notes and export
it as JSON. Reviews do not change training eligibility.

The default source is SQLite collections under `artifacts/learning`. For an
explicit source, start the local app with `QI_COLLECTION_PATHS=/absolute/path/collection.sqlite`.
See the [interface guide](docs/interface.md#generated-game-review) for denominators,
review persistence and evidence boundaries.
