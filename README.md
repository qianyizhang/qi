---
description: Setup and usage for the local qi Xiangqi game.
scope: project setup
status: stable
last_update: 2026-09-07
document_class: coordination
---

# qi

A local two-human Xiangqi board, with a Python referee, structured CLI, and
portable save/replay files. Learning engines are future work.

## Setup and play

Use Python 3.12, uv, and Node 22.12+ (verified here with Node 25.9).

```bash
make install
make check
make play
```

Open http://127.0.0.1:8000 in your browser. Both players share that board.
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

## Rules and verification

[xiangqi-training-v1](docs/xiangqi-training-v1.md) includes king safety, legal
movement, and losses on checkmate or stalemate. Threefold repetition and 300
plies produce automatic draws; ordinary terminal outcomes take precedence.
Repeated checking/chasing has no special penalty. These are training rules,
not competitive adjudication.

`make check` runs Ruff, documentation validation, TypeScript/format checks,
Python tests, and a production browser build. `make format` applies formatting;
`make authoring-check` is a separate advisory writing check.

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
