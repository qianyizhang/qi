---
description: Project scope, architecture direction, and learning milestones.
scope: project direction
status: stable
last_update: 2026-09-22
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

[ADR-0012](adr/0012-replaceable-game-execution.md) owns the accepted rules/reference
and replaceable-execution boundary, superseding ADR-0001's Python-only direction.
[ADR-0013](adr/0013-modular-packages-and-direct-migration.md) accepts uv-managed
package dependencies, lazy loading and direct consumer migration without default
shims. The [game package](../packages/qi-game/README.md) now owns replay contracts
and a referee protocol used by CLI/HTTP. Player, learning, data and experiment
package separation remains later work. An optional
[native trajectory package](../packages/qi-game-native/README.md) is implemented
for explicit generation runs; Python remains the default.

The local frontend connects play, generated-data review, learning walkthroughs,
experiment reports, benchmarks and reference material.
Both humans can share one browser in pass-and-play, or either side can select a
built-in player, a configured checkpoint or Pikafish. The same Python operations
remain available through the CLI. [ADR-0005](adr/0005-shared-local-frontend.md)
records the shared frontend architecture; [the interface guide](interface.md)
owns player settings, saved sessions, reports and bounded trace jobs.
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
| Tooling | Python 3.12, uv, Ruff, pytest, Hypothesis; package-owned dependencies | qi application and qi-game workspace packages with one lock and an isolated game test lane |
| Referee | Readable Python reference plus conforming replaceable execution | Snapshot operations accept an injected backend; application/search default to Python, while policy generation may explicitly select the optional native trajectory package |
| CLI | Typer and Pydantic at external boundaries; JSON output | Game commands |
| Reference | pyffish/Fairy-Stockfish for differential checks; Pikafish via UCI as teacher | Validate installation, rule coverage, and licensing before use |
| Neural learning | PyTorch policy/value model and an educational PUCT implementation | After replay and arena |
| LLM learning | Transformers, Datasets, PEFT, TRL; SFT before RL | Independent track after arena |
| UI | FastAPI, React, TypeScript, Vite, SVG board | First playable milestone, sharing referee operations |
| Data | SQLite collections, frozen Parquet snapshots and retained JSON datasets/records | Replay, selection, then training and experiments |

Referee, CLI/API, and browser dependencies are installed and locked.
The accepted package migration uses one uv workspace and lockfile for supported
packages. Studies that need incompatible dependencies use excluded, separately
locked uv projects. Isolated package tests check declared dependency closure;
lazy imports and a shared environment alone cannot enforce it.

The optional native backend targets Apple Silicon macOS and Linux x86_64 CPU.
GPU/model-device dependencies stay outside the referee extension; Windows and
GPU-native simulation are deferred. It remains explicit and experimental rather
than a default promotion. Possible multi-client/batch serving remains a
low-fidelity, single-owner direction to revise around demonstrated workloads.
Session/run ownership and evidence remain governing constraints.
The [decision record](../records/work-items/items/AB-ARCH-001-modular-runtime.md)
routes the first implementation slice.

The optional local learning extra pins PyTorch for a small teacher-imitation
policy; its [work item](../records/work-items/items/AB-LEARN-001-policy-imitation.md)
records the working pipeline and unsuccessful held-out generalization smoke.
Larger model choices, accelerator budgets, and LLM trainer versions remain open.

The [core model](models.md) owns cross-context relationships. The referee owns
legality, transitions and outcomes; players select actions under budgets.
[ADR-0004](adr/0004-training-data-bounded-context.md) assigns selection, supervision
provenance and dataset composition to Training Data. Its first slice supports
random and teacher-guided continuations with frozen mixtures. Trainers prepare model inputs
and change weights using frozen data. Current search and training call Python
directly. The redesign permits coarse native execution while Python owns research
and ML; HTTP and CLI validation stay outside simulation loops. First native
acceptance targets batched gameplay/trajectory production with controlled actors.
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
- Prefer simple local execution first. Native substitution is accepted under
  ADR-0012; measure representative costs before selecting/adopting an implementation.
  Concurrency, distributed training and remote simulation services need their
  own demonstrated workload need.
