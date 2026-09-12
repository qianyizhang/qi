---
description: Declarative learning recipes and retrospective experiment evidence.
scope: learning recipes and retained evidence
status: experimental
last_update: 2026-09-11
document_class: artifact
---

# Learning recipes and retained evidence

The [architecture surface screen](../../../records/work-items/items/AB-LEARN-016-architecture-surfaces.md)
uses study-only models and diagnostic scripts under `architecture-surfaces-v1/`.
Its frozen protocol reuses generated-data snapshots; these alternative weights
are not production policy checkpoints. The owner records execution and findings.

Cross-kind discovery: `qi experiment search "<question/topics>"` or the shared
dashboard at `/experiments`. Findings remain in the linked owning work items and
reports; this guide retains recipe and historical-format navigation.

Use the [method](../../../docs/experiments.md) and [trainer guide](../../../src/qi/learning/README.md)
for new experiments. Training recipes here can be previewed with `qi learn run --config`.
The [preparation example](preparation-two-mode-v1.json) instead runs through
`qi data prepare --config`; source-coverage protocol JSON is consumed by its study script.
The [teacher-quality protocol](teacher-quality-v1.json) uses
`scripts/run_teacher_quality.py`, with repository-relative paths; it is not a training recipe.
The [generated follow-up protocol](generated-followups-v1.json) similarly uses
`scripts/run_generated_followups.py` for `prepare`, `run` and `verify`, selecting
`--study semantic` or `--study scaling`. Its `--attempt` selects a fresh execution
directory while charging retained prior attempts. The script under
`generated-followups-v1/summarize.py` projects verified results and renders the
scaling plot (Matplotlib required only for plotting); `verify_closeout.py` audits
the complete local execution, resource accounting and sealed-input exclusion.
The historical recipes reconstruct settings, not the original implementation.
Their prepared datasets and weights are local, ignored artifacts; a fresh clone
alone cannot rerun them. Dataset paths in recipes resolve relative to the config file.

| Historical material | Recipe / retrospective record | Original local evidence |
| --- | --- | --- |
| Matched generated semantic enrichment (18 complete comparisons; three retained earlier controls) | [Protocol](generated-followups-v1.json), [results](history/generated-semantic-enrichment-v1.json), [interpretation](../../../records/work-items/items/AB-LEARN-013-semantic-enrichment.md) | `artifacts/learning/generated-followups-v1/semantic/` |
| Generated-data scaling (30 unique fits; one resource pilot) | [Protocol](generated-followups-v1.json), [results](history/generated-data-scaling-v1.json), [interpretation](../../../records/work-items/items/AB-LEARN-014-generated-data-scaling.md) | `artifacts/learning/generated-followups-v1/scaling/` |
| Controlled teacher-label student comparison (18 complete fits) | [Protocol](teacher-quality-v1.json), [results](history/teacher-quality-v1.json), [interpretation](../../../records/work-items/items/AB-LEARN-009-teacher-quality.md) | `artifacts/learning/teacher-quality-v1/` |
| Teacher budget, MultiPV/WDL, throughput and root-trace pilots | [Aggregates](history/teacher-generation-pilot-v1.json), [owning advisory](../../../records/reports/2026-09-09-teacher-generation-advisory.md) | `artifacts/pikafish-*-20260909/` |
| Initial imitation and tiny overfit | [Record](history/smoke-v1.json) | `artifacts/learning/diagnostic-v1-report.json`, `policy-v1-report.json` |
| Nested data-size curve | [Recipe](generalization-v1.json), [record](history/generalization-v1.json) | `artifacts/learning/generalization-v1/` |
| Hyperparameter sweep | [Record](history/tuning-v1.json) | `artifacts/learning/tuning-v1/` |
| Width/orientation sweep | [Record](history/tuning-perspective-v1.json) | `artifacts/learning/tuning-perspective-v1/` |
| Locked fresh-test evaluation | [Record](history/tuning-final-test.json) | `artifacts/learning/tuning-v1/final-test-report.json` |
| Interrupted data-scaling execution | [Recipe](data-scaling-interrupted.json), [record](history/data-scaling-interrupted.json) | `artifacts/learning/data-scaling-v1/curve/` |
| Completed data-scaling execution | [Recipe](data-scaling-v1.json), [record](history/data-scaling-v1.json) | `artifacts/learning/data-scaling-v1/curve-cached/` |
| CPU/MPS benchmark | [Record](history/device-benchmark.json) | `artifacts/learning/device-benchmark/` |
| Framework comparison | [Record](history/framework-benchmark.json) | `artifacts/learning/framework-benchmark/` |
| Source-coverage feasibility (no training) | [Audit](history/source-coverage-feasibility.json), [study record](../../../records/work-items/items/AB-LEARN-006-source-coverage.md) | `artifacts/learning/source-coverage-investigation-v1/` |
| Source-coverage comparison (18 complete fits) | [Results](history/source-coverage-v1.json), [interpretation](../../../records/work-items/items/AB-LEARN-006-source-coverage.md); six full recipes under `source-coverage-v1/` | `artifacts/learning/source-coverage-v1/` |
| Fresh source-coverage preparation shortfall (zero fits) | [Original protocol](source-coverage-confirmation-v1/protocol.json), [shortfall](history/source-coverage-confirmation-shortfall.json) | `artifacts/learning/source-coverage-confirmation-v1/` |
| Fresh source-coverage confirmation (18 complete fits) | [Results](history/source-coverage-confirmation-v2.json), [amended protocol](source-coverage-confirmation-v2/protocol.json), [feasibility](history/source-coverage-confirmation-feasibility.json), [work record](../../../records/work-items/items/AB-LEARN-007-fresh-source-confirmation.md); six full recipes under `source-coverage-confirmation-v2/` | `artifacts/learning/source-coverage-confirmation-v2/` |

The source-coverage recipes group three initialization seeds for each prepared
dataset. The recorded study executed the same eighteen fits individually so the
first fit could also provide timing. Its saved per-trial configs preserve the
actual allowances; replay recipes use the subsequent measured allowance.

For the fresh confirmation, `scripts/confirm_source_coverage.py` owns generation
and preparation; `scripts/run_source_coverage.py` owns profile, run and summarize.
Run these study scripts from the repository root: protocol paths are
repository-relative, unlike paths in preparation and training configs.
The amended protocol pins a full local sampler audit. Reconstruct that audit with
`scripts/audit_fresh_coverage.py --config <protocol> --output <fresh-directory>`
and compare its digest before generation. Large datasets, full input selections,
source snapshots and checkpoints remain local; the tracked compact findings
alone cannot recreate an absent artifact directory. Preserve the original
shortfall separately from the completed amended attempt.

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


## Persistent teacher preparation

[AB-DATA-004](../../../records/work-items/items/AB-DATA-004-persistent-teacher.md)
owns the measured findings, conditions and decision, discoverable as
`qi experiment show persistent-teacher-v1`. Its [compact evidence](history/persistent-teacher-v1.json)
retains timings, hashes and resolved settings. Raw runs and executed-source copies
remain under `artifacts/learning/persistent-teacher-v1/`; the reproduction script
is `scripts/check_persistent_teacher.py`.
