---
description: Own the educational game core and search while reusing external teachers and training tools.
scope: architecture decision
status: stable
last_update: 2026-09-07
document_class: coordination
---

# ADR-0001: Own the referee and search; reuse external teachers

- **Status**: superseded by [ADR-0012](0012-replaceable-game-execution.md)
- **Last Update**: 2026-09-07

Qi will implement its own framework-independent Python referee and compact
search implementation. External engines provide differential checks and teacher
labels for both learning tracks. This boundary keeps game and search mechanics
part of the learning goal while making early training failures easier to isolate.

## Context

The user accepted this ownership boundary and teacher bootstrapping during the
initial decision interview. The destination is learning through construction,
including conventional policy/value learning and LLM post-training.

The referee owns legality, transitions, and outcomes; players choose actions;
trainers update weights. External validation is evidence, not ownership of qi's
rules. The first version may simplify repetition/chasing under an explicit,
versioned training ruleset; exact adjudication remains open.

## Considered Options

- **Reuse a rules/search engine as the core** — reaches training sooner, but
  removes implementation work the user explicitly wants to learn from.
- **Own the referee/search and bootstrap with teacher data** — selected to retain
  that learning while separating supervised-learning failures from self-play failures.
- **Require learning from scratch first** — rejected as an initial prerequisite;
  it combines data-generation, exploration, and optimization uncertainty.

## Consequences

Qi bears the correctness and maintenance cost of its referee. Rule edge cases,
replay, and independent differential checks need explicit verification.
External implementations can disagree with the selected training ruleset;
comparisons must distinguish common movement rules from adjudication differences.

Record teacher identity and settings with generated data. Describe initialized
self-play as teacher-bootstrapped; isolate from-scratch experiments if added.
Teacher access during data generation does not grant evaluated players access.

Third-party engine choice and integration require validation before adoption.
LLM observations, outputs, reasoning, tool access, model choice, and comparison
protocol remain provisional. This ADR does not fix them.
