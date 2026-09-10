---
description: Explicit local Pikafish participant using pinned resources and engine-native diagnostics.
scope: external player adapter
status: stable
last_update: 2026-09-10
document_class: coordination
---

# Pikafish player

The implementation ID is pikafish, version pikafish-uci-v1. Select a named
server-configured binding; the bare implementation has no default executable.
The adapter reuses the local UCI teacher transport and sends full move history.
The referee validates the proposed move and owns all outcomes.

The binding pins executable/network fingerprints, threads and hash memory.
Requested nodes/depth and the protocol timeout are per-decision settings.
Returned engine diagnostics preserve native work, cp/mate scores, perspective
and bounds; unavailable counters stay null and reported overshoot is retained.
The common qi work counters remain zero because this adapter performs no qi
search. A timeout, missing resource or illegal move fails explicitly.

Each decision owns and closes its UCI process. Persistent engine pooling is not
part of this adapter. Other participants receive no teacher access.
