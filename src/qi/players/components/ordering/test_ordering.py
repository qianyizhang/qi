"""Move hints never remove actions, and cutoff memory is local to one search."""

from qi_game.reference import Game, legal_moves

from qi.players.common import NodeBudget
from qi.players.components.ordering import MoveOrdering


def test_preferred_move_precedes_captures_and_all_legal_moves_remain():
    ordered = MoveOrdering().moves(Game(), 0, NodeBudget(100), "b2e2")
    assert ordered[0] == "b2e2"
    assert len(ordered) == len(set(ordered)) == len(legal_moves(Game().board, "red"))


def test_killers_and_history_promote_quiet_cutoffs_without_training():
    orderer = MoveOrdering()
    orderer.cutoff(Game(), "b2e2", 2, 3)
    orderer.cutoff(Game(), "h2e2", 2, 2)
    assert orderer.killers[2] == ["h2e2", "b2e2"]
    quiet = [move for move in orderer.moves(Game(), 2, NodeBudget(1)) if move not in ("b2b9", "h2h9")]
    assert quiet[:2] == ["h2e2", "b2e2"]
    assert orderer.history[("red", "b2e2")] == 9
    assert MoveOrdering().history == {}


def test_exchange_ordering_defers_poisoned_captures():
    budget = NodeBudget(100)
    ordered = MoveOrdering(use_exchange=True).moves(Game(), 0, budget)
    assert ordered.index("b2b9") > ordered.index("b2e2")
    assert budget.see_nodes > 0
