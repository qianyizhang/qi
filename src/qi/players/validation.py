"""Pure decision invariants shared by live players and saved evidence readers."""

from math import isfinite

from qi.game import Game, legal_moves
from qi.players.core import Choice, Decision, PlayerConfig


def validate_decision(decision: Decision | Choice, config: PlayerConfig, game: Game) -> None:
    """Raise ValueError at the first invalid move, budget or diagnostic invariant.

    Identity, timing, replay and protocol restrictions belong to callers. Optional
    statistics are checked when present; validation never invokes a player.
    """
    legal = set(legal_moves(game.board, game.turn))
    if decision.move not in legal:
        raise ValueError("Decision move is rejected by the referee.")
    if not 0 <= decision.qnodes <= decision.nodes <= config.nodes:
        raise ValueError("Node accounting must satisfy 0 <= qnodes <= nodes <= budget.")
    if not 0 <= decision.completed_depth <= config.depth:
        raise ValueError("Completed depth exceeds the configured depth budget.")
    if not 0 <= decision.max_qply <= decision.qnodes:
        raise ValueError("Quiescence depth must be between zero and qnodes.")
    if decision.model_calls not in (0, 1):
        raise ValueError("Model calls must be zero or one.")

    if (stats := decision.mcts) is not None:
        for field in (
            "tree_visits",
            "rollout_steps",
            "leaf_nodes",
            "simulations",
            "terminal_simulations",
            "rollout_cutoffs",
            "budget_cutoffs",
            "max_tree_depth",
        ):
            if getattr(stats, field) < 0:
                raise ValueError(f"MCTS {field} must be nonnegative.")
        if stats.tree_visits + stats.rollout_steps + stats.leaf_nodes != decision.nodes:
            raise ValueError("MCTS work does not partition total nodes.")
        if stats.simulations != stats.terminal_simulations + stats.rollout_cutoffs + stats.budget_cutoffs:
            raise ValueError("MCTS simulation totals disagree.")
        if stats.simulations != sum(row.visits for row in stats.root_moves):
            raise ValueError("Root visits disagree with simulations.")
        if stats.unfinished_simulations not in (0, 1):
            raise ValueError("MCTS unfinished_simulations must be zero or one.")
        if not 0 <= stats.leaf_aborts <= stats.unfinished_simulations:
            raise ValueError("MCTS leaf_aborts exceed unfinished simulations.")
        if stats.tree_visits < 2 * stats.simulations + stats.unfinished_simulations:
            raise ValueError("MCTS tree visits do not cover completed and unfinished simulations.")
        if stats.max_tree_depth > stats.tree_visits:
            raise ValueError("MCTS maximum tree depth exceeds tree visits.")
        roots = stats.root_moves
        if len(roots) != len({row.move for row in roots}):
            raise ValueError("MCTS root actions contain duplicates.")
        if {row.move for row in roots} != legal:
            raise ValueError("MCTS root actions differ from referee legal moves.")
        for row in roots:
            if row.visits < 0:
                raise ValueError(f"MCTS root {row.move} visits must be nonnegative.")
            if row.visits == 0:
                if row.mean_value is not None:
                    raise ValueError(f"Unvisited MCTS root {row.move} must have no mean value.")
            elif row.mean_value is None or not isfinite(row.mean_value) or not -1 <= row.mean_value <= 1:
                raise ValueError(f"Visited MCTS root {row.move} must have a finite mean value in [-1, 1].")

    if (stats := decision.search_stats) is not None:
        if not 0 <= stats.see_nodes <= decision.nodes - decision.qnodes:
            raise ValueError("Search exchange nodes overlap quiescence work or exceed total nodes.")
        if not 0 <= stats.tt_cutoffs <= stats.tt_hits <= decision.nodes:
            raise ValueError("Search cache accounting must satisfy 0 <= tt_cutoffs <= tt_hits <= nodes.")
        if not 0 <= stats.cutoffs <= decision.nodes:
            raise ValueError("Search cutoffs must be between zero and total nodes.")
        if not 0 <= stats.extensions <= decision.nodes:
            raise ValueError("Search extensions must be between zero and total nodes.")
        if not 0 <= stats.max_extensions <= 4:
            raise ValueError("Search maximum extensions must be between zero and four.")
