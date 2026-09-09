---
description: Declarative learning recipes and retrospective experiment evidence.
scope: learning experiment index
status: experimental
last_update: 2026-09-09
document_class: artifact
---

# Learning experiment records

Use the [method](../../../docs/experiments.md) and [trainer guide](../../../src/qi/learning/README.md)
for new experiments. JSON recipes here can be previewed with `qi learn run --config`.
The historical recipes reconstruct settings, not the original implementation.
Their prepared datasets and weights are local, ignored artifacts; a fresh clone
alone cannot rerun them. Dataset paths in recipes resolve relative to the config file.

| Experiment | Recipe / retrospective record | Original local evidence |
| --- | --- | --- |
| Initial imitation and tiny overfit | [Record](history/smoke-v1.json) | `artifacts/learning/diagnostic-v1-report.json`, `policy-v1-report.json` |
| Nested data-size curve | [Recipe](generalization-v1.json), [record](history/generalization-v1.json) | `artifacts/learning/generalization-v1/` |
| Hyperparameter sweep | [Record](history/tuning-v1.json) | `artifacts/learning/tuning-v1/` |
| Width/orientation sweep | [Record](history/tuning-perspective-v1.json) | `artifacts/learning/tuning-perspective-v1/` |
| Locked fresh-test evaluation | [Record](history/tuning-final-test.json) | `artifacts/learning/tuning-v1/final-test-report.json` |
| Interrupted data-scaling execution | [Recipe](data-scaling-interrupted.json), [record](history/data-scaling-interrupted.json) | `artifacts/learning/data-scaling-v1/curve/` |
| Completed data-scaling execution | [Recipe](data-scaling-v1.json), [record](history/data-scaling-v1.json) | `artifacts/learning/data-scaling-v1/curve-cached/` |
| CPU/MPS benchmark | [Record](history/device-benchmark.json) | `artifacts/learning/device-benchmark/` |
| Framework comparison | [Record](history/framework-benchmark.json) | `artifacts/learning/framework-benchmark/` |
| Source-coverage feasibility (no training) | [Audit](history/source-coverage-feasibility.json), [proposed study](../../../records/work-items/items/AB-LEARN-006-source-coverage.md) | `artifacts/learning/source-coverage-investigation-v1/` |

`history/` records are explicitly retrospective, contain source links and limitations,
and are not accepted as runnable configs. Continuous tuning fits produced checkpoint
observations at multiple update counts; those observations are not independent fits.
Original smoke reports did not measure cross-entropy. Do not backfill either fact
with current runner behavior.

`legacy-scripts/` preserves byte-for-byte copies of the scripts used for the cited
studies. These are historical source material, not new supported commands. They
assume their original directory layout and dependencies and may overwrite outputs;
inspect and adapt them into a fresh experiment before executing. Production recipes
remain strict and reject unsupported prototype options.

The bounded migration script adds these projections without modifying original
runs. With local evidence available, verify them using:

```bash
uv run python scripts/migrate_learning_records.py --check
```

Existing projections must match exactly; the script refuses to overwrite a changed
record. Durable conclusions and review triggers live in the linked work items and
[campaign](../../../records/campaigns/policy-generalization.md), not inferred from
configuration compatibility.
