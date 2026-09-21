---
description: Investigate representative experiment costs and preserve evidence while reducing them.
scope: experiment efficiency campaign
status: experimental
last_update: 2026-09-21
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

The [generation diagnosis](../reports/2026-09-21-generation-bottlenecks.md)
measures two distinct regimes: collection writes dominate cheap controlled
generation, while external teacher search dominates the realistic policy workload.
The maintained native referee also pays for full-state copying on each move.
These are measured costs; learning-report inference and training preparation
remain separate, unprofiled candidates.

## Unknowns

Whether independent policy-generation workers improve retained throughput at
acceptable combined resource cost; whether bounded native state preparation can
retain allocation-failure atomicity; and how to improve persistence while keeping
the accepted recovery contract. Minibatch training changes the optimization recipe
and needs separate scientific evaluation.

## Frontier

For real-teacher throughput, compare two isolated workers with serial execution of
the same frozen sources before adding a scheduler. For native execution, evaluate
bounded atomic preparation instead of copying the entire repetition map. Preserve
the current per-move durability contract; diagnostic synchronization disabling is
not an adoption candidate. The report ranks these by workload. No follow-up
implementation is scheduled by this page.

## Work

- [Profile experiment costs](../work-items/items/AB-LEARN-008-experiment-performance.md).
- [Native and pipeline bottleneck evidence](../reports/2026-09-21-generation-bottlenecks.md).
- [Persistent teacher preparation evidence](../work-items/items/AB-DATA-004-persistent-teacher.md).

Work items own execution status and acceptance criteria.

## Learning ledger

2026-09-10: captured review candidates. Separate structural suspicions from timed
evidence, and performance-only changes from changes to the learning treatment.

2026-09-21: measured generation after native integration and incremental append.
Whole-game native-loop speed does not predict per-move integration or external
teacher throughput. Existing Python/native referee phase timers charge different
work; use matched complete actions and separate unprofiled pipeline comparisons.

## Closeout

Close when the selected workload meets an agreed cost target, or remaining
options are explicitly deferred. Promote adopted behavior and reproducible
measurement commands to their owning module guides.
