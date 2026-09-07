---
description: Canonical domain vocabulary for qi.
scope: domain vocabulary
status: stable
last_update: 2026-09-07
document_class: coordination
---

# Glossary

| Term | 中文 | Meaning |
| :-- | :-- | :-- |
| Xiangqi | 中国象棋 | The first two-player game implemented by qi. |
| Chinese checkers | 跳棋 | Proposed later star-board game; distinct from checkers. |
| Referee | 裁判 | Owns legal actions, state transitions, and terminal outcomes. |
| Player | 行棋方 | Selects actions; may be human, search-based, or learned. |
| Trainer | 训练器 | Updates model parameters from labeled data or trajectories. |
| Ruleset | 规则集 | Versioned rules including adjudication and termination. |
| State | 状态 | Board, side to move, history, and adjudication context. |
| Trajectory | 对局轨迹 | Ordered states/actions with player-attributed outcomes. |
| MCTS | 蒙特卡洛树搜索 | Search family; learning is a separate component. |
| PUCT | 先验引导的树搜索选择法 | Tree selection balancing value, visits, and policy priors. |
| SFT | 监督微调 | Supervised fine-tuning on target model responses. |
| Arena | 评测场 | Reproducible matches under specified opponents and budgets. |

| Ply | 半回合 | One legal move by one player; 300 plies is the training ceiling. |
| Snapshot | 对局快照 | Versioned initial position and moves sufficient for exact replay. |
| State hash | 状态哈希 | Digest identifying the ruleset and full saved move history. |
