---
description: Compact navigator over authority areas, rules, glossary, and agent flows in qi.
scope: documentation navigator index
status: stable
last_update: 2026-09-10
document_class: coordination
---

# Docs index

This is a **navigator, not an authority**: it routes authority areas, structural
docs, and main human-facing flows. Complete file discovery belongs to generated
Human View. When the index and a target disagree, identify the concern, fix the
stale route, and preserve the owning authority. Doctrine:
`docs/rules/governance.md` "Scoped authority and core models".

Project scope and milestone direction: [Project plan](project.md).
Accepted ownership and Training Data model: [Core model](models.md).
Generation, frozen mixtures and phase policies: [Training Data](../src/qi/training_data/README.md).
Player modules and learning guide: [Players](../src/qi/players/README.md).
Baseline players and matches: [Baselines](baselines.md).
Performance specs, evidence, and scoring: [Evaluation](evaluation.md).
Search experiment tracking and local reports: [Experiments](../src/qi/experiments/README.md).
Experiment method and campaigns: [Method](experiments.md), [policy generalization](../records/campaigns/policy-generalization.md),
[LLM move selection](../records/campaigns/llm-move-selection.md),
[experiment efficiency](../records/campaigns/experiment-efficiency.md).
Local external analysis: [Teacher](teacher.md).
Local supervised policy training: [Trainer](../src/qi/learning/README.md).
Coordinates and replay operations: [Interface](interface.md).
Training adjudication: [xiangqi-training-v1](xiangqi-training-v1.md).

## Authority by concern

Do not use one global precedence list for unrelated concerns:

| Concern | Authority |
|:--|:--|
| Project identity, invariant, core-model entry point, commands | `CLAUDE.md` |
| Executable local behavior | Owning code, tests, schema, or configuration |
| Cross-shard current contract | Owning contract, README, schema, or API definition |
| Durable reason for a significant trade-off | ADR |
| Canonical domain term | `docs/glossary/*` |
| Portable governance process | `docs/rules/*` |

If docs/models.md exists, it owns the project's cross-decision conceptual
relationships. It must link the lower authorities it governs rather than copy
their implementation details.

## Area routes

| Area | Contents |
|:--|:--|
| `docs/` | Current coordination and structural authorities |
| `docs/adr/` | Durable architecture decisions |
| `docs/rules/` | Portable governance doctrine |
| `docs/glossary/` | Canonical domain vocabulary |
| `records/work-items/` | Work-item lifecycle and durable item records |
| `records/campaigns/` | Bounded questions and evidence synthesis across experiments |
| `records/reports/` | Scoped audit findings and their promoted destinations |

When an optional area such as docs/adr/, docs/models.md, records/campaigns/,
records/reports/, sources/, or archive/ needs a durable route, add one here and
keep `[tool.doc_governance].index_route_areas` synchronized.

## Rules (portable doctrine, kit-owned)

| Doc | Scope |
|:--|:--|
| [`docs/rules/governance.md`](rules/governance.md) | Scoped authority, core models, toolchain layout, kit propagation |
| [`docs/rules/authoring.md`](rules/authoring.md) | Profile-scoped technical-authoring doctrine |
| [`docs/rules/agentic-glossary.md`](rules/agentic-glossary.md) | Portable human-agent collaboration vocabulary |
| [`docs/rules/doc.md`](rules/doc.md) | Documentation, work-item, and deprecation lifecycle |
| [`docs/rules/python.md`](rules/python.md) | Python style doctrine |
| [`docs/rules/skill.md`](rules/skill.md) | Skill authoring & lifecycle |
| [`docs/rules/skill-glossary.md`](rules/skill-glossary.md) | Portable skill-authoring vocabulary |
| [`docs/rules/testing.md`](rules/testing.md) | Testing doctrine |

## Glossary

| Doc | Scope |
|:--|:--|
| [`docs/glossary/ddd.md`](glossary/ddd.md) | Ubiquitous-language SSOT |

## Main flows

Humans can ask in ordinary language. Skills under `.codex/skills/` implement
these flows; they are not a menu the user must memorize.

| Flow | Human intent | Supporting skills |
|:--|:--|:--|
| **Understand** | See the relevant model or change clearly. | `show-me`; explicit rich artifact: `explain-layman` |
| **Align** | Resolve fit, vocabulary, and durable decisions. | `show-gap`, `grilling`, `grill-with-docs`, `domain-modeling` |
| **Change** | Advance a bounded destination through verifiable work; use a Campaign at the threshold in `docs/rules/governance.md`. | `next-slice`, work items, `handoff` |
| **Maintain** | Preserve documentation and kit/consumer ownership. | `doc-hygiene-audit`, `governance-sync` |

<!-- Keep this a compact task/concept router. Configure area routes in
     pyproject.toml; generated Human View owns complete discovery. -->
