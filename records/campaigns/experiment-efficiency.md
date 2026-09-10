---
description: Investigate representative experiment costs and preserve evidence while reducing them.
scope: experiment efficiency campaign
status: experimental
last_update: 2026-09-10
document_class: coordination
---

# Experiment efficiency

## Destination

Make representative local experiments cheaper to repeat without changing their
data, player behavior, metrics or completeness claims.

## Model relationship

[Training Data](../../src/qi/training_data/README.md) owns preparation and frozen
datasets; the [trainer](../../src/qi/learning/README.md) owns fitting and reports.
Each owner retains its evidence checks. Follow the [experiment method](../../docs/experiments.md).

## Current understanding

Cumulative generation checkpoints revisit and serialize growing source libraries.
Learning reports perform repeated inference and compute full-dataset metrics.
These are candidate costs, not measured dominant bottlenecks. Persistent teacher
sessions already exist; their recorded pilot does not establish end-to-end gains
for every preparation workload.

## Unknowns

Representative phase timings, peak memory and scaling; safe reuse boundaries;
whether checkpoint cadence, storage layout or report computation merits the first
change. Minibatch training changes the optimization recipe and needs separate
scientific evaluation.

## Frontier

Select one bounded representative workload, preserve its inputs and outputs, and
profile it before choosing an optimization. Consider prepared-input reuse,
checkpoint cadence or sharding, and chunked metrics only where measurements
justify them. No experiment or performance change is scheduled by this page.

## Work

- [Profile experiment costs](../work-items/items/AB-LEARN-008-experiment-performance.md).
- [Persistent teacher preparation evidence](../work-items/items/AB-DATA-004-persistent-teacher.md).

Work items own execution status and acceptance criteria.

## Learning ledger

2026-09-10: captured review candidates. Separate structural suspicions from timed
evidence, and performance-only changes from changes to the learning treatment.

## Closeout

Close when the selected workload meets an agreed cost target, or remaining
options are explicitly deferred. Promote adopted behavior and reproducible
measurement commands to their owning module guides.
