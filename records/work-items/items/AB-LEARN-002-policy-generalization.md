---
description: Measure policy generalization across nested data sizes and fixed held-out games using CPU or MPS.
scope: backlog item
status: stable
last_update: 2026-09-08
document_class: work_record
work_id: AB-LEARN-002
work_status: done
work_kind: build
added: 2026-09-08
tags: domain
depends_on: AB-LEARN-001, AB-EVAL-002
residual_of: none
residual_items: none
---

# AB-LEARN-002 — Bounded policy generalization

## Intent

Measure whether more teacher-labeled inputs improve held-out imitation while
keeping the existing model, optimizer, teacher settings, and validation split fixed.
Record the accepted backend decision in [ADR-0003](../../../docs/adr/0003-pytorch-mps-training.md).

## Acceptance Criteria

- Explicit CPU/MPS training, synchronized timing, CPU-compatible checkpoints,
  portable default tests, and an opt-in real MPS integration lane.
- Reuse one validated dataset reserving the exact requested evaluation corpus.
  Nested source-interleaved training subsets and fixed initialization seeds keep
  comparisons controlled; validation never selects a checkpoint.
- Persist a source-identified manifest, embedded dataset, every completed trial,
  checkpoints, and a learning curve with agreement, cross-entropy, random-legal
  reference and variation across seeds. Incomplete seed groups receive no averages.
- Bound per-fit optimization and total run time; preserve partial/failure evidence
  and never overwrite an earlier run or silently shrink its requested matrix.
- Run the real 64-source-game, up-to-1024-label generation and the 96/192/384/768
  by 7/17/27 seed matrix locally, reserving search-positions-v1. Report any actual
  incompleteness or negative generalization result. Each phase allows 600 seconds;
  each fit allows 60 seconds and 200 updates.
- Repository checks and focused CPU/MPS integration checks pass.

## Context and Trade-offs

The user accepted PyTorch after benchmarking the newer release and MLX, then
requested the ADR and training pipeline. This is a data-size experiment using
random legal trajectories and the existing shallow teacher. It does not promise
strength or add model architectures, value learning, PUCT, or training services.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-08 | Codex | — | wip | User authorized the ADR and discussed generalization pipeline |
| 2026-09-08 | Codex | wip | done | CPU/MPS checks, full repository gate, and all 12 real fits verified |

## Implementation Ledger

### 2026-09-08 — decision

- Evidence: the saved baseline reproduces 96/96 training and 0/32 validation
  agreement; device benchmarks support MPS without changing frameworks.
- Consequence: extend the existing trainer and add bounded sequential experiment
  orchestration. CPU stays the default; local actual runs explicitly select MPS.
- Follow-up: verify the implementation and record the new dataset and learning curve.
- Review: not-required.

### 2026-09-08 — verification and result

- Evidence: the [trainer guide](../../../src/qi/learning/README.md) owns device,
  fixed-split learning-curve, deadline, and checkpoint behavior. The real dataset
  contains 768 training labels from 48 source games and 251 validation labels
  from 16 source games (1019 labels total). It reserves the exact current
  search-positions-v1 corpus and all its history-prefix inputs. Dataset SHA-256:
  `129d0b5a986a5df124ce8a40c4af2b5a01dac2fcc4e3cfabeb728efd56d6a118`.
- Evidence: all 12 MPS fits completed 200 updates within the allowances; total
  experiment time was 6.99 seconds, excluding the separate labeling phase.
  Nested sizes 96/192/384/768 used initialization seeds 7/17/27 and one fixed
  251-position validation split. Mean held-out agreement was respectively
  11.95%, 12.75%, 16.60%, and 20.19%; population standard deviations across seeds
  were 0.65, 1.72, 0.82, and 0.68 percentage points. Random-legal expected agreement
  was 2.67%. All training agreements were 100%.
- Interpretation: more examples improved imitation within this fixed experiment.
  Held-out cross-entropy fell from 16.765 to 10.987, but remained worse than the
  uniform-legal baseline (3.664): confidence on wrong moves is still poor. This
  is not a strength claim, and the earlier 0/32 smoke used different data.
  No checkpoint was selected by validation or activated for browser play.
- Validation: final `make check` passed with 303 Python tests, one opt-in GPU
  skip, three web lifecycle tests, lint/docs checks and the production build.
  `make test-learning-mps` passed its real Metal training/CPU reload check.
  Existing two FastAPI/Starlette deprecation warnings remain. A subprocess test
  verifies nonzero CLI exit and saved evidence on a run deadline.
- Verification: a separate artifact pass reloaded every checkpoint on CPU,
  checked exact train/validation identities, seeds, teacher-data/corpus identities,
  replayed positions, checked legal predictions and recomputed per-position losses
  and all curve aggregates. Raw data, manifests, all trial reports/checkpoints,
  `verify.py`, `verification.json`, and `summary.md` remain in ignored
  `artifacts/learning/generalization-v1/`; the source dataset is adjacent.
- Consequence: the requested controlled experiment is runnable and has completed
  with positive top-1 data-size evidence and residual overfitting/calibration limits.
- Follow-up: representation or regularization experiments require their own
  controlled comparison; none is needed to complete this pipeline slice.
- Review: local full-diff/contract review and independent artifact recomputation;
  no separate reviewer agent.
