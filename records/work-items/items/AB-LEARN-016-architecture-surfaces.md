---
description: Explore policy architecture mechanisms alongside data, teacher and metric limitations.
scope: backlog item
status: experimental
last_update: 2026-09-12
document_class: work_record
work_id: AB-LEARN-016
work_status: wip
work_kind: research
added: 2026-09-12
tags: domain
depends_on: AB-LEARN-014
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-12"
---

# AB-LEARN-016 — Architecture and diagnostic surfaces

## Intent

Use the existing frozen-data and training scaffolding to learn why policy models
behave differently. The user authorized architecture experiments and a consolidated
report investigating data, teacher and metric shortcomings. This is an exploratory
mechanism screen; it neither selects a production default nor claims playing strength.
The broader saved-model/game-validity comparison in [AB-LEARN-015](AB-LEARN-015-evaluation-metric-comparison.md)
retains its separate unresolved protocol.

## Acceptance Criteria

- Freeze five cases × seeds 7/17/27 on the existing mixed-4000 snapshot and its
  373 inspected development inputs. Preserve all 3900 sealed inputs unscored.
  Hash/replay/cache and transformed-input exclusion checks precede fitting.
- Reuse `SnapshotTensors` and full-batch `accumulated_step`; Adam .01, CPU one
  thread, float32, chunks 256. Observe updates 50 and 200 from each fit: 15 fits,
  30 correlated checkpoints. No setting selection from intermediate results.
- Contrast absolute MLP64 with MLP128 (capacity), canonical MLP64 (coordinate
  sharing), canonical MLP64 with bilinear source/destination scores (head
  structure), and canonical conv32 with the same scoring formula (spatial
  sharing). Report parameters, runtime and unresolved capacity/optimizer confounds.
- Diagnose train/development loss and agreement; six-cell macro and micro;
  forced/non-forced positions, legal-choice baseline, action-frequency strata,
  source/phase and confidence. Compare source/destination decisions where useful.
  Fixed temperatures 1 and 2 diagnose calibration with identical argmax moves;
  neither temperature is fitted or selected. This was added before fitting.
- Before any teacher query, freeze eight development inputs per source/phase cell
  using ascending SHA256(`architecture-surfaces-v1:` + input_hash). On these 48
  histories compare fresh 100k and 1M single-PV searches and 1M all-legal MultiPV
  WDL, one thread, Hash16, no depth cap, 20s per-query timeout. Retain raw answers,
  bounds, actual depths, missing assessments, label changes, near ties and WDL
  saturation. Higher-budget estimates are diagnostic references, not ground truth.
- Maximum 1800 seconds cumulative fitting including failed scientific fits,
  600 seconds per fit; 900 seconds teacher stage including failures. Stop before
  another unit when allowance is exhausted, on integrity failure/nonfinite loss,
  or process peak RSS over 1.5GB. Retain partial work; no automatic extension.
  Preparation, engineering checks and offline verification are timed separately.
- Retain source copies, resolved configs, raw per-input observations, weights,
  failed/partial attempts and receipts. Independently reload every completed
  checkpoint, rederive findings, validate the catalog and run repository checks.
- Deliver a report distinguishing observations, explanations and unresolved
  alternatives, and rank the next investigations by explanatory value.

## Context and Trade-offs

[Earlier tuning](AB-LEARN-003-local-policy-tuning.md) found that wider and
mover-relative alternatives did not transfer in the small shallow-label regime.
[Generated scaling](AB-LEARN-014-generated-data-scaling.md) changed the data and
teacher, found useful scaling, and exposed memorization and overconfidence.
[Teacher quality](AB-LEARN-009-teacher-quality.md) found mixed agreement gains but
improved supporting move estimates. This study revisits representation under the
changed regime and couples it to explanatory diagnostics; earlier criteria and
outcomes remain unchanged.

Predictions before fitting: widening may improve fit without addressing sparse
action supervision; coordinate/head sharing may help rare actions but constrain
useful interactions; spatial sharing may generalize efficiently while a small
receptive field misses long-range rook/cannon relations. Canonicalization may add
input aliases, so exclusions must be checked in that equivalence class. The
board-and-turn encoding omits history available to the teacher. Shared architecture
scores and hard-label cross-entropy cannot distinguish near-equal moves from blunders.

The decision rule is explanatory, not a winning-score threshold: prioritize a
mechanism only when its expected diagnostic pattern appears across paired seeds,
and state conflicting slices. A single higher aggregate justifies no adoption.
All cases use one recipe, one training pool and a repeatedly inspected development
set. Seeds probe initialization, not independent datasets. Equal updates do not
equalize compute; a poor fixed-recipe result does not reject an architecture family.
The [protocol](../../../data/experiments/learning/architecture-surfaces-v1/protocol.json)
pins local inputs and execution settings; study weights stay outside production
checkpoint formats. No new generation, cloud spending or match-outcome claim is
part of this screen.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-12 | Codex | — | wip | User authorized a bounded architecture and diagnostic exploration; protocol recorded before execution. |

## Implementation Ledger

### 2026-09-12 — decision: predeclared exploratory screen

- Evidence: protocol and prior-work links above; existing frozen cache has 4000
  training and 373 development rows, one-thread 100k labels.
- Consequence: five contrasts and diagnostic sample are fixed before scores;
  explanation and next-focus selection are the deliverables.
- Follow-up: preserve all attempted work and consolidate observed mechanisms.
- Review: not-required; authorized research scope, no production adoption.


```experiment
{
  "schema_version": 1,
  "id": "architecture-surfaces-v1",
  "title": "Architecture mechanisms and diagnostic surfaces",
  "question": "Which architecture, data, teacher and metric mechanisms explain the observed imitation limits?",
  "kind": "learning",
  "topics": [
    "architecture",
    "representation",
    "teacher",
    "metrics",
    "data coverage",
    "mechanism",
    "generalization"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Five architectures, seeds7/17/27, mixed4000 train +373 inspected development; updates50/200, Adam.01 CPU1. 48 stratified teacher inputs,100k/1M SPV and1M alllegal.1800s fits+900s queries.3900 sealed inputs excluded.",
  "limitations": "Exploratory one-pool fixed-recipe study; no model default or playing strength.",
  "decision": "Execute fixed contrasts and diagnose limitations; choose next focus from explained patterns.",
  "revisit": "After verified evidence and consolidated report.",
  "evidence": [
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/protocol.json",
      "role": "config",
      "sha256": null
    }
  ],
  "prior_work": [
    {
      "id": "policy-tuning-v1",
      "relationship": "extends",
      "contribution": "Revisit capacity and coordinate sharing on changed generated100k-label regime."
    },
    {
      "id": "generated-data-scaling-v1",
      "relationship": "uses",
      "contribution": "Reuse frozen4k inputs and inspected development to investigate representation rather than scale."
    },
    {
      "id": "teacher-quality-v1",
      "relationship": "extends",
      "contribution": "Diagnose reference instability and metric disagreement on fixed development sample."
    }
  ],
  "novelty": "Couple architecture contrasts to action support, choice difficulty, confidence and teacher stability diagnostics; explain mechanisms rather than optimize one metric."
}
```
