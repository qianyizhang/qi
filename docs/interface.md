---
description: Shared coordinates and replay operations for local Xiangqi play.
scope: game interface
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Game interface

Files `a`–`i` run left to right from Red's view; ranks `0`–`9` run from
Red's home rank to Black's. A move concatenates source and destination, such as
`b2e2`. Uppercase pieces are Red; lowercase are Black. Piece letters are
`K A B N R C P` (general, advisor, elephant, horse, chariot, cannon, soldier).

Saved JSON contains `schema_version: 1`, `ruleset: "xiangqi-training-v1"`,
`initial_fen`, and ordered `moves`. This slice accepts the standard initial
position only. Replay reconstructs all derived state and rejects invalid history.
The snapshot is portable data, not a server session identifier.

Python owns referee operations. JSON CLI and HTTP are adapters. HTTP exposes
`POST /api/new`, `/api/inspect`, and `/api/apply`; API schemas are available at
`/docs`. Apply requires `expected_state_hash`, snapshot, and move. The hash covers
ruleset and full history, not just the board. Invalid actions return structured
errors and cannot change the input snapshot. HTTP operations are stateless;
remote multiplayer/session coordination is not implemented.

CLI stdout contains one JSON object; errors use a structured stderr object and
nonzero exit status. Save stdout to a different file from the input snapshot.
Browser exports use the same snapshot and import validates it before replacement.
Replay navigation is read-only; return to the last move to continue playing.

## Browser opponents

`GET /api/players` lists registered in-process player IDs, versions, labels,
descriptions, and browser budget defaults. The browser discovers its options here.
`POST /api/opponent` accepts snapshot, expected-state hash, registered player ID,
seed, depth, and nodes. It checks the full-history hash before search,
selects one move through the shared Python player, and returns `position` plus
`choice` diagnostics after guarded application. The operation is stateless and
cannot mutate the supplied snapshot. Terminal positions return `game_over`.

The browser request budget is bounded to depth 1–4 and 1–512 nodes; the UI uses
base seed zero and the selected catalog entry’s defaults (depth 2; 128 nodes for
original alpha-beta, 512 for quiescence). The actual seed is base plus absolute ply,
matching arena decision seeding. No executable path or external teacher is
accepted by this endpoint. Defaults are deterministic, not latency guarantees.

The UI defaults to pass-and-play and allows any catalog player, including random, alpha-beta, and quiescence,
with the human playing either color. Mode/side changes keep the live game;
if the selected computer owns the current turn it moves automatically. Human
moves are disabled on computer turns. Failure leaves the current position intact
and exposes an explicit retry; there is no automatic retry loop.

Replay pauses opponent work. Returning to the latest move resumes an opponent
turn. Starting a new game, importing, changing player controls, or navigating
history invalidates earlier requests. The browser aborts fetches and also rejects
stale results by request generation, even if a response arrives after cancellation.
Server computation may finish within its bounded node budget after browser abort.
Exports remain game-only replay snapshots; player controls and diagnostics are
not persisted. Reload defaults to a new pass-and-play game.
