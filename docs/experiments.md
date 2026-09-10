---
description: Minimal method for comparable experiments and durable learning.
scope: experiment methodology
status: stable
last_update: 2026-09-10
document_class: coordination
---

# Experiments

Organize around a question, an experiment that tests it, and concrete executions.
A parameter sweep is one experiment; an interrupted execution and its rerun remain
separate runs. Configs describe intended work; results describe observed work.

## Before running

Record these in the experiment's existing work item:

- **Question and expectation:** prediction, reasoning, and evidence that could challenge it.
- **Comparison:** baseline, intended differences, fixed data/evaluation, seeds and metrics.
- **Budget and decision rule:** stop condition and what result would change the next action.
- **Prior evidence:** findings this extends, challenges, or attempts to reproduce.

Label exploratory selection explicitly. Lock a confirmation protocol before
inspecting its test results. Initialization-seed variation does not measure
uncertainty across training datasets. Related positions from one game are not
independent experimental repetitions.

## After running

Append observed results with denominators, variation, partial work, deviations and
evidence links. Separate observation from interpretation, name remaining limits,
and record the decision plus a concrete revisit trigger. Negative and inconclusive
results count as findings; successful execution does not imply a successful hypothesis.
Small exploratory trials can remain rows in the parent experiment's log.

Use work items for experiment history, a bounded Campaign for current understanding
across experiments, and module guides/ADRs for adopted behavior and decisions.
The [policy-generalization campaign](../records/campaigns/policy-generalization.md)
links the current learning evidence without duplicating its detailed results.

## Configs and runs

The [trainer guide](../src/qi/learning/README.md) owns executable recipe semantics.
Recipes use seven sections: data, model, objective, optimizer, training, evaluation,
and execution. Data refers to a prepared dataset; dataset generation and curriculum
composition belong to [Training Data](models.md), not to the training runner.
`qi data prepare --config` accepts a separate complete preparation config for
trajectory generation, teacher supervision and assembly; its frozen output becomes
the training config's `data.dataset`. The [Training Data guide](../src/qi/training_data/README.md)
owns this contract and a two-mode example.

Tracked recipes live in `data/experiments/learning/`. Each configured execution
saves a fully resolved recipe and a concrete config for every started trial.
Copy a saved config, change a setting, and run it into a fresh directory. Its
`origin_config` travels with the copy and becomes the new run's `derived_from`;
the manifest also records the submitted config path. This is local lineage,
not a tamper-proof audit log. Existing artifact identities remain in manifests and
checkpoints; no separate fingerprint registry is needed.
Manifests also record the Git revision and whether source/dependency files are
dirty. Commit experiment code before relying on Git for reconstruction; a dirty
run's source hash alone cannot recover uncommitted code.
Without the checkout source and dependency lockfile, source and Git identity
fields are `null`; runtime/package metadata remains available. This supports
installed-package runs without claiming a reconstructable checkout identity.

Compare intended variables first, then check other config differences, dataset and
implementation identities, and completeness before interpreting a gain. The current
runner does not certify scientific comparability. The first named-cases × seeds
format is deliberately provisional; extend it only when a real experiment needs it.

## Corrections and preservation

Preserve original evidence. For a bug, append a correction naming affected runs,
conclusions, and replacement evidence. Recompute a broken metric from retained
outputs where possible. Training or split defects require rerunning affected
comparisons, including the baseline. A performance-only fix needs output-equivalence
evidence; previous timings remain observations of the old implementation.

Schema version 1 fixes config interpretation. Future readers must preserve that
meaning or require an explicit migration. Loading an old recipe under new code is a
new execution, not proof of historical reproduction.

Keep recipes, compact findings, and necessary experiment scripts in Git. Datasets,
weights and detailed run outputs remain local under ignored `artifacts/`; they are
not backed up by Git. The [historical index](../data/experiments/learning/README.md)
records availability, reconstruction limits, and evidence paths. Historical config
projections are retrospective: unknown values stay unknown and unsupported
prototype variants are not made executable merely to standardize their format.
