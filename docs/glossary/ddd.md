---
description: Canonical domain and technical vocabulary, including beginner explanations used by the experiment report.
scope: domain vocabulary
status: stable
last_update: 2026-09-21
document_class: coordination
---

# Glossary

These definitions are the vocabulary authority for qi. The HTML report embeds
this glossary at generation time: its tooltips and searchable reference are
projections of these entries. Aliases connect visible labels and saved field names
to a canonical term; they do not introduce different meanings. `_Avoid_` records
human misconceptions. Only an explicit optional `Replaced terms` column declares
deprecated spellings for the authoring checker; aliases and misconceptions do not.

## Game and rules

| Term | 中文 | Meaning | _Avoid_ | Aliases |
| :-- | :-- | :-- | :-- | :-- |
| Xiangqi | 中国象棋 | Chinese chess, played by Red and Black. This is the first game implemented in qi. | Confusing it with Chinese checkers | — |
| Chinese checkers | 跳棋 | The proposed later star-shaped board game. Its rules differ from Xiangqi. | Calling it Xiangqi | — |
| Referee | 裁判 | The code that decides which moves are legal, applies them, and determines when a game ends. Players ask it for moves; they cannot override its rulings. | Player or evaluator as rules authority | — |
| Referee backend | 裁判执行后端 | A replaceable implementation of the same named rules and history semantics. The accepted design permits Python or conforming accelerated execution. | A different ruleset or independent rules authority | — |
| Player | 行棋方 | A human or program that chooses a legal move. A program may choose randomly, search ahead, or use learned weights. | Using Policy as the name for every player | players |
| Player binding | 行棋方配置绑定 | A named local configuration selecting a player implementation and any checkpoint or external-engine resources. Each participant resolves its own binding to pinned content identities. | An algorithm version or a content fingerprint | player_binding |
| Player session | 行棋执行会话 | One participant's runtime context for a game, including permitted mutable search state and an explicit reset policy. Accepted for the runtime redesign; not yet implemented. | Saved Game session, client connection, or a globally shared player instance | — |
| Ruleset | 规则集 | The named rules used to judge a game. qi uses xiangqi-training-v1, including simplified repetition handling and a 300-ply ceiling. | Tournament-correctness claims | xiangqi-training-v1 |
| Board | 棋盘 | The 90 squares and their pieces. In raw records, a dot means an empty square; uppercase pieces are Red and lowercase pieces are Black. | Treating the board alone as full state | leaf_board |
| General | 将／帅 | The king piece, shown as 帥 or 將 and encoded K/k. It normally moves one point orthogonally inside its palace; opposing generals cannot face along an unobstructed file. | A piece that can be left in check | king |
| Advisor | 仕／士 | A palace guard, shown as 仕 or 士 and encoded A/a. It moves one point diagonally and stays in its own palace. | A bishop with unlimited range | guard |
| Elephant | 相／象 | Shown as 相 or 象 and encoded B/b. It moves two points diagonally, cannot jump a blocked midpoint, and cannot cross the river. | A sliding bishop | bishop |
| Horse | 马 | Shown as 馬 and encoded N/n. It moves one point orthogonally then one diagonally outward; a piece blocking the first point prevents that move. | A chess knight that always jumps | knight |
| Chariot | 车 | Shown as 車 and encoded R/r. It moves any unobstructed distance along a rank or file. | A piece that jumps blockers | rook |
| Cannon | 炮 | Shown as 炮 or 砲 and encoded C/c. It moves like a chariot without capturing; to capture, it jumps exactly one intervening piece. | Jumping a screen on an ordinary noncapture | cannon |
| Soldier | 兵／卒 | Shown as 兵 or 卒 and encoded P/p. It moves one point forward; after crossing the river it may also move one point sideways, never backward. | A chess pawn with diagonal captures or promotion | pawn |
| Palace | 九宫 | Each side's three-by-three area in the middle of its back three ranks. Generals and advisors stay inside their own palace. | The entire home half | palace |
| River | 河界 | The boundary between the two halves of the board. It limits elephants and changes soldiers' available moves after crossing. | A playable rank | river |
| State | 状态 | Everything needed to continue and judge a game: board, side to move, and relevant move history. The same board can have a different outcome under different histories. | Board alone | — |
| Position | 局面 | Canonical board and side to move under a ruleset. A saved position also carries the history needed to reconstruct its exact state; a Position occurrence identifies its place in a trajectory. | Assuming board equality implies identical replay history | positions |
| Side to move | 当前行棋方 | The color whose turn it is: Red or Black. Many search scores are expressed from this side's point of view. | Always interpreting positive as good for Red | side; turn; leaf_side |
| Legal move | 合法着法 | A move accepted by the referee, including the requirement not to leave your own general in check. | A move merely suggested by a player | legal actions; legal moves |
| Move | 着法 | Moving one piece from one square to another. Raw notation such as b2e2 means source b2 to destination e2; files a–i and ranks 0–9 use Red's viewpoint. | Mixing coordinates with Chinese move notation | moves; selected; cutoff_move |
| Ply | 半回合 | One move by one side. Red moves once and Black replies: that is two plies. qi's training rules stop at 300 legal plies if no earlier result applies. | A pair of moves | plies |
| Check | 将军 | A threat to capture the opposing general. The checked side must make a legal move that removes the threat. | A proof that the game is already won | checked |
| Capture | 吃子 | A move that removes an opposing piece from its destination square. Captures often start tactical exchanges. | Any move toward an opponent | captures |
| Checkmate | 将死 | The side to move is in check and has no legal reply; it loses. | Every terminal position | checkmate |
| Stalemate | 困毙 | The side to move has no legal move even though it is not in check. In this Xiangqi ruleset it loses. | The chess convention of calling this a draw | stalemate |
| Repetition | 重复局面 | The same board and side to move occur again. This training ruleset draws on the third occurrence; it does not implement full tournament chasing rules. | Identical boards without checking side/history | threefold repetition; threefold-repetition |
| Terminal outcome | 终局结果 | A result declared by the referee: win, loss, or draw, with a reason. Search or recording limits are not game outcomes. | Treating a search cutoff as game over | terminal; outcome; outcomes; winner |
| Draw | 和棋 | A game that the referee ends without a winner, for example through the repetition or ply-limit rule. An unfinished game is not a draw. | Incomplete games | draws; ply-limit |
| Trajectory | 对局轨迹 | The ordered sequence of states and actions in a game, with outcomes attributed to the appropriate player. | A single position | trajectories |
| Snapshot | 对局快照 | A saved starting position, ruleset, and move list that can reconstruct a game exactly. | An image of the board | snapshot |
| Game session | 对局会话 | The saved Play record containing a referee snapshot, current participant settings, and the known configuration history of recorded moves. Imported game-only history may have unknown player attribution. | A fixed-player evaluation run or a snapshot alone | game_session |
| Replay | 重放 | Rebuilding a game by applying its recorded moves through the referee. This checks states and outcomes, not playing strength or original wall-clock timing. | Re-running the player's search | replays |
| FEN | 局面记法 | Forsyth–Edwards Notation: a compact text description of a board and side to move. qi snapshots support the fixed standard starting FEN plus moves. | Complete history-dependent state | initial_fen |
| State hash | 状态哈希 | A fingerprint of the ruleset and full saved move history. Applying a move with this guard checks that it refers to the expected game state. | A board-only hash | state_hash; expected_state_hash |

## Players and search methods

| Term | 中文 | Meaning | _Avoid_ | Aliases |
| :-- | :-- | :-- | :-- | :-- |
| Search | 搜索 | Trying possible continuations before choosing a move. This spends computation but does not itself train a model. | Training | — |
| Minimax | 极小化极大 | Choose the move with the best result assuming the opponent chooses the reply that is worst for you. Leaf positions are estimated when a full game cannot be searched. | Assuming an opponent cooperates | — |
| Alpha-beta | α–β 剪枝搜索 | A faster way to compute a minimax result by skipping branches that cannot improve the current choice within the searched horizon. qi's basic recipe uses material scoring. | A learned model | alphabeta; alphabeta-material-v1 |
| Quiescence | 静态搜索 | Extra search through captures and legal check evasions at a normal search leaf, so a score is less likely to stop halfway through an exchange. | An unlimited tactical solver | quiescence search; alphabeta-quiescence-v1 |
| MCTS | 蒙特卡洛树搜索 | Monte Carlo Tree Search: repeatedly explore a path, estimate its result, and update statistics. qi chooses the root move with the most completed visits. | Assuming it requires neural learning | mcts-uct-v1 |
| UCT | 树置信上界 | Upper Confidence bounds applied to Trees: the MCTS rule that balances promising moves with moves tried less often. Opponent values must be converted to the choosing side's perspective. | PUCT with learned priors | — |
| PUCT | 先验引导的树搜索选择法 | A tree-selection method that combines value estimates, visit counts, and prior move preferences. It is a planned learning direction, not the current plain MCTS recipe. | Current implemented UCT | — |
| Evaluator | 局面评估器 | A function that estimates how favorable a nonterminal position is for a stated player. Its heuristic score is not a referee outcome. | Rules authority | evaluation; evaluator |
| Material | 子力 | A score based on which pieces remain and their assigned values. In qi a rook is valued at 900, but that is a heuristic scale rather than a win probability. | The whole positional assessment | material |
| Positional evaluation | 位置评估 | Adds hand-set piece placement, mobility, and king-safety terms to material. The weights in this project have not been tuned as a strength claim. | Learned weights | positional assessment; alphabeta-positional; alphabeta-positional-v1 |
| Placement | 棋子位置 | The contribution from where pieces stand, according to hand-set positional preferences. It is one part of the static evaluation. | A searched result | placement |
| Mobility | 机动性 | The evaluator's contribution from available legal movement. More options can be useful, but this term is a heuristic rather than proof of an advantage. | Playing strength by itself | mobility |
| King safety | 将帅安全 | The evaluator's hand-set contribution for the safety of the general. It is not a guaranteed mate detector. | A proof of forced mate | king_safety |
| Tactics | 战术 | Short forcing sequences such as checks, captures, and exchanges. The experiment's proven targets cover immediate wins only. | A player interface | tactical |
| Strategy | 战略 | Longer-term positional plans, such as improving piece activity or preparing an attack. It describes play rather than a software interface. | Policy as a probability distribution | — |
| Move ordering | 着法排序 | Trying promising legal moves earlier. This can help alpha-beta prune sooner, while preserving which legal moves are eligible for search. | Pruning moves just because they are late | ordered_moves; alphabeta-ordered; alphabeta-ordered-v1 |
| Killer move | 杀手着法 | A quiet move that caused a cutoff at the same search ply and is tried early later in that decision. | A guaranteed winning move | — |
| History heuristic | 历史启发 | A search-local record of quiet moves that caused useful cutoffs, used to order future moves in the same decision. | Referee repetition history | — |
| SEE | 静态交换评估 | Static Exchange Evaluation: estimates the material result of captures and legal recaptures on one square. qi uses it to order moves, not to prove tactics or prune them. | A complete tactical solution | static exchange evaluation; exchange analysis; exchange; exchange-reply; exchange-step; alphabeta-see; alphabeta-see-v1 |
| Check extension | 将军延伸 | Spending extra search depth when a position is in check, under a per-path extension allowance and the shared visit budget. | Free extra work | check-extension; extensions; check_extensions; alphabeta-checks; alphabeta-checks-v1 |
| TT | 置换表 | Transposition Table: a search-local cache of compatible scores, bounds, and move hints. Its key includes adjudication history and search context, not just the board. | A board-only outcome cache | transposition table; transpositions; alphabeta-tt; alphabeta-tt-v1 |
| Combined alpha-beta | 组合 α–β | The alphabeta-enhanced recipe combines positional scoring, move ordering, SEE, check extensions, a transposition table, and quiescence. More components can spend budget before reaching greater depth. | Assuming combined means stronger at every budget | alphabeta-enhanced; alphabeta-enhanced-v1; combined recipe |
| Tactical MCTS | 战术叶节点评估 MCTS | The mcts-quiescence recipe uses bounded quiescence at rollout leaves. Its extra leaf visits share the global budget; unfinished tactical estimates are discarded. | A learned value network | mcts-quiescence; mcts-quiescence-v1; tactical leaf |
| Recipe | 行棋算法配方 | A named combination of search and evaluation components. A stable ID selects it; a version identifies its behavior. | A new set of game rules | recipes |
| Baseline | 基线 | A reference player or method used for comparison. Beating it in a small sample does not establish general strength. | Ground truth for every best move | baselines |

## Search trees and values

| Term | 中文 | Meaning | _Avoid_ | Aliases |
| :-- | :-- | :-- | :-- | :-- |
| Search tree | 搜索树 | Positions connected by possible moves. The report shows explored work; it does not invent unsearched branches or their scores. | The entire possible game tree | searched branches; branches |
| Node | 节点 | A position or recorded step inside a search tree. A stored MCTS node can be visited repeatedly. | One unique node for every charged visit | — |
| Root | 根节点 | The position where a move decision begins. Root actions are the legal first moves being compared. | A leaf | root actions; root_moves |
| Parent | 父节点 | The earlier trace event that contains or leads to this event. A null parent denotes a top-level event. | Necessarily the preceding event in time | parent |
| Leaf | 叶节点 | A frontier where search stops expanding and obtains an outcome or estimated value. A leaf can be evaluated by quiescence. | A completed game | leaf; leaves |
| Search depth | 搜索深度 | How many ordinary plies alpha-beta aims to examine in an iteration. Extensions and quiescence can add work beyond this horizon. The configured depth does not control MCTS. | Total node count or MCTS depth | depth; effective_depth; stored_depth; default_depth |
| Completed depth | 已完成深度 | The deepest ordinary alpha-beta iteration fully finished within the budget. An interrupted deeper iteration does not count. Zero means no full iteration finished; MCTS has no comparable ordinary depth. | Treating partial search as completed depth | completed_depth; mean_completed_depth; mean_depth; Depth¹ |
| Iterative deepening | 迭代加深 | Search depth one, then depth two, and so on, retaining the last fully completed answer when the budget runs out. | One uninterrupted tree at the maximum depth | iterative-deepening; iteration; iteration-result |
| Horizon | 搜索边界 | The depth or other frontier where search must estimate a position instead of following the game to its end. | A proven final result | frontier |
| Pruning | 剪枝 | Skipping branches that cannot improve the current bounded search choice under the algorithm's rules. Skipped branches have no newly computed score. | Removing legal moves from the referee | prune; pruned |
| Cutoff | 截断 | A reason to stop exploring a branch. Alpha-beta bound cutoffs and rollout/budget limits have different meanings; none alone ends the real game. | A game outcome | cutoffs; search_cutoffs; beta-cutoff; cutoff |
| Alpha bound | α 界 | The current lower threshold in an alpha-beta search window: the best guarantee already available to the side choosing at that node. Child windows change sign as perspective alternates. | Always a root-relative score | alpha; final_alpha |
| Beta bound | β 界 | The upper threshold in an alpha-beta search window. Reaching it can make further exploration of that branch unnecessary to the parent. | A probability | beta |
| Score bound | 分数界 | Whether a returned value is exact for its searched horizon, a lower bound, or an upper bound. A bound is not necessarily the true minimax value. | Treating every returned number as exact | bound |
| Exact score | 精确搜索值 | A value resolved within the stated search horizon and evaluator. It is not a claim that the game has been solved to its final outcome. | Perfect play | exact |
| Lower bound | 下界 | The searched value is at least this number; a cutoff may have prevented finding its exact value. | An exact score | lower |
| Upper bound | 上界 | The searched value is at most this number; it need not be the exact value. | An exact score | upper |
| Stand pat | 静态估值基线 | The static evaluation used as a quiescence baseline when not in check. It is a scoring option, not permission to pass a turn. | A legal pass move | stand_pat; stand-pat-cutoff |
| Search score | 搜索分数 | A search result on a stated evaluator's scale and perspective. Material, positional, mate, and MCTS value scales are not interchangeable. A null score means none is reported. | A calibrated chance of winning | score; scores; Search score · one player; score_scale |
| Value | 价值估计 | An estimated result used by search. Read its perspective and scale: MCTS uses bounded values, while alpha-beta may use material, positional, or mate scores. | A universal comparable number | value; leaf_value |
| Score perspective | 分数视角 | Which side benefits from a positive value. Most node values belong to that node's side to move; MCTS root-action diagnostics are converted to the choosing player's perspective. | Always positive for Red | value_perspective; perspective |
| Mean value | 平均价值 | In MCTS, the average of completed backed-up estimates. A tree node's mean belongs to its own side to move; root-action means in a Choice belong to the choosing side. It is not a calibrated win probability. | Combining incompatible perspectives | mean_value |
| Mate score | 将死分数 | A large signed score representing a terminal win or loss; search adjusts it by distance so nearer wins and later losses can be preferred. | Ordinary material or probability | mate-or-material |
| Selection | 选择 | Following an existing MCTS child according to UCT, balancing estimated value and exploration. | Choosing the final game move already | selection |
| Expansion | 扩展 | Adding a previously untried child to the MCTS tree. Later simulations can revisit that stored node. | Completing a simulation | expansion |
| Simulation | 模拟 | One MCTS attempt to follow a tree path, estimate a leaf, and back up its value. Only completed backed-up attempts count in the simulations statistic. | A real played game | simulations; simulation |
| Rollout | 模拟续局 | A sampled continuation from an MCTS frontier. qi uses seeded random legal moves, then an outcome or leaf estimate. A rollout limit is not a draw. | Training or actual opponent play | rollout; rollout-step |
| Backup | 价值回传 | Updating MCTS node visit counts and accumulated estimates along the selected path. The sign alternates between sides. | Copying an artifact file | backup; backed_value; backed_up |
| MCTS node visits | MCTS 节点访问次数 | The number of completed simulations whose value was backed up through a stored node. Unfinished simulations do not increase this count; it differs from charged work visits. | Counting every attempted step as a completed sample | root visits |
| Retained tree | 保留的搜索树 | MCTS nodes stored during this decision, shown with their final visit/value statistics. Rollout steps are recorded separately and are not all retained tree nodes. | Every rollout position | mcts-tree; Final MCTS tree |
| Unsearched moves | 未搜索着法 | Legal candidate moves that were not explored at this point, due to ordering, pruning, or budget. They have no invented score. | Illegal moves | unsearched; unsearched_moves; untried; noncaptures |
| Move hint | 着法提示 | A previously promising or cached move used to guide ordering. A cache hit can provide only a hint without allowing a score cutoff. | A proved best move | hint |
| Exchange gain | 交换子力收益 | The material gained by a step in SEE's same-square capture sequence, on the piece-value scale. | A full position evaluation | gain |

| Engine diagnostics | 引擎原生诊断 | An explicit external engine's reported work and cp/mate assessment, with its own score perspective and bounds. These counters do not use qi charged-visit semantics. | qi search accounting or teacher access granted to other players | engine |
| Binding identity | 配置绑定内容标识 | The content fingerprint of an implementation, checkpoint or engine/network resources and fixed engine settings. A saved participant rejects changed resource bytes. | A label or file path | binding_sha256 |
| Work semantics | 工作量计数语义 | Identifies whether a configuration uses qi charged visits or external engine-native accounting. Native reported work can exceed requested UCI limits and can be unknown. | Equating visits across different engines | work_semantics |
| Move timeout | 单步超时 | The finite wall-time allowance for one external engine decision, including its protocol exchange. Timeout fails the request without applying a move. | Search depth or a prediction of actual latency | timeout_seconds |

## Budgets, counters, and timing

| Term | 中文 | Meaning | _Avoid_ | Aliases |
| :-- | :-- | :-- | :-- | :-- |
| Node budget | 搜索节点预算 | The maximum charged work visits allowed for one move decision, shared across iterations and extra tactical work. It does not promise a fixed elapsed time. | A count of unique boards or seconds | Visit budget; budget; budgets; node_budgets; default_nodes |
| Charged visits | 计费访问次数 | Search-work steps charged to the shared budget. Revisiting a position still costs work. A result's nodes is actual usage; a configuration's nodes sets its limit. | Unique tree nodes or completed simulations | nodes; visits; visit; charged visit; work; Search work; mean_nodes |
| Q visits | 静态搜索访问次数 | Positions visited in quiescence, including its already-counted entry frontier. Q visits can overlap MCTS tree or rollout counts, so these columns cannot all be added together. | Extra visits disjoint from every other counter | qnodes; mean_qnodes; Q visits² |
| SEE visits | 交换评估访问次数 | Capture-analysis steps charged by static exchange evaluation. In alpha-beta accounting these are separate from Q visits, but both use the shared budget. | Free ordering work | see_nodes; mean_see_nodes |
| Tree visits | 树访问工作量 | MCTS work spent entering the root and visiting tree children, including repeated visits. Tree visits plus rollout steps plus extra leaf visits equal total charged work. | MCTS completed node visits | tree_visits |
| Rollout steps | 模拟续局步数 | Simulated moves taken during random rollouts. Each successor visit consumes budget; these steps do not alter the real game. | Real game plies | rollout_steps; step |
| Rollout length | 模拟续局长度 | The maximum random continuation length in plies before MCTS uses its leaf evaluator. It is not alpha-beta search depth. | The whole simulation count | rollout_plies; default_rollout_plies |
| Extra leaf visits | 额外叶节点访问次数 | Additional work spent by MCTS's tactical leaf evaluator, beyond tree visits and rollout steps. Abandoned leaf work still consumes the budget. | All Q visits | leaf_nodes |
| Leaf aborts | 叶节点评估中断 | Tactical MCTS leaf estimates interrupted by budget exhaustion. Their work is charged, but their unfinished estimates are not backed up into completed statistics. | A player failure or a drawn game | leaf_aborts; discarded-leaf |
| Terminal simulations | 到达终局的模拟 | Completed MCTS simulations whose simulated continuation reached a referee outcome. They are still simulations, not actual match results. | Completed real games | terminal_simulations |
| Rollout cutoffs | 模拟长度截断 | Completed MCTS estimates taken because the rollout reached its configured length instead of a terminal outcome. | Draws | rollout_cutoffs; rollout-limit |
| Budget cutoffs | 预算截断 | Completed plain-MCTS estimates taken at a work limit. These differ from tactical leaf aborts, whose unfinished estimates are discarded. | Every incomplete search | budget_cutoffs; work-limit; heuristic_cutoffs |
| Unfinished simulations | 未完成模拟 | MCTS attempts that produced no backed-up estimate, for example a root-only attempt or an interrupted tactical leaf. | Completed simulations | unfinished_simulations; root-only |
| Maximum tree depth | 最大树深度 | The deepest stored-tree path visited by MCTS during the decision. Rollout and extra leaf depth are not included. | Alpha-beta completed depth | max_tree_depth |
| Quiescence horizon limit | 静态搜索边界限制 | At the configured tactical-leaf depth, a position that is not in check returns its static evaluation. Check evasions can continue beyond that depth under the shared visit budget. | An aborted or unbacked estimate | leaf-limit; max_plies |
| Quiescence depth | 静态搜索深度 | Depth within the quiescence continuation, starting at zero at its entry frontier. max_qply is the deepest such level reached. | Ordinary alpha-beta depth | qply; max_qply |
| Extension allowance | 延伸额度 | Extra plies permitted along a search path for check extensions. Remaining, consumed maximum, and ordinary depth are separate quantities. | Additional global node budget | extensions_left; max_extensions; remaining |
| Cache | 缓存 | Saved computation reused later. Referee caches can stay warm across recipe runs; transposition tables here are local to a single decision. This can affect measured timing. | Evidence of algorithmic speedup by itself | caches |
| Cache hit | 缓存命中 | Finding a compatible table entry to examine. It may only supply a move hint; a hit does not necessarily avoid further search. | A cache cutoff | cache-hit; tt_hits; TT hits |
| Cache cutoff | 缓存截断 | Reusing a compatible cached score or bound to finish a search branch without searching its descendants again. This is a subset of cache hits. | Every table hit | cache-cutoff; tt_cutoffs; TT cutoffs; TT cutoffs / hits |
| Cache store | 缓存写入 | Saving a completed search value, its bound, horizon, extension context, and optional move hint for reuse within this decision. | Storing an interrupted result as complete | cache-store |
| Latency | 耗时 | Elapsed wall-clock time for a move decision, including validation but excluding file writing. Fixed recipe order, shared caches, and machine conditions affect it. | An isolated speedup measurement | elapsed_ms; mean_elapsed_ms; mean_ms; Decision time; Mean decision time; Mean ms; timing |
| Millisecond | 毫秒 | One thousandth of a second. The report's decision-time measurements use this unit. | Seconds | ms; milliseconds |
| Mean | 平均值 | The sum of measured values divided by the number of samples. An average can hide variation between positions. | A guarantee for every sample | average |
| Deadline | 截止时限 | The run's elapsed-time allowance, checked between move decisions. One in-flight bounded decision may finish after it; pending work stays incomplete. | A hard per-instruction CPU cutoff | allowance_seconds; deadline |
| Budget exhaustion | 预算耗尽 | Search cannot charge another visit. Iterative alpha-beta retains its last completed iteration; tactical MCTS discards an unfinished leaf estimate. | A terminal game outcome | BudgetExhausted |
| Model calls | 模型调用次数 | Number of learned-policy inference passes used for a decision. It is zero for these search-only experiments. | Search visits | model_calls |
| Invalid action | 非法动作 | A proposed move that the referee rejects. The shared player boundary checks legality rather than silently accepting it. | A weak but legal move | invalid_actions |
| Retry | 重试 | An additional attempt after a failure or rejection. Retries would need to be reported; this experiment runner does not silently retry moves. | An extra search iteration | retries |

## Experiments and interpretation

| Term | 中文 | Meaning | _Avoid_ | Aliases |
| :-- | :-- | :-- | :-- | :-- |
| Arena | 评测场 | Runs games under specified players, openings, seeds, and budgets while retaining replayable results. | A strength guarantee | — |
| Benchmark series | 基准系列 | Frozen reference entrants, opening book, rules and rating method defining a local comparison scale. | A universal Elo scale | BenchmarkSeries |
| Benchmark entrant | 基准参赛者 | One pinned player implementation, resource identity and configuration rated as a distinct participant. | A mutable checkpoint nickname | Entrant |
| Benchmark spec | 基准规格 | A series plus frozen candidates, paired starts and the planned matchups for one execution. | Observed game outcomes | BenchmarkSpec |
| Rating snapshot | 等级分快照 | An immutable dated projection of verified complete pairs, including uncertainty and evidence identity. | Raw outcome authority | BenchmarkSummary |
| Opening book | 开局库 | Sourced replayable prefixes selected before matches to vary starting situations. | Moves chosen by the evaluated player | Book |
| Reference panel | 参照组 | Frozen benchmark entrants against which new candidates are compared. | Known true strengths | references |
| Evaluation spec | 评测规格 | A versioned protocol, fixed corpus, and participant configurations defining what an evaluation measures. | A score without its benchmark conditions | EvalSpec; spec_sha256 |
| Evaluation run | 评测运行 | Recorded execution evidence for every planned game, including completion and failures. Summaries can be recomputed without playing again. | A cached summary as outcome authority | EvalRun |
| Evaluation summary | 评测摘要 | Versioned metrics derived from validated run evidence, linked to the spec identity and completion status. | A universal engine ranking | EvalSummary |
| Game score rate | 对局得分率 | Wins plus half the draws divided by games in complete color pairs, from the named participant's view. No complete pair means unavailable. | Win probability or Elo rating | score_rate; A score; game-score-v1 |
| Pair completion | 配对完成度 | Completed color pairs compared with all planned pairs. Incomplete pairs contribute no game score. | Counting a single finished partner as a scored pair | completed_pairs; planned_pairs; Pairs done / planned |
| Failed games | 失败对局 | Planned games whose execution failed. They remain visible and are never scored as draws. | Referee-adjudicated losses | failed_games |
| Experiment catalog | 实验目录 | Shared discovery projection of questions, findings, conditions and evidence links in owning work items or reports. Missing artifacts or unsupported run formats do not erase a registered finding. | A second conclusion authority or proof that unregistered work never happened | experiment-catalog; prior work |
| Experiment plan | 实验计划 | The frozen question and matrix of corpus positions, recipes, budgets, seeds, and comparisons to execute. | Results already obtained | plan; preview; question; name; order |
| Experiment run | 实验运行 | One execution of a plan with its environment, saved units, and status. A run can stop before the planned matrix finishes. | Assuming a run is complete | run |
| Experiment task | 实验执行任务 | A local function or script adapted to the accepted minimal run/evaluation boundary, retaining its domain configuration and correctness rules. The general boundary is not yet implemented. | A universal workflow language or automatic integration approval | — |
| Matrix | 实验组合矩阵 | All planned combinations of positions, players, budgets, and seeds, plus selected paired games. A time limit may leave some combinations missing. | Equally sampled results when units are missing | comparison matrix; planned |
| Corpus | 局面集 | The fixed collection of saved positions used for evaluation. Its identity and provenance travel with the plan. Selected examples are not necessarily representative of all play. | Automatically representative benchmark data | corpus; purpose |
| Opening | 起始局面 | Legacy evaluation name for a saved starting position, including midgame or tactical positions. New Training Data vocabulary uses Starting position; the existing corpus fields retain their meaning. | The opening game phase | openings; opening_id; game_openings |
| Probe | 单局面测试 | One move decision from one fixed position under one configuration. It tests local behavior without playing a whole game. | A complete match | probes; Fixed-position probes |
| Recorded unit | 实验记录单元 | One planned probe or game, with its exact job settings, saved decisions, final saved position, and status. | A whole experiment run | unit; units; job; unit_id |
| Turn record | 着法记录 | One saved actual decision: ply number, color, selected move, identity guard, and diagnostics. | A pair of turns | turns; choice |
| Match | 对局 | An actual game between configured players, continued until a referee outcome or an explicit interruption. | An MCTS simulation | game; games; match; matches |
| Player A | 对比方 A | The first recipe in a matchup. Its color is swapped across paired games; A is not always Red. | Red in every game | a; player_a; a_side |
| Player B | 对比方 B | The second recipe in a matchup. It plays the opposite color from A in each paired game. | Black in every game | b; player_b |
| Paired-color outcomes | 换色配对结果 | Each opening and configuration is played in both color assignments. Only two completed partner games enter paired totals, reducing dependence on who played Red. | Including a game whose partner is unfinished | paired-color; paired games; color pairs; pairs |
| Unpaired completed games | 未配对的完整对局 | Games that reached a referee outcome but whose opposite-color partner is missing or unfinished. They are excluded from paired-color totals. | A complete color pair | unpaired_completed_games |
| W/D/L | 胜／和／负 | Wins, draws, and losses from the named player's viewpoint. The matchup table reports Player A's results. | Red's results regardless of Player A's color | wins; losses; A wins / draws / losses |
| Sample | 样本 | A measured probe or game. The denominator matters: a few selected samples cannot support a general strength claim. | The whole population | samples; sample counts; Samples / planned; expected |
| Seed | 随机种子 | An integer controlling reproducible pseudo-random choices. The same algorithm, state, settings, and seed should reproduce deterministic decisions, not elapsed timing. | A source of extra playing strength | seeds |
| Configuration | 配置 | The exact player recipe, applicable seed and search settings, and any checkpoint identity used for a decision. A player binding also pins external-engine resources when that player is selected. | Informal player labels alone | config; settings |
| Immediate win | 一步获胜 | A move whose successor is a winning referee outcome immediately. These targets are exhaustively checked over legal moves; they are not teacher guesses. | Any promising tactic | Immediate wins; winning_moves; tactical_solved; tactical_tested |
| Ground truth | 判定依据 | A result established by the declared authority for a specific question. Here only the immediate-win targets have referee-proven best-move sets; other probes do not. | Treating every engine preference as truth | — |
| Held-out evaluation | 留出评估 | Testing on positions excluded from training. Board/turn inputs and relevant history prefixes must be reserved to prevent leakage. | Training examples presented as unseen tests | held-out |
| Generalization | 泛化 | Performing well on new examples beyond those used to learn or select a method. A tiny fixed corpus does not establish this. | Memorization or successful serialization | general strength; playing strength |
| Elo | 等级分 | A relative rating inferred from match results under a rating model. This report does not estimate Elo from its small selected sample. | A directly measured absolute skill score | — |
| Completion | 完成范围 | A completed probe has one saved decision; a completed game has a referee outcome. A complete trace records all explored work even if the search itself hit its budget. Read which object the flag describes. | Equating trace completeness with solved game or completed run | complete; completed; completion |
| Partial run | 部分运行 | Some planned work is unfinished or unstarted. Completed evidence remains usable with its missing coverage stated; partial games do not become draws. | Labeling the full matrix complete | incomplete; partial; partial game |
| Run status | 运行状态 | Whether execution is running, complete, at its deadline, failed, or interrupted. The report derives completed unit counts from files rather than trusting the status counter alone. | A scientific success/failure conclusion | status; running; failed; interrupted |
| Failure reason | 失败或停止原因 | The recorded explanation for an error, interruption, cutoff, or game outcome. Interpret it with the surrounding record type. | Treating every reason as a game result | error; reason; interruption; termination_reasons |
| Verification | 证据校验 | Replaying saved moves and checking states, outcomes, identities, and search accounting before showing results. This validates the recorded pipeline, not playing strength. | Held-out model evaluation | validation; verified |
| Summary | 汇总 | Values recomputed from the saved evidence, such as means or paired outcomes. Summaries are useful views; raw units and their validation remain the basis. | A separate source of results | summary |

## Traces, files, and software

| Term | 中文 | Meaning | _Avoid_ | Aliases |
| :-- | :-- | :-- | :-- | :-- |
| Search trace | 搜索轨迹 | An optional recording of the work actually explored for one decision. It is separate from benchmark timing and from the entire possible game tree. | All possible continuations | trace; traces; recording; All explored work |
| Trace event | 轨迹事件 | One recorded search action or scope, with an event ID, parent, kind, and relevant values. Execution events can revisit the same board. | One unique board per event | events; event |
| Trace capacity | 轨迹容量 | The maximum events the recorder may retain. Hitting this limit stops recording, not search, and makes the trace explicitly incomplete. | Silently calling a truncated trace full | event_limit; limit; dropped_events; omitted events; truncation |
| Parity | 一致性 | Agreement between the saved untraced decision and its traced rerun for the move and every deterministic diagnostic. Timing is deliberately excluded. | Independent proof of every heuristic score | decision_equal; deterministic parity |
| Diagnostics | 诊断指标 | Recorded details explaining how a decision used work, depth, scores, or search statistics. These help interpret behavior but do not by themselves prove strength. | Outcomes or model quality | search_stats; diagnostics |
| Provenance | 来源记录 | The recorded origins and conditions of evidence: plan, corpus, code identity, versions, seeds, and environment. It helps identify what was actually compared. | A guarantee of authorship | provenance |
| Manifest | 运行清单 | The run's saved plan and provenance, including content digests and runtime allowance. It describes the experiment that produced the units. | A mutable dashboard setting | manifest |
| Artifact | 产物文件 | A saved output such as a run record, trace, or HTML report. Local artifacts here live under the ignored artifacts directory. | An authoritative result merely because it is a file | artifacts; path |
| Projection | 派生视图 | A view generated from another source, such as the report from verified units or these tooltips from the glossary. Regenerating the view does not change the original experiment. | A new source of truth | derived view |
| Hash | 哈希指纹 | A compact fingerprint computed from content. Matching hashes identify matching content under the hash scheme; they do not prove authorship or prevent someone replacing all records. | A digital signature | hashes; fingerprint; digest; sha256 |
| SHA-256 | SHA-256 哈希算法 | The fingerprint algorithm used for source, corpus, plan, unit, and checkpoint identities. A changed digest signals changed input content. | Encryption or a signed certificate | source_sha256; corpus_sha256; plan_sha256; unit_sha256; checkpoint_sha256; glossary_sha256 |
| Identifier | 标识符 | A name or lookup key for an item. A logical scenario or recipe name can remain stable across revisions; a fingerprint can serve as a content-derived key for one exact revision. | Assuming a logical name fixes content | id; label; description; kind |
| Schema version | 格式版本 | The version of a saved record's structure and interpretation. Readers reject unsupported formats rather than guessing their meaning. | A player algorithm version | schema_version |
| Player version | 行棋算法版本 | An identifier for a recipe's decision or budget semantics. It is more precise than the recipe's display name. | The general qi package version | version; player_version; player_versions |
| JSON | JSON 数据格式 | JavaScript Object Notation: the structured text format used for raw records. Keys name fields; arrays contain lists; null means no value is present. | Executable instructions | raw decision evidence; raw units; null |
| HTML | HTML 网页格式 | The document format of this report. It embeds its data, styles, scripts, and glossary so it can be read locally without a service. | A live connection to the runner | — |
| CLI | 命令行接口 | Command-line interface: the terminal commands used to preview, run, verify, report, or inspect experiments. A local HTML file cannot execute those commands for you. | A button that silently runs searches | command line |
| Git revision | Git 修订版本 | A saved source-control commit. Dirty working-tree edits can exist beyond that commit, so the run also records a source-content digest. | Complete identity of uncommitted code | commit; revision |
| Working tree | 工作区 | The local source files, including changes not yet committed to Git. The manifest records dirty state as additional provenance. | A search tree | working_tree |
| Runtime environment | 运行环境 | Python version, package versions, operating platform, and related conditions used to run the experiment. They can affect compatibility and timing. | Search configuration alone | platform; packages; environment |
| Python | Python 编程语言 | The language/runtime used by the referee, search, and experiment runner. Its recorded version is checked when rerunning a traced decision. | A player algorithm | python |
| Pydantic | Pydantic 数据校验库 | The Python library used to validate structured inputs and records against their declared shapes and types. It does not judge move quality. | The referee | pydantic |
| Qi | Qi 项目 | This local game-learning laboratory and software package. Its package version alone is not the full identity of the source used in an experiment. | Xiangqi's rulebook | qi |
| Elapsed time | 已用时间 | Wall-clock duration measured during execution. It includes time spent waiting or scheduling; it is not a hardware-independent amount of computation. | Exact CPU time | seconds; elapsed_seconds |
| Index | 序号 | A position in an ordered list. The inspect command's turn_index starts at zero, while recorded game ply numbers start at one. | Interchanging zero-based indices and plies | turn_index |
| Timestamp | 时间戳 | A recorded point in time, such as when a run started. Unlike elapsed time, it names a moment rather than a duration. | Run duration | started_at |
| Trace scope status | 轨迹步骤状态 | Whether a recorded search scope was entered, finished, or interrupted. Entered means execution began; complete means that scope returned, not that the game ended. | Run status or game outcome | entered |
| Extension depth change | 延伸深度变化 | Ordinary search depth before and after a check extension. The extra ply still consumes the shared visit budget. | Elapsed time | before; after |
| Atomic write | 原子写入 | Writing a temporary file, then replacing the target once the write is ready. This helps readers avoid treating a half-written file as complete evidence. | A guarantee that an entire run finishes | — |

## Learning track

| Term | 中文 | Meaning | _Avoid_ | Aliases |
| :-- | :-- | :-- | :-- | :-- |
| Trainer | 训练器 | Code that updates model weights from data. It is separate from the player that later uses those weights to choose moves. | Search | — |
| Policy | 策略分布 | A mapping from a position to move preferences or probabilities. A policy may be hand-written or learned; it is not a synonym for every player. | The whole automated player interface | policy |
| Value model | 价值模型 | A learned estimator of a position's result or desirability for a stated player. Learned value estimation remains a later direction here. | The current hand-set evaluator | value head |
| Teacher | 教师引擎 | An external engine used to provide analysis or move labels. It is not the authority for qi's rules and is not implicitly available to evaluated players. | Referee or player tool access by default | teacher |
| Teacher query | 教师查询 | One request to analyze a position with its full history and return a move under specified search limits. A query can guide play without becoming a retained training example. | One node or necessarily one training example | — |
| Teacher node limit | 教师节点上限 | The requested cap on engine-counted search work per query. Reported work can overshoot; these nodes are not qi's charged visits or unique boards. A higher cap permits more work if another limit does not stop search first. | Guaranteed node count or elapsed time | requested_nodes |
| Teacher depth limit | 教师深度上限 | The requested ordinary search depth in plies per query: depth 6 means six half-moves, not six move pairs. Selective search can explore branches unevenly; another limit may stop it earlier. | Every branch searched exactly six plies | requested_depth |
| Teacher hash memory | 教师搜索缓存内存 | RAM assigned to an engine's transposition table, which caches search results. Pikafish's UCI Hash option sets MiB per process; it excludes network and other process memory. This search-cache concept is shared by other engines. | The SHA-256 content fingerprint or all worker RAM | hash memory; hash_mb |
| Mebibyte | 二进制兆字节 | A memory unit equal to 1,048,576 bytes (1024 squared). A 16 MiB hash table occupies 16,777,216 bytes. | Decimal MB, which is 1,000,000 bytes | MiB |
| Teacher worker | 教师工作进程 | An independent engine process serving queries. A persistent worker keeps its process and network loaded between queries; search-state reset is a separate policy. | A CPU thread or an implemented persistent pool by default | persistent worker |
| Teacher threads | 教师搜索线程数 | CPU threads cooperating on one worker's search. Workers times threads approximates search concurrency; more threads can change search work and selected moves. | Number of independent queries | Threads |
| Query throughput | 查询吞吐量 | Successful teacher queries divided by wall-clock seconds across all workers. State whether startup and validation are timed; this differs from nodes per second and retained examples per second. | Per-query latency or label quality | queries/s; queries per second |
| Principal variation | 主要变化 | A candidate move followed by the engine's analyzed continuation. | A complete search tree | PV |
| MultiPV | 多主要变化搜索 | Engine search for several leading principal variations. More candidates change search allocation; this is not just printing more of an unchanged search. | Display-only candidate count | — |
| WDL estimate | 胜和负估计 | Modeled win/draw/loss chances conditional on a candidate move and engine continuation, from the root player's perspective. Pikafish emits three integers summing to 1000 per line. | Move-selection probabilities or verified student win rates | UCI_ShowWDL |
| Root-move trace | 根着法观测记录 | Observations of ordinary search effort and score evidence per candidate, preserving unknown values, bounds, depths and older estimates. The local prototype performs no extra searches. | An exact top-five ranking | roottrace |
| Exact-window score | 搜索窗口内估值 | A returned search estimate inside its alpha-beta window, rather than an upper or lower bound. It remains specific to its search and may be stale. | Proven game value | — |
| Jensen–Shannon divergence | Jensen–Shannon 散度 | Symmetric discrepancy between distributions; the pilot compares each move's WDL against the same move under a reference. With base-2 logarithms it ranges from 0 to 1; lower is closer. | Accuracy or proof of calibration | JSD |
| Kendall's tau-b | Kendall 等级相关系数 | Ranking correlation accounting for ties, ranging from -1 to 1; higher means closer rankings. Undefined when there are no comparable ranks. | A distance where lower is better | tau-b |
| Teacher imitation | 教师模仿 | Training a policy to predict a teacher's selected legal move. Agreement on training examples alone does not demonstrate held-out skill. | Proven playing strength | — |
| Checkpoint | 模型检查点 | A saved model architecture/metadata and weight state used for inference. Its digest identifies the particular weights loaded by a process. | A training dataset | checkpoint |
| Inference | 推理计算 | Applying fixed learned weights to an input to obtain predictions. It does not update the model's weights. | Training | — |
| Legal masking | 合法着法掩码 | Excluding illegal moves from the policy's available outputs or training loss. Legal output does not imply a strong move. | Learned rules correctness | legal mask |
| Logit | 未归一化分数 | A model's raw score for an action before conversion into probabilities. It is not already a probability. | Win probability | logits |
| Cross-entropy | 交叉熵 | The policy training loss that penalizes assigning too little probability to the teacher's chosen legal move. Lower training loss alone does not prove generalization. | Match outcome score | loss |
| Overfitting | 过拟合 | Learning the training examples well without transferring that performance to unseen inputs. A tiny overfit can still diagnose whether optimization works. | Held-out success | memorization |
| Self-play | 自我对弈 | Generating games with current players/models to supply data for later learning. A self-play improvement loop is a planned direction. | Any recorded arena game | self-play |
| SFT | 监督微调 | Supervised fine-tuning: updating a pretrained model using desired examples. The LLM SFT track remains planned. | Reinforcement learning | — |
| Reinforcement learning | 强化学习 | Updating behavior using rewards or outcomes rather than only imitating a supplied answer. It remains a later learning direction in qi. | Current search-only comparisons | RL |
| LLM | 大语言模型 | A large language model that could be evaluated or trained to choose moves or use tools. The detailed LLM experiment interface remains undecided. | The current alpha-beta or MCTS player | large language model |


## Training Data

These terms describe the accepted [core model](../models.md). The
[Training Data guide](../../src/qi/training_data/README.md) identifies implemented
formats and later extensions. Existing MCTS Rollout and legacy evaluation Opening
fields keep their current contracts.

| Term | 中文 | Meaning | _Avoid_ | Aliases |
| :-- | :-- | :-- | :-- | :-- |
| Training Data | 训练数据上下文 | The bounded context that owns example selection, supervision provenance and dataset composition for trainers. | Weight optimization | — |
| Dataset preparation | 数据集制备 | Generates trajectories, supplies supervision and freezes an assembled dataset under a saved preparation config. | GT generation | PreparationConfig |
| Generation mode | 轨迹生成模式 | The move chooser used to produce a continuation: currently random or teacher-guided. It does not choose the supervision authority. | Ground-truth mode | mode |
| Teacher supervision | 教师监督 | Teacher-preference move targets under pinned engine, network and search settings. The teacher need not be the actor that played the game. | Ground truth; proven best move | SupervisionSettings; supervision |
| Trajectory source | 轨迹来源 | Produces or replays a game with its actor and origin recorded. | The supervision provider | — |
| Continuation | 对局续行 | Additional play from a stated starting position under declared limits and move choosers. | An MCTS Rollout by default | — |
| Position sampler | 局面采样器 | Selects positions from trajectories under explicit conditions and budgets. | Choosing the next game move | — |
| Position occurrence | 局面出现记录 | A position at an exact absolute ply in a source trajectory, retaining replay history and provenance. | A unique board alone | position_occurrences |
| Semantic tag | 语义标签 | A versioned descriptive predicate on a position or its selected teacher move, independent of inherited source themes. | A proved tactic or a scalar quality score | semantic_tags |
| Input exclusion | 输入排除项 | A recorded decision omitting a model observation from selection while retaining its original evidence. | A reserved evaluation opening | excluded_inputs |
| Analysis attempt | 分析尝试 | One execution on a recorded state under a supervision specification, retaining success, failure or interruption independently of other attempts. | A reusable request; the definitive label | analyses |
| Frozen training snapshot | 冻结训练快照 | Materialized validated inputs and selected targets with source evidence and policies, unchanged by later collection updates. | A live SQL view | — |
| Starting position | 起始局面 | The replay-backed state from which a continuation, probe or match begins; it can belong to any game phase. | Opening phase | — |
| Game phase | 对局阶段 | A board-based opening, middlegame, endgame or unknown classification under a named policy, with curated labels recorded separately by provenance. | A ply-number range | — |
| Theme | 局面主题 | A descriptive category such as cannon tactics or defending against check; several themes may apply to one position. | A mutually exclusive game phase | — |
| Scenario | 场景 | A named selection of positions and descriptive tags, optionally with an objective and answer authority. | An implied proven solution | — |
| Sampling window | 采样窗口 | The part of a trajectory eligible for position selection. | The continuation's stopping limit | — |
| Supervision provider | 监督提供方 | Supplies a training target with its specification and answer authority. | The actor that played the observed move | — |
| Supervision specification | 监督规格 | The target contract and teacher or answer-authority configuration that determine how a label is interpreted. | Unqualified ground truth | — |
| Labeled example | 带标注样本 | A replayable state paired with a target and its supervision specification, retaining source provenance. | An unlabeled state | — |
| Quota bucket | 配额分组 | One explicit mixture group to which a retained example contributes once. | Every overlapping descriptive tag | — |
| Source family | 来源族 | Related variations and continuations kept together for splitting; independent games sharing only the standard initial board remain separate families. | Every game with the same initial board | — |
| Dataset manifest | 数据集清单 | A frozen selection of example references and their order, splits, quota membership, recipe, seed and governing policy versions. | An execution-timing record | — |
| State fingerprint | 状态指纹 | A content fingerprint of the ruleset, starting state and full recorded history. Existing state_hash is the current replay identity. | A board-only observation fingerprint | — |
| Observation fingerprint | 观测指纹 | A content fingerprint of a versioned model-observation scheme and its exposed input. | Full-history state identity | — |
| Example fingerprint | 样本指纹 | A content fingerprint of a state, supervision specification and target, used to reference one labeled example. | A state fingerprint alone | — |
| Dataset fingerprint | 数据集指纹 | A content fingerprint of the canonical frozen dataset manifest. Existing dataset digests have their own unchanged versioned semantics. | A logical dataset name | — |
