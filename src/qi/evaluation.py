"""Fixed opening batches with paired colors and auditable player-relative totals."""

from collections import Counter
from dataclasses import replace
from hashlib import sha256
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qi.arena import MatchRecord, play_match
from qi.game import GameError, Side
from qi.players import PlayerConfig, bind_config
from qi.protocol import Snapshot


class Opening(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1, pattern=r"^[a-z0-9-]+$")  # SAMPLE: central-cannon
    description: str = Field(min_length=1)
    snapshot: Snapshot


class Corpus(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    purpose: Literal["evaluation"] = "evaluation"
    provenance: str = Field(min_length=1)
    openings: list[Opening] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_openings(self) -> Self:
        ids, states = set(), set()
        for opening in self.openings:
            game = opening.snapshot.game()
            if game.outcome:
                raise ValueError(f"Terminal opening: {opening.id}")
            if opening.id in ids or game.state_hash in states:
                raise ValueError("Opening IDs and full-history states must be unique.")
            ids.add(opening.id)
            states.add(game.state_hash)
        return self

    @property
    def digest(self) -> str:
        return sha256(self.model_dump_json().encode()).hexdigest()


class EvaluationGame(BaseModel):
    opening_id: str
    a_side: Side
    match: MatchRecord


class PlayerSummary(BaseModel):
    wins: int
    draws: int
    losses: int
    decisions: int
    nodes: int
    mean_completed_depth: float
    elapsed_ms: float
    mean_elapsed_ms: float
    invalid_actions: int = 0
    retries: int = 0
    qnodes: int = 0
    max_qply: int = 0
    model_calls: int = 0
    simulations: int = 0
    rollout_steps: int = 0
    terminal_simulations: int = 0
    heuristic_cutoffs: int = 0
    max_tree_depth: int = 0


class EvaluationRecord(BaseModel):
    schema_version: Literal[1] = 1
    corpus: Corpus
    corpus_sha256: str
    player_a: PlayerConfig
    player_b: PlayerConfig
    games: list[EvaluationGame]
    summary: dict[str, PlayerSummary]
    termination_reasons: dict[str, int]


def summarize(games: list[EvaluationGame], player: Literal["a", "b"]) -> PlayerSummary:
    wins = draws = losses = nodes = depth = decisions = 0
    elapsed = 0.0
    qnodes = max_qply = 0
    model_calls = 0
    simulations = rollout_steps = terminal_simulations = heuristic_cutoffs = max_tree_depth = 0
    for entry in games:
        side = entry.a_side if player == "a" else ("black" if entry.a_side == "red" else "red")
        result = entry.match
        if result.winner is None:
            draws += 1
        elif result.winner == side:
            wins += 1
        else:
            losses += 1
        for turn in result.turns:
            if turn.side == side:
                decisions += 1
                nodes += turn.choice.nodes
                qnodes += turn.choice.qnodes
                model_calls += turn.choice.model_calls
                if (stats := turn.choice.mcts) is not None:
                    simulations += stats.simulations
                    rollout_steps += stats.rollout_steps
                    terminal_simulations += stats.terminal_simulations
                    heuristic_cutoffs += stats.rollout_cutoffs + stats.budget_cutoffs
                    max_tree_depth = max(max_tree_depth, stats.max_tree_depth)
                max_qply = max(max_qply, turn.choice.max_qply)
                depth += turn.choice.completed_depth
                elapsed += turn.choice.elapsed_ms
    return PlayerSummary(
        qnodes=qnodes,
        max_qply=max_qply,
        model_calls=model_calls,
        simulations=simulations,
        rollout_steps=rollout_steps,
        terminal_simulations=terminal_simulations,
        heuristic_cutoffs=heuristic_cutoffs,
        max_tree_depth=max_tree_depth,
        wins=wins,
        draws=draws,
        losses=losses,
        decisions=decisions,
        nodes=nodes,
        mean_completed_depth=depth / decisions if decisions else 0,
        elapsed_ms=elapsed,
        mean_elapsed_ms=elapsed / decisions if decisions else 0,
    )


def evaluate_batch(corpus: Corpus, a: PlayerConfig, b: PlayerConfig) -> EvaluationRecord:
    # CONTRACT: Preflight every opening before starting any match, including direct callers.
    corpus = Corpus.model_validate(corpus.model_dump())
    a, b = bind_config(a), bind_config(b)
    games = []
    for index, opening in enumerate(corpus.openings):
        pair_a, pair_b = replace(a, seed=a.seed + 2 * index), replace(b, seed=b.seed + 2 * index)
        for a_side in ("red", "black"):
            red, black = (pair_a, pair_b) if a_side == "red" else (pair_b, pair_a)
            match = play_match(red, black, opening.snapshot.game())
            outcome = match.snapshot.game().outcome
            if outcome is None or (outcome.winner, outcome.reason) != (match.winner, match.reason):
                raise GameError("invalid_match", "Match result does not agree with replay.")
            games.append(EvaluationGame(opening_id=opening.id, a_side=a_side, match=match))
    return EvaluationRecord(
        corpus=corpus,
        corpus_sha256=corpus.digest,
        player_a=a,
        player_b=b,
        games=games,
        summary={player: summarize(games, player) for player in ("a", "b")},
        termination_reasons=dict(Counter(entry.match.reason for entry in games)),
    )
