---
description: How the first checkpoint-backed move policy encodes positions and chooses legal actions.
scope: learned policy player
status: stable
last_update: 2026-09-10
document_class: coordination
---

# Learned policy

ID: `policy`. Version: `policy-mlp-v1`.

A policy scores possible moves. This one learns from the local teacher's chosen
move at each labeled position. It performs one CPU network pass, keeps only the
referee's legal moves, and chooses the highest score. It does no tree search and
never consults a teacher during play. Ties use ascending action ID.

## Read the code

- `encoding.py`: 14 piece planes (seven types for each color), 90 squares each,
  plus a black-to-move bit: 1261 numbers. Coordinates stay absolute for both sides.
  Action ID is source square × 90 + destination square, giving 8100 outputs.
- `runtime.py`: a 64-unit ReLU hidden layer, output logits, legal-action selection,
  and validated CPU checkpoint loading. Logits are preferences, not position values.
- `__init__.py`: the shared player descriptor and explicit local configuration.
- [Trainer](../../learning/README.md): dataset construction, loss, experiments.

The input deliberately omits history. Identical boards with the same side to move
produce the same preferences even when their repetition histories differ. The
referee checks terminal outcomes before the player runs and adjudicates every move.
This limitation prevents claiming that the network observes the full game state.

## Load and play

```bash
uv sync --extra learning
export QI_POLICY_CHECKPOINT="$PWD/artifacts/learning/policy-v1.pt"
uv run --extra learning qi players
uv run --extra learning qi choose --state game.json --player policy
uv run --extra learning qi match --red policy --black random
uv run --extra learning qi play
```

The convenience environment setting exposes “Learned policy.” For independent
checkpoints, configure [named player entries](../README.md#named-player-bindings);
each entry appears separately in Play and resolves its own checkpoint. The browser
submits IDs and pinned digests, never filesystem paths.
A missing, malformed, incompatible, or nonfinite checkpoint is an explicit error;
there is no fallback to random weights. Checkpoints are local experiment artifacts.

Named entries cache each verified path and content digest. Replacing bytes rejects
an existing selection; explicitly selecting the new identity loads the new model.
The convenience environment default stays pinned for the process lifetime;
restart the process to adopt replacement weights for that default. Arena configurations pin the
SHA-256 before play; every choice reports it with `model_calls: 1`. Search nodes
and depth are zero; search budgets and seed do not change this greedy policy.
For named entries, the first choice can include dependency/model loading in its
latency; subsequent choices reuse the model. The convenience default loads while
binding, before the choice timer. Training reports separately measure warm
inference with legal masking; do not compare cold and warm timings as equivalent.

Checkpoints contain versioned metadata and this architecture's state dictionary.
Loading uses explicit CPU placement and `weights_only=True`, following
[PyTorch's state-dictionary loading guidance](https://docs.pytorch.org/tutorials/beginner/basics/saveloadrun_tutorial.html).
Metadata includes the dataset, reserved corpus, teacher binary/network, actual
training inputs, validation inputs, seed, completed steps, PyTorch version, training device and CPU thread count.
Legacy checkpoints default the latter fields to CPU and one thread. Training may
use MPS; saved tensors and this inference path remain on CPU.
Shape, dtype, finite weights, and split consistency are checked before use.
