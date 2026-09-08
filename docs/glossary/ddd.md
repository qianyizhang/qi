---
description: Canonical domain vocabulary for qi.
scope: domain vocabulary
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Glossary

| Term | 中文 | Meaning | _Avoid_ |
| :-- | :-- | :-- | :-- |
| Xiangqi | 中国象棋 | The first two-player game implemented by qi. | — |
| Chinese checkers | 跳棋 | Proposed later star-board game; distinct from checkers. | — |
| Referee | 裁判 | Owns legal actions, state transitions, and terminal outcomes. | — |
| Player | 行棋方 | Selects an action; automated implementations share a callable contract. | Strategy or Policy as the plugin name |
| Trainer | 训练器 | Updates model parameters from labeled data or trajectories. | — |
| Ruleset | 规则集 | Versioned rules including adjudication and termination. | — |
| State | 状态 | Board, side to move, history, and adjudication context. | — |
| Trajectory | 对局轨迹 | Ordered states/actions with player-attributed outcomes. | — |
| MCTS | 蒙特卡洛树搜索 | Search family; learning is a separate component. | — |
| PUCT | 先验引导的树搜索选择法 | Tree selection balancing value, visits, and policy priors. | — |
| SFT | 监督微调 | Supervised fine-tuning on target model responses. | — |
| Arena | 评测场 | Reproducible matches under specified opponents and budgets. | — |
| Ply | 半回合 | One legal move by one player; 300 plies is the training ceiling. | — |
| Snapshot | 对局快照 | Versioned initial position and moves sufficient for exact replay. | — |
| State hash | 状态哈希 | Digest identifying the ruleset and full saved move history. | — |
| Alpha-beta | α–β 剪枝搜索 | Minimax search that prunes branches unable to improve the current bound. | — |
| Node budget | 搜索节点预算 | Maximum visited positions across all iterations of one move decision. | — |

## Player-building vocabulary

| Term | Full Form | 中文 | Meaning | _Avoid_ |
| :-- | :-- | :-- | :-- | :-- |
| Policy | — | 策略分布 | Maps a state to action preferences or probabilities; can be learned or hand-written. | Entire player or search algorithm |
| Search | — | 搜索 | Explores possible continuations to inform a player's decision. | Training |
| Evaluator | — | 局面评估器 | Assigns a heuristic score to a nonterminal position from a stated perspective. | Referee |
| Quiescence | Quiescence search | 静态搜索 | Extends the ordinary search frontier through captures and legal check evasions. | A learned policy |
| UCT | Upper Confidence bounds applied to Trees | 树置信上界 | MCTS selection rule balancing estimated return against exploration of less-visited children. | PUCT with learned priors |
| Rollout | — | 模拟续局 | A sampled continuation used to estimate a tree node's value; a length cutoff is not a referee outcome. | Training run |
| Stand pat | — | 静态估值基线 | Uses the current evaluation as a quiescence baseline when not in check. | A legal pass move |
| Tactics | — | 战术 | Short forcing sequences such as exchanges and checks. | Player interface |
| Strategy | — | 战略 | Longer-term positional plans and priorities. | Policy as a probability distribution |
