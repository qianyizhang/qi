---
name: experiment
version: "1.0.0"
description: >-
  Recall prior experiment findings, compare proposed work, and record evidence-linked
  conclusions. Use for experimental ideas, previous-result questions, or authorized
  experiment execution in qi; recall also precedes next-slice recommendations and
  protocol grilling involving experiments.
scope: qi experiment recall and evidence workflow
status: stable
last_update: 2026-09-10
document_class: artifact
---

# Experiment

Use [the experiment method](../../../docs/experiments.md) as the workflow authority.
The shared dashboard at `/experiments` and `qi experiment search` read the same
catalog. The [module guide](../../../src/qi/experiments/README.md#shared-catalog-and-recording)
owns commands and entry fields; existing work items/reports own conclusions.

## Recall before proposing

1. Search the question and useful aliases with `uv run qi experiment search
   "<terms>"`. Read relevant entries with `show <id>`, their owners and referenced
   evidence. Check conditions, denominators, limitations and local availability.
2. State **prior finding and limits → overlap → proposed contribution**, with
   source links. Match data, teacher, budgets, target, metric and evaluation scope;
   a new label or larger budget alone does not make a study independent.
3. If catalog matches are absent, incomplete or suspicious, search owner prose
   with `rg` and the [historical index](../../../data/experiments/learning/README.md).
   Do not claim novelty from an empty search. Register recovered history in its
   existing owner when the task authorizes record maintenance; label the entry
   retrospective and retain unknowns.
4. Grill only unresolved material choices using `grilling`, after recall. Reuse
   settled decisions. A request to explain or plan is not permission to run trials.

## Execute and retain learning

For authorized work, predeclare the comparison, conditions, budget/stop rule and
prior-work contribution in its owner; register a planned entry using `template`,
`owner` and `record`. Use the owning runner's preview and execution contract.
Preserve resolved configs, implementation/data lineage, denominators, deviations,
failed/partial attempts and raw artifacts. Registration does not convert a
prototype into a supported runner or establish scientific comparability.

After execution or analysis, append an assessed entry/revision in the same owner
with finding, conditions, limitations, decision, revisit trigger and evidence
paths (hashes where useful). Cite prior IDs and the specific contribution. Preserve
original evidence and earlier conclusions; a correction identifies affected
findings and replacement evidence. Execution completion, conclusion and local
availability stay distinct. Keep imitation/reference agreement separate from
playing strength; a largest tested teacher budget is not a proven upper bound.

Use the current `owner_sha256` with `record` to reject stale writes. Validate with
`qi experiment check-catalog`; use `--verify-evidence` for supplied hashes of
available artifacts. Confirm `search`/`show` retrieves the new finding and report
its owner/evidence links, measured scope and next decision to the user. Stamp
new skill-produced records per [skill rules](../../../docs/rules/skill.md), without
claiming authorship of the original historical experiment.
