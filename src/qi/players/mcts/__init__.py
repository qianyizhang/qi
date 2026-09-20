"""UCT selection, bounded random rollouts, and side-to-move value backup."""

from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass, field
from math import isfinite, log, sqrt
from random import Random

from qi_game.core import GameError
from qi_game.reference import Game, legal_moves

from qi.players.common import BudgetExhausted, NodeBudget, evaluate
from qi.players.core import Decision, MctsStats, Player, PlayerConfig, PlayerInfo, RootMove
from qi.players.trace import enabled, event, note, span, traced

LeafEvaluator = Callable[[Game], float]
BudgetedLeafEvaluator = Callable[[Game, NodeBudget], float]


def material_value(game: Game) -> float:
    score = evaluate(game)
    return score / (abs(score) + 900)


def value(game: Game, leaf: LeafEvaluator) -> float:
    if (outcome := game.outcome) is not None:
        if outcome.winner is None:
            return 0.0
        return 1.0 if outcome.winner == game.turn else -1.0
    estimate = leaf(game)
    if not isfinite(estimate) or not -1 <= estimate <= 1:
        raise GameError("invalid_evaluator", "MCTS leaf values must be finite and in [-1, 1].")
    return estimate


@dataclass
class Node:
    game: Game
    untried: list[str]
    children: dict[str, "Node"] = field(default_factory=dict)
    visits: int = 0
    total_value: float = 0.0

    @classmethod
    def create(cls, game: Game, rng: Random) -> "Node":
        moves = [] if game.outcome else sorted(legal_moves(game.board, game.turn))
        rng.shuffle(moves)
        return cls(game, moves)

    @property
    def mean_value(self) -> float:
        return self.total_value / self.visits if self.visits else 0.0

    def select_child(self) -> "Node":
        # INVARIANT: Child values belong to the opponent; negate before maximizing UCT.
        return max(
            sorted(self.children.items()),
            key=lambda item: -item[1].mean_value + sqrt(2 * log(self.visits) / item[1].visits),
        )[1]


def backup(path: list[Node], estimate: float) -> None:
    """The estimate initially belongs to the final tree node's side to move."""
    for node in reversed(path):
        node.visits += 1
        node.total_value += estimate
        event("backup", node.game, visits=node.visits, mean_value=node.mean_value, backed_value=estimate)
        estimate = -estimate


@dataclass
class Search:
    budget: NodeBudget
    rng: Random
    rollout_plies: int
    leaf: LeafEvaluator = material_value
    tree_visits: int = 0
    rollout_steps: int = 0
    terminal_simulations: int = 0
    rollout_cutoffs: int = 0
    budget_cutoffs: int = 0
    unfinished_simulations: int = 0
    max_tree_depth: int = 0
    budgeted_leaf: BudgetedLeafEvaluator | None = None
    leaf_aborts: int = 0

    def visit_tree(self) -> None:
        self.budget.visit()
        self.tree_visits += 1

    @traced("rollout")
    def rollout(self, start: Game) -> float:
        game = start
        steps = 0
        trace_parent = None
        while not game.outcome and steps < self.rollout_plies and self.budget.nodes < self.budget.limit:
            self.budget.visit()
            self.rollout_steps += 1
            steps += 1
            game = game.apply(self.rng.choice(sorted(legal_moves(game.board, game.turn))))
            if trace_parent is None:
                trace_parent = event("rollout-step", game, step=steps)
            else:
                trace_parent = event("rollout-step", game, step=steps, parent=trace_parent)
        estimate = (
            value(game, lambda position: self.budgeted_leaf(position, self.budget))
            if self.budgeted_leaf
            else value(game, self.leaf)
        )
        note(leaf_board=game.board, leaf_side=game.turn, leaf_value=estimate)
        if game.outcome:
            note(reason="terminal")
            self.terminal_simulations += 1
        elif steps == self.rollout_plies:
            note(reason="rollout-limit")
            self.rollout_cutoffs += 1
        else:
            note(reason="work-limit")
            self.budget_cutoffs += 1
        return estimate if game.turn == start.turn else -estimate

    def run(self, root: Node) -> MctsStats:
        while self.budget.nodes < self.budget.limit:
            with ExitStack() as scopes:
                scopes.enter_context(span("simulation", root.game, simulation=root.visits + 1))
                self.visit_tree()
                node, path = root, [root]
                while not node.game.outcome and self.budget.nodes < self.budget.limit:
                    self.visit_tree()
                    if node.untried:
                        move = node.untried.pop()
                        child = Node.create(node.game.apply(move), self.rng)
                        node.children[move] = child
                        node = child
                        path.append(node)
                        scopes.enter_context(span("expansion", node.game, unsearched_moves=node.untried.copy()))
                        break
                    node = node.select_child()
                    path.append(node)
                    scopes.enter_context(span("selection", node.game, visits=node.visits, mean_value=node.mean_value))
                if len(path) == 1:
                    self.unfinished_simulations += 1
                    note(reason="root-only", backed_up=False)
                    break
                self.max_tree_depth = max(self.max_tree_depth, len(path) - 1)
                try:
                    estimate = self.rollout(node.game)
                except BudgetExhausted:
                    self.unfinished_simulations += 1
                    self.leaf_aborts += 1
                    note(reason="discarded-leaf", backed_up=False)
                    break
                backup(path, estimate)
                note(backed_up=True)
        roots = tuple(
            RootMove(move, child.visits, -child.mean_value)
            if (child := root.children.get(move)) and child.visits
            else RootMove(move, 0, None)
            for move in sorted(legal_moves(root.game.board, root.game.turn))
        )
        return MctsStats(
            root.visits,
            self.tree_visits,
            self.rollout_steps,
            self.terminal_simulations,
            self.rollout_cutoffs,
            self.budget_cutoffs,
            self.unfinished_simulations,
            self.max_tree_depth,
            roots,
            self.budget.nodes - self.tree_visits - self.rollout_steps,
            self.leaf_aborts,
        )


def search(
    game: Game,
    config: PlayerConfig,
    leaf: LeafEvaluator = material_value,
    *,
    budgeted_leaf: BudgetedLeafEvaluator | None = None,
) -> Decision:
    if game.outcome:
        raise GameError("game_over", "Cannot search a terminal game.")
    rng = Random(config.seed)
    root = Node.create(game, rng)
    worker = Search(NodeBudget(config.nodes), rng, config.rollout_plies, leaf, budgeted_leaf=budgeted_leaf)
    stats = worker.run(root)
    if enabled():
        pending = [(root, None)]
        while pending:
            node, parent = pending.pop()
            key = event(
                "mcts-tree",
                node.game,
                parent=parent,
                visits=node.visits,
                mean_value=node.mean_value,
                unsearched_moves=node.untried.copy(),
            )
            pending.extend((child, key) for child in reversed(list(node.children.values())))
    # Coordinate order breaks ties; unvisited moves never outrank a completed sample.
    best = max(stats.root_moves, key=lambda move: (move.visits, move.mean_value if move.mean_value is not None else -2))
    return Decision(
        best.move, nodes=worker.budget.nodes, qnodes=worker.budget.qnodes, max_qply=worker.budget.max_qply, mcts=stats
    )


def select(game: Game, config: PlayerConfig) -> Decision:
    return search(game, config)


PLAYER = Player(
    PlayerInfo(
        "mcts",
        "mcts-uct-v1",
        "MCTS · UCT",
        "Tree search with random rollouts and material cutoffs.",
        True,
        default_nodes=512,
        default_rollout_plies=8,
    ),
    select,
)
