---
description: Decide the training-data boundary, addressable situations, and reproducible dataset composition.
scope: backlog item
status: stable
last_update: 2026-09-09
document_class: work_record
work_id: AB-DATA-001
work_status: done
work_kind: decision
added: 2026-09-09
tags: domain
depends_on: AB-LEARN-004
residual_of: none
residual_items: none
---

# AB-DATA-001 — Training Data boundary and curriculum

## Intent

Make training situations addressable independently of generation mode. Decide a
Training Data bounded context covering trajectory sources, position selection,
supervision provenance, and dataset assembly. The accepted model is promoted to [the core model](../../../docs/models.md),
[ADR-0004](../../../docs/adr/0004-training-data-bounded-context.md) and the
[glossary](../../../docs/glossary/ddd.md). This record retains the interview
evidence; runtime implementation remains pending.

## Acceptance Criteria

- Settle ownership relative to the referee, players, teacher adapter and trainers.
- Distinguish starting positions, semantic game phases, themes, optional task
  objectives, generation modes and sampling windows.
- Settle mixture semantics, source lineage, held-out boundaries, continuation
  limits, shortages and supervision identity before implementing new modes.
- Promote the settled meaning to owning model/glossary/contracts and identify a
  bounded first implementation slice after the interview concludes.

## Context and Trade-offs

Current generation starts standard-board random trajectories, selects positions,
queries one teacher configuration, and embeds replay/observation exclusions in a
single dataset model. The 16x data study improved imitation, but labels remain
concentrated in the first 32 plies. New sources and mixed curricula need more
explicit domain concepts than a growing generator-mode switch.

The current evaluation term `Opening` includes arbitrary replayable starting
positions; glossary `Rollout` currently means an MCTS continuation. Resolve these
meaning collisions explicitly. Snapshot v1 permits only the standard starting
FEN with a replayable move list; diagram-only states would change that contract.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-09 | Codex | — | wip | User requested a decision interview on addressable phases and scenarios. |

| 2026-09-09 | Codex | wip | done | User accepted the final identity/supervision/family recommendations; model promoted and first build slice identified. |

## Implementation Ledger

### 2026-09-09 — decision: round-one direction

- Evidence: user answered "all your rec" to the four recommendations on phase
  meaning, history availability, scenario objectives and slice-level evaluation.
- Proposed wording carried forward: use a versioned board-feature phase policy,
  with recorded curated classifications and an unknown state; keep ply number
  independently available. First implementation supports replay-backed starting
  positions. Diagram-only positions remain a separate future contract change
  with explicit handling of unavailable history.
- Proposed wording carried forward: a named scenario describes positions and
  tags, with an optional explicit objective and answer authority. Teacher
  preferences, demonstrated moves and referee-proven solutions have different
  meanings. Shared slice vocabulary supports training and evaluation; held-out
  source families remain separate. Slice coverage/results are required, and the
  evaluation mixture stays fixed across training-recipe comparisons.
- Consequence: proceed to mixture, continuation and shortfall decisions. No
  phase thresholds, mixture percentages, diagram semantics or multi-ply solution
  proofs have been selected implicitly.
- Follow-up: restate this wording in the next interview round, resolve the
  remaining frontier, then promote settled contracts coherently.
- Review: ratified as user-endorsed direction; final cross-boundary wording is
  still being developed in the interview.

### 2026-09-09 — decision: round-two direction and identity question

- Evidence: user accepted all four round-two recommendations, and separately
  asked whether hashed state could serve as the reference ID and whether
  fingerprint is the correct term. That question is not approval of a particular
  identity design.
- Wording carried forward: mixture quotas count retained unique examples assigned
  to one explicit quota bucket, while descriptive tags can overlap. Retain reusable
  labeled records and materialize a fixed selection manifest with recipe and seed.
  Keep continuation limits separate from position-selection conditions. Preserve
  partial work and report shortages without silently redistributing quotas or
  presenting an incomplete dataset as the requested complete recipe.
- Finding: existing `Game.state_hash` fingerprints ruleset, standard starting FEN
  and full move history. Policy `input_key` fingerprints encoding version, board
  and turn. These intentionally represent different equality relations. Current
  dataset digest covers the full serialized record, including teacher timing.
- Proposed identity direction, not yet locked: explicit state, observation and
  labeled-example fingerprints, with canonical versioned identity payloads and
  a frozen-manifest fingerprint. Operational timing belongs in run evidence.
  Human-facing scenario/recipe identifiers remain distinct from content references.
  Clarify the glossary's Identifier/Hash distinction during final promotion.
- Follow-up: resolve example identity, supervision compatibility and precise
  source-family boundaries before concluding the model interview.
- Review: round-two behavior accepted; fingerprint design remains a proposal.


### 2026-09-09 — decision and verification: close the model interview

- Evidence: user answered "all your rec" to round three: separate state,
  observation, example and dataset fingerprints; initially one supervision
  contract/teacher recipe per mixed dataset; and explicit source families with
  independent standard-board games exempt from being one shared family.
- Consequence: the model interview is complete. Core relationships are promoted
  to `docs/models.md`, rationale to ADR-0004, and accepted vocabulary to the
  glossary. CLAUDE/project/index/trainer bindings distinguish this accepted
  architecture from the still-existing single-generator implementation.
- Naming: use Starting position for new data concepts; preserve legacy Opening
  corpus fields and MCTS Rollout meaning. Fingerprints can serve as content keys;
  logical scenario/recipe names do not by themselves freeze content. Existing hash
  fields and artifacts require an explicit migration rather than silent rehashing.
- Follow-up: AB-DATA-002 identifies a bounded build with random and teacher-guided
  sources, addressable situations, frozen two-mode composition and trainer
  consumption. Implementation has not started. Classifier thresholds, example
  mixture proportions and canonical serialization details remain named build or
  experiment choices; diagram-only states and additional modes remain later work.
- Verification: documentation hygiene passed across 67 Markdown files, local
  links and diff whitespace passed, and all 17 glossary/report-consumer tests
  passed. No production code or data generation changes are part of this task.
- Review: ratified through the three user-endorsed rounds; no unresolved
  cross-boundary decision is being inferred as implementation completion.
