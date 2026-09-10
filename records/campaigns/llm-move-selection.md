---
description: Planned investigation of LLM move selection before and after supervised fine-tuning.
scope: LLM move selection campaign
status: experimental
last_update: 2026-09-10
document_class: coordination
---

# LLM move selection

## Destination

Determine whether a bounded SFT treatment improves one pretrained model's move
selection over its untuned baseline under a fixed protocol. This investigation
is planned and unscheduled.

## Model relationship

The referee supplies legal actions and outcomes; the model produces attempts;
evaluation preserves and assesses them. Training Data supplies frozen examples;
the trainer updates weights. Preserve the [core model](../../docs/models.md) and
the independent learning tracks in the [project direction](../../docs/project.md).

## Current understanding

Replay, teacher supervision and frozen datasets exist. Current policy-imitation
results concern a small neural model; they do not establish pretrained-LLM behavior.

## Unknowns

Model/device feasibility, representation and decoding choices, budget, untuned
behavior, SFT benefit, and how teacher disagreement relates to move quality.

## Frontier

When selected, lock a small feasibility and untuned position-evaluation protocol
before fitting. Use its evidence to scope a base-versus-SFT comparison under the
[experiment method](../../docs/experiments.md). No run is commissioned here.

## Work

- [LLM baseline and SFT comparison](../work-items/items/AB-LLM-001-baseline-and-sft.md).

## Learning ledger

2026-09-10: captured the requested baseline/SFT direction as planned exploration.
No LLM measurement or model choice has been made by this planning task.

## Closeout

Close after the bounded comparison supports a next decision, or its remaining
stages are explicitly deferred. Promote executable contracts to their modules
and durable findings to work records; preserve unresolved questions explicitly.
