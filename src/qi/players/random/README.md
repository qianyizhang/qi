---
description: How the seeded random baseline selects a legal move.
scope: random player
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Random player

ID: `random`. Version: `random-v1`.

1. Ask the referee for legal moves.
2. Put them in the shared deterministic order: captures by victim value, then
   coordinate order. Keeping this original ordering preserves seeded decisions.
3. Use a fresh Python random generator with the supplied seed to pick uniformly.

It has no lookahead or position evaluator, reports zero search nodes, and ignores
depth/node settings. Equal code, Python version, seed, and state reproduce the
move. Arena/browser callers derive the per-move seed from the absolute ply.

Start with `__init__.py` and `test_random.py`. This is the smallest example of the
[parent player contract](../README.md).
