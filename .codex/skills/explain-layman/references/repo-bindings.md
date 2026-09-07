---
binding_schema: "1"
profile: "qi"
profile_version: "1.0.0"
artifact_language: "English with Chinese domain terms"
output_dir: "docs/background"
index_file: "docs/index.md"
canonical_repo_url: "file:///Users/zhangqy/pkgs/qi"
verification_command: "make check"
agent_instructions: "CLAUDE.md"
---

# qi explainer bindings

## Audience and artifact defaults

A developer learning game engines, reinforcement learning, and LLM post-training
by building. Explain from first principles in English with Chinese game terms.
Artifacts are experimental projections unless an owning authority adopts them.

## Authority and grounding

Route through docs/index.md. docs/project.md owns project direction;
docs/glossary/ddd.md owns terms. Code and tests own implemented behavior.

## Non-negotiable boundaries

Distinguish implemented behavior, planned interfaces, and experimental results.
Keep referee, player, and trainer responsibilities separate. Never describe a
simplified training ruleset as tournament-correct.

## Vocabulary and tooltips

Use the domain glossary for game and learning terms. Explain MCTS as search,
SFT as supervised fine-tuning, and player-attributed rewards explicitly.

## Navigation and provenance

Link artifacts from the documentation index when useful. Footers identify qi,
source paths, date, and source revision when one exists. This repository is
local-only; replace the canonical local URL when a remote is configured.

## Verification

Run make check and the explainer validator. Visually inspect any generated
artifact, including narrow layouts and interaction controls.
