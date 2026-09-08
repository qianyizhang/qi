---
description: Train and deploy a small local policy that imitates teacher move choices.
scope: backlog item
status: stable
last_update: 2026-09-08
document_class: work_record
work_id: AB-LEARN-001
work_status: done
work_kind: build
added: 2026-09-08
tags: domain
depends_on: AB-TEACHER-001, AB-ENGINE-002
residual_of: none
residual_items: none
---

# AB-LEARN-001 — First learned policy

## Intent

Prove local teacher labeling, supervised training, checkpoint reload, and
teacher-free play through the existing player boundary.

## Acceptance Criteria

- Replayable labeled positions retain teacher identity and query settings.
- Source games belong to one split; duplicate model inputs and reserved
  evaluation inputs cannot cross the data boundary.
- A small CPU policy learns legal-masked move classification; no value target.
- Versioned checkpoints validate metadata and weights, report their digest, and
  fail explicitly when absent or incompatible. Inference cannot access a teacher.
- The named policy is usable through CLI, arena, and the browser catalog.
- A tiny diagnostic overfit, exact reload predictions, held-out agreement,
  latency, legal actions, and replayable paired baseline games are recorded.
- Default checks remain usable without the optional learning dependency.

## Context and Trade-offs

User accepted the policy-only, CPU-first bounded smoke recommendation. Encoding
v1 uses 14 absolute-color piece planes across 90 squares plus side to move (1261
floats); actions are source-square * 90 + destination-square (8100 logits).
A 64-unit ReLU hidden layer is intentionally small. Board and turn omit history:
the referee still adjudicates repetition and terminal states before inference.
Deduplication therefore uses board-and-turn identity, not full-history hashes.

Generated source games use seeded random legal play; train/validation membership
is assigned before sampling. The reserved corpus is embedded and all its history
prefix inputs are excluded. Generation is bounded to 16 source games, 32 plies
and 8 samples per game by default; teacher queries use explicit budgets. Training
defaults to 200 full-batch steps and a 60-second optimization deadline, CPU only,
one thread. These are pipeline diagnostics, not general strength experiments.

The optional PyTorch extra is pinned. Checkpoints contain only validated metadata
and a known architecture's state dictionary, loaded on CPU with weights-only
deserialization. QI_POLICY_CHECKPOINT explicitly configures the local process;
the file is loaded once per resolved path and its bytes remain pinned in memory.
Restart to adopt replacement weights. HTTP never accepts filesystem paths.
All datasets, checkpoints, and match artifacts stay local and ignored.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-08 | Codex | — | wip | User authorized the proposed local learned-policy slice |
| 2026-09-08 | Codex | wip | done | Learning, reload, browser, dependency isolation, and paired replay checks passed |

## Implementation Ledger

### 2026-09-08 — decision

- Evidence: existing replay, teacher, player catalog, and paired arena already
  provide the required surrounding contracts.
- Consequence: add one policy module and one trainer module; reserve value
  learning, PUCT, accelerator support, and larger data runs for later work.
- Follow-up: verify isolation, artifact validation, and end-to-end learning.
- Review: not-required.

### 2026-09-08 — verification

- Evidence: the local pinned Pikafish run produced 96 training labels from 12
  source games and 32 validation labels from four source games. Dataset digest:
  `aaf4e6d4e2450b32f9deb91c1def34e47ec372559c3646f2dba9328513128e34`.
  Query limits were 1000 nodes and depth 3; all labeled inputs are distinct and
  disjoint from reserved opening/history-prefix inputs. Full provenance is in
  ignored artifacts/learning/smoke-v1.json.
- Evidence: the 8-example diagnostic fit achieved 8/8 agreement; loss fell from
  3.64329 to 0.00103 over 200 steps. The 96-example run achieved 96/96 training
  agreement; loss fell from 3.65221 to 0.00087 over 200 steps, using 0.64 seconds
  of the 60-second optimization allowance on this CPU. Both runs reproduced all
  train and validation predictions after checkpoint reload.
- Evidence: the full checkpoint matched 0/32 held-out teacher moves, with 32/32
  legal outputs and approximately 0.077 ms mean warm inference including masking.
  Its SHA-256 is
  `1f973a5c5f1f32a33f602d6932120d724615a1cda4595ed175f7cad2142fa14a`.
  Weights and JSON training reports remain under ignored artifacts/learning/.
- Evidence: eight paired-color games against random yielded W/D/L 0/7/1; eight
  against alpha-beta at 128 nodes and depth 2 yielded 0/4/4, both over
  qi-openings-v1 with seed 7. All 16 final outcomes were independently replayed.
  Every policy turn retained the checkpoint hash and exactly one model pass;
  there were no illegal outputs or retries. Full records are local
  artifacts/learning/policy-vs-random.json and policy-vs-alphabeta.json.
- Evidence: `make check` passed with 120 Python tests, three browser lifecycle
  unit tests, docs/lint/type/format checks, and the production build. All 24
  desktop/mobile Playwright cases passed with the real checkpoint configured;
  the mobile policy view was visually inspected. A clean environment without
  torch passed 111 tests and skipped the optional integration module; attempting
  configured policy use returned a structured learning_not_installed error.
- Consequence: local labeling, optimization, validated serialization, and
  teacher-free CLI/arena/browser play are operational. The model memorizes this
  small training set and has not demonstrated held-out imitation or strength.
  This is an engineering checkpoint, not a successful generalization result.
- Follow-up: improve the data curriculum and policy representation in a future
  experiment before drawing strength conclusions or adding policy-guided search.
- Review: not-required.
