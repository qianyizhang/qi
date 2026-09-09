---
description: Project scope, architecture direction, and learning milestones.
scope: project direction
status: stable
last_update: 2026-09-09
document_class: coordination
---

# Project direction

## Purpose and provenance

Build to learn: first a working two-player Xiangqi game, then compare conventional
policy/value learning and LLM post-training. Later, consider Chinese checkers
(跳棋, assuming the star-shaped board variant).

This plan distills the supplied conversation
[Choose Learning Engine Stack](https://chatgpt.com/c/6a9e9fd2-3f20-83ee-b470-f44391808bee).
Its recommendations are design inputs, not evidence of implemented behavior or
freshly verified third-party capabilities.

## Decision state

[ADR-0001](adr/0001-own-referee-and-search-use-external-teachers.md) records the
accepted ownership and teacher-bootstrapping boundary.

The first playable milestone includes a minimal browser board for two humans
and structured CLI access to the same Python operations. Both humans can share one
browser in local pass-and-play; baseline computer opponents are also implemented.
Remote multiplayer is outside the current scope.
Keep the referee independent of browser sessions and transport so a future
adapter can reuse it; do not add accounts, rooms, or synchronization machinery.

[xiangqi-training-v1](xiangqi-training-v1.md) owns accepted adjudication;
[ADR-0002](adr/0002-version-simplified-training-adjudication.md) explains why it is
simplified and versioned.

Develop on the local Mac first. A rented single node with up to eight GPUs is a
possible later training environment, not an initial infrastructure requirement
or spending authorization. Exact hardware capacity, rental budget, and training
runtime remain unverified or undecided.

LLM move-only output, legal-move-list input, reasoning, tool use, and evaluation
comparisons remain low-fidelity directions. Revisit them before their experiment
slice; do not turn them into fixed interface contracts now.

## Stack and boundaries

| Area | Direction | Adoption point |
| :-- | :-- | :-- |
| Tooling | Python 3.12, uv, Ruff, pytest, Hypothesis | Bootstrap |
| Referee | Framework-independent Python state transitions | First playable game |
| CLI | Typer and Pydantic at external boundaries; JSON output | Game commands |
| Reference | pyffish/Fairy-Stockfish for differential checks; Pikafish via UCI as teacher | Validate installation, rule coverage, and licensing before use |
| Neural learning | PyTorch policy/value model and an educational PUCT implementation | After replay and arena |
| LLM learning | Transformers, Datasets, PEFT, TRL; SFT before RL | Independent track after arena |
| UI | FastAPI, React, TypeScript, Vite, SVG board | First playable milestone, sharing referee operations |
| Data | JSONL trajectories; add Parquet/SQLite when justified | Replay, then experiments |

Referee, CLI/API, and browser dependencies are installed and locked.
The optional local learning extra pins PyTorch for a small teacher-imitation
policy; its [work item](../records/work-items/items/AB-LEARN-001-policy-imitation.md)
records the working pipeline and unsuccessful held-out generalization smoke.
Larger model choices, accelerator budgets, and LLM trainer versions remain open.

The [core model](models.md) owns cross-context relationships. The referee owns
legality, transitions and outcomes; players select actions under budgets.
[ADR-0004](adr/0004-training-data-bounded-context.md) assigns selection, supervision
provenance and dataset composition to Training Data. Its first slice supports
random and teacher-guided continuations with frozen mixtures. Trainers prepare model inputs
and change weights using frozen data. Search and training
call Python directly; HTTP and CLI validation stay outside simulation loops.
Do not create generic multi-game abstractions before a second game needs them.

## Milestones

Milestone 1 is implemented; verification lives in the
[playable work item](../records/work-items/items/AB-GAME-001-playable-xiangqi.md).
Milestone 2 now has baseline players, CLI matches, and a fixed evaluation corpus
with paired-color batch summaries and a local UCI teacher adapter validated with
pinned Pikafish. See [teacher setup and limits](teacher.md). See [baseline contracts](baselines.md).
Milestone 3 has CPU/MPS policy training and bounded data-size learning curves
under [ADR-0003](adr/0003-pytorch-mps-training.md). Plain MCTS with random
rollouts is also implemented independently of training; see its
[module guide](../src/qi/players/mcts/README.md). Learned value estimation, PUCT,
self-play training, and the LLM track remain planned.
Local search comparisons now have [experiment tracking and offline reports](../src/qi/experiments/README.md),
with optional explored-tree recordings separate from benchmark timings.

1. Specify a named training ruleset and build a two-human Xiangqi browser board
   plus structured CLI access, with legal actions, outcomes, and deterministic
   save/replay for local pass-and-play.
2. Add random and small alpha-beta players, an evaluation arena, and a replaceable
   external teacher. Define fixed evaluation positions and budget reporting.
3. Branch into two learning tracks: teacher-supervised policy/value learning then
   PUCT self-play; untuned LLM evaluation then SFT, position-level RL, game-level RL.
4. Extend inspection and experiment tooling, then investigate Chinese checkers
   portability.

MCTS is search; it does not itself imply learned parameters. Separating direct
policy comparisons from systems using search or tools is a provisional evaluation
direction, to be settled before running those experiments.

## Constraints for implementation

- Ruleset identity and replay history travel with saved state. Board/FEN alone
  must not stand in for history-dependent adjudication or search-cache identity.
- Name simplified repetition/chasing behavior and version any semantic change.
  Do not claim tournament correctness for a training ruleset.
- Invalid actions leave state unchanged. Machine output uses stdout; diagnostics
  use stderr. Live mutation will require an expected-state guard.
- Outcomes and rewards identify the player perspective. Shared results should
  allow per-player values; no accidental reward for the opponent's tokens.
- Record seeds, ruleset, model/teacher versions, openings, inference budget,
  latency, invalid actions, and any retries in evaluation artifacts.
- Keep evaluation data separate from training data and teacher tools inaccessible
  to evaluated players unless tool access is the explicit experiment.
- Prefer synchronous execution first. Profile before adding concurrency,
  distributed training, another language, or a remote simulation service.
