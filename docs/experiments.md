---
description: Minimal method for comparable experiments and durable learning.
scope: experiment methodology
status: stable
last_update: 2026-09-21
document_class: coordination
---

# Experiments

Organize around a question, an experiment that tests it, and concrete executions.
A parameter sweep is one experiment; an interrupted execution and its rerun remain
separate runs. Configs describe intended work; results describe observed work.

## Before proposing

Use the [`experiment` skill](../.codex/skills/experiment/SKILL.md) for experimental
ideas, prior-result questions and authorized experiment work. The shared dashboard
at `/experiments` and `qi experiment search` read the same catalog, including
teacher pilots without supported search manifests.

Search question terms and aliases, read matching owners and their evidence, then
state: **prior finding and limits → overlap → new contribution**. Link the prior
experiment IDs and describe whether the idea extends, reproduces, challenges or
uses them. Do this before ranking new work or grilling protocol choices. Search
owner prose with `rg` and the [historical index](../data/experiments/learning/README.md)
when matches are absent or coverage is uncertain. Empty results do not establish
novelty. Newly found historical work should be registered retrospectively in its
owner, preserving unknowns and original evidence.

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
Update its catalog entry in the same owner using the
[recording commands](../src/qi/experiments/README.md#shared-catalog-and-recording).
A final conclusion needs finding, conditions, limitations, decision, revisit
trigger and evidence paths; keep failed and incomplete attempts in the execution
history. Append corrections as new revisions identifying affected evidence;
never erase the earlier finding or infer success from runner completion.
Run `qi experiment check-catalog` and confirm the updated entry is discoverable.

Use work items for experiment history, a bounded Campaign for current understanding
across experiments, and module guides/ADRs for adopted behavior and decisions.
The [policy-generalization campaign](../records/campaigns/policy-generalization.md)
links the current learning evidence without duplicating its detailed results.

## Configs and runs

### Retained source and current tools

Supported application/tooling imports follow the current package owners.
Retained study code under `data/experiments/` may instead pin its own source
bytes or a complete historical tree. This includes legacy learning scripts,
the architecture-surface study and its diagnostics, and frozen move-generation
timing/game controllers. Preserve those files and the original run artifacts;
changing an import can invalidate a recorded source hash or select a different
engine for a historical timing comparison.

Reproduce such a study with its recorded revision or archived source tree and
matching lock, plus the retained inputs. The last pre-extraction checkout is not
a universal reproduction environment: studies can require earlier exact bytes.
Do not run historical scripts against HEAD merely because they still exist here.
For a new experiment, adapt the useful logic into a separately identified task
with current imports, fresh outputs and explicit source lineage. No old runtime
API shims are provided. The [game package guide](../packages/qi-game/README.md)
owns current referee imports; the [historical index](../data/experiments/learning/README.md)
routes retained learning evidence.

### Agent execution and integration

Within an authorized task's owned paths, frozen evaluator and budget, agents may
develop candidates, execute comparisons, retain failures, select a feasible winner
and prepare a tested integration change. Ranking alone does not change shared
defaults. Automatic integration may be authorized for a bounded experiment; reuse
that authorization rather than asking again. Candidate work cannot silently alter
its governing evaluator, shared contracts or budget.

The accepted generalization is a minimal local task/run/evaluation envelope over
functions or scripts, adapting existing runners and catalog. Domain runners retain
their configuration, correctness, recovery and evidence semantics. Begin inside qi;
add general machinery only after useful tasks demonstrate a need. This boundary
is accepted under [AB-ARCH-001](../records/work-items/items/AB-ARCH-001-modular-runtime.md)
and is not yet implemented.

Recorded trials will use a fresh worker process and output root per trial,
executed serially by default. Direct function calls remain available for
interactive prototypes. A persistent server may coordinate clients and jobs;
it must preserve trial identity, isolation and evidence. Workloads will determine
any shared external resource semantics; a fresh Python process alone does not
isolate those resources. Serving remains deliberately low fidelity. This
execution change is accepted but not implemented.

### Implemented training recipes

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

Keep recipes, compact findings, and necessary experiment scripts in Git. The tiny
synthetic [reference fixture](../src/qi/learning/README.md#reference-reproduction)
is also tracked and packaged so reproduction does not depend on local artifacts.
Other datasets, weights and detailed run outputs remain local under ignored `artifacts/`; they are
not backed up by Git. The [historical index](../data/experiments/learning/README.md)
records availability, reconstruction limits, and evidence paths. Historical config
projections are retrospective: unknown values stay unknown and unsupported
prototype variants are not made executable merely to standardize their format.
