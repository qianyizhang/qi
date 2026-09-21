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
The [follow-up](../reports/2026-09-21-generation-optimization.md) removes full-state
copying from native scalar moves: matched action throughput improves 1.882x and
controlled generation 1.086x over the old native implementation. Two isolated
teacher/game workers improve verified generation throughput 1.770x, with higher
simultaneous memory use. Learning-report inference and training preparation
remain separate, unprofiled candidates.

## Unknowns

How production parallel generation should combine isolated worker collections and
own interruption/recovery; how worker count scales beyond the measured pair; and
how to improve persistence while keeping the accepted recovery contract.
Minibatch training changes the optimization recipe
and needs separate scientific evaluation.

## Frontier

The measured two-worker gain supports designing opt-in production parallel
generation, with explicit collection combination and recovery ownership before
implementation. Native scalar preparation is implemented and tested; Python stays
default. Preserve per-move durability. Diagnostic synchronization disabling is not
an adoption candidate. No production scheduler is authorized by this page.

## Work

- [Profile experiment costs](../work-items/items/AB-LEARN-008-experiment-performance.md).
- [Native and pipeline bottleneck evidence](../reports/2026-09-21-generation-bottlenecks.md).
- [Atomic native stepping](../work-items/items/AB-ARCH-008-atomic-native-step.md).
- [Two-worker generation experiment](../work-items/items/AB-DATA-009-two-worker-generation.md).
- [Persistent teacher preparation evidence](../work-items/items/AB-DATA-004-persistent-teacher.md).

Work items own execution status and acceptance criteria.

## Learning ledger

2026-09-10: captured review candidates. Separate structural suspicions from timed
evidence, and performance-only changes from changes to the learning treatment.

2026-09-21: measured generation after native integration and incremental append.
Whole-game native-loop speed does not predict per-move integration or external
teacher throughput. Existing Python/native referee phase timers charge different
work; use matched complete actions and separate unprofiled pipeline comparisons.

2026-09-21 follow-up: safe scalar preparation removes the measured native copy
cost, while teacher throughput benefits from two isolated workers. Exact combined
outputs and interrupted-worker reuse pass; the next decision concerns production
output and recovery semantics, not whether concurrency has local throughput value.

## Closeout

Close when the selected workload meets an agreed cost target, or remaining
options are explicitly deferred. Promote adopted behavior and reproducible
measurement commands to their owning module guides.
