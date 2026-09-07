---
description: Shared coordinates and replay operations for local Xiangqi play.
scope: game interface
status: stable
last_update: 2026-09-07
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
