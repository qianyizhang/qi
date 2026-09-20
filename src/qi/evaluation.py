"""Fixed opening batches with paired colors and auditable player-relative totals."""

from collections import Counter
from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256
from math import isfinite
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from qi_game.contracts import Snapshot
from qi_game.core import GameError, Side
from qi_game.reference import restore

from qi.arena import MatchRecord, play_match
from qi.artifacts import Provenance, digest, provenance
from qi.players import PlayerConfig, bind_config
from qi.players.catalog import get_player
from qi.players.core import config_data
from qi.players.validation import validate_decision
from qi.scoring import GameScore, PairedScore, score_pairs


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
            game = restore(opening.snapshot)
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


class EvalSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1, 2] = 1
    protocol: Literal["paired-games-v1"] = "paired-games-v1"
    corpus: Corpus
    player_a: PlayerConfig
    player_b: PlayerConfig

    @property
    def digest(self) -> str:
        return digest(
            {
                **self.model_dump(mode="json"),
                "player_a": config_data(self.player_a),
                "player_b": config_data(self.player_b),
            }
        )

    def configurations(self, index: int, side: Side) -> tuple[PlayerConfig, PlayerConfig]:
        a = replace(self.player_a, seed=self.player_a.seed + 2 * index)
        b = replace(self.player_b, seed=self.player_b.seed + 2 * index)
        return (a, b) if side == "red" else (b, a)


class EvalGame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opening_id: str
    a_side: Side
    status: Literal["pending", "running", "complete", "failed", "incomplete"] = "pending"
    match: MatchRecord | None = None
    error: str | None = None

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        if (self.status == "complete") != (self.match is not None):
            raise ValueError("Only completed games must contain a match.")
        if (self.status in ("failed", "incomplete")) != (self.error is not None):
            raise ValueError("Failed or interrupted games must retain an error.")
        return self


class EvalRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1, 2] = 1
    spec: EvalSpec
    spec_sha256: str
    provenance: Provenance
    player_versions: dict[Literal["a", "b"], str]
    games: list[EvalGame]

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        expected_schema = 2 if self.spec.player_a.binding_sha256 or self.spec.player_b.binding_sha256 else 1
        if self.schema_version != self.spec.schema_version or self.schema_version != expected_schema:
            raise ValueError("Evaluation schema does not match participant binding semantics.")
        if self.spec_sha256 != self.spec.digest or set(self.player_versions) != {"a", "b"}:
            raise ValueError("Evaluation identity mismatch.")
        expected = [(opening.id, side) for opening in self.spec.corpus.openings for side in ("red", "black")]
        if [(game.opening_id, game.a_side) for game in self.games] != expected:
            raise ValueError("Run must retain every planned game exactly once in spec order.")
        for index, entry in enumerate(self.games):
            if entry.match is not None:
                self.validate_match(index // 2, entry)
        return self

    def validate_match(self, index: int, entry: EvalGame) -> None:
        match = entry.match
        opening = self.spec.corpus.openings[index].snapshot
        red, black = self.spec.configurations(index, entry.a_side)
        if match.schema_version != (2 if red.binding_sha256 or black.binding_sha256 else 1) or (
            match.red,
            match.black,
            match.opening,
        ) != (red, black, opening):
            raise ValueError("Match configuration or opening differs from spec.")
        game = restore(opening)
        for turn in match.turns:
            choice = turn.choice
            config = red if game.turn == "red" else black
            who = "a" if game.turn == entry.a_side else "b"
            if (
                game.outcome is not None
                or turn.ply != len(game.moves) + 1
                or turn.side != game.turn
                or choice.state_hash != game.state_hash
                or choice.seed != config.seed + len(game.moves)
                or choice.player_version != self.player_versions[who]
                or choice.checkpoint_sha256 != config.checkpoint_sha256
                or choice.binding_sha256 != config.binding_sha256
            ):
                raise ValueError("Match turn differs from replay or participant identity.")
            if not isfinite(choice.elapsed_ms) or choice.elapsed_ms < 0:
                raise ValueError("Invalid measured latency.")
            # Replay owns transition errors (including invalid_move/illegal_move).
            next_game = game.apply(choice.move, choice.state_hash)
            validate_decision(choice, config, game)
            game = next_game
        if (
            Snapshot(moves=list(game.moves)) != match.snapshot
            or game.outcome is None
            or (game.outcome.winner, game.outcome.reason) != (match.winner, match.reason)
        ):
            raise ValueError("Match outcome or snapshot differs from replay.")


class EvalSummary(BaseModel):
    schema_version: Literal[1] = 1
    protocol: Literal["paired-games-v1"] = "paired-games-v1"
    spec_sha256: str
    status: Literal["complete", "incomplete", "failed"]
    players: dict[Literal["a", "b"], PairedScore]


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
    leaf_nodes: int = 0
    leaf_aborts: int = 0
    see_nodes: int = 0
    search_cutoffs: int = 0
    check_extensions: int = 0
    tt_hits: int = 0
    tt_cutoffs: int = 0


class EvaluationRecord(BaseModel):
    schema_version: Literal[1] = 1
    corpus: Corpus
    corpus_sha256: str
    player_a: PlayerConfig
    player_b: PlayerConfig
    games: list[EvaluationGame]
    summary: dict[str, PlayerSummary]
    termination_reasons: dict[str, int]
    evaluation: EvalSummary | None = None


def summarize(games: list[EvaluationGame], player: Literal["a", "b"]) -> PlayerSummary:
    wins = draws = losses = nodes = depth = decisions = 0
    elapsed = 0.0
    qnodes = max_qply = 0
    model_calls = 0
    simulations = rollout_steps = terminal_simulations = heuristic_cutoffs = max_tree_depth = 0
    leaf_nodes = leaf_aborts = see_nodes = search_cutoffs = check_extensions = tt_hits = tt_cutoffs = 0
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
                if (stats := turn.choice.search_stats) is not None:
                    see_nodes += stats.see_nodes
                    search_cutoffs += stats.cutoffs
                    check_extensions += stats.extensions
                    tt_hits += stats.tt_hits
                    tt_cutoffs += stats.tt_cutoffs
                if (stats := turn.choice.mcts) is not None:
                    simulations += stats.simulations
                    rollout_steps += stats.rollout_steps
                    leaf_nodes += stats.leaf_nodes
                    leaf_aborts += stats.leaf_aborts
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
        leaf_nodes=leaf_nodes,
        leaf_aborts=leaf_aborts,
        see_nodes=see_nodes,
        search_cutoffs=search_cutoffs,
        check_extensions=check_extensions,
        tt_hits=tt_hits,
        tt_cutoffs=tt_cutoffs,
        wins=wins,
        draws=draws,
        losses=losses,
        decisions=decisions,
        nodes=nodes,
        mean_completed_depth=depth / decisions if decisions else 0,
        elapsed_ms=elapsed,
        mean_elapsed_ms=elapsed / decisions if decisions else 0,
    )


def run_evaluation(spec: EvalSpec, *, save: Callable[[EvalRun], None] | None = None) -> EvalRun:
    """Execute once, optionally saving before and after each game; stop on failure."""
    spec = EvalSpec.model_validate(spec.model_dump())
    spec = spec.model_copy(update={"player_a": bind_config(spec.player_a), "player_b": bind_config(spec.player_b)})
    if spec.player_a.binding_sha256 or spec.player_b.binding_sha256:
        spec = spec.model_copy(update={"schema_version": 2})
    run = EvalRun(
        schema_version=spec.schema_version,
        spec=spec,
        spec_sha256=spec.digest,
        provenance=provenance(),
        player_versions={
            "a": get_player(spec.player_a.kind).info.version,
            "b": get_player(spec.player_b.kind).info.version,
        },
        games=[
            EvalGame(opening_id=opening.id, a_side=side)
            for opening in spec.corpus.openings
            for side in ("red", "black")
        ],
    )
    if save:
        save(run)
    for index, entry in enumerate(run.games):
        entry.status = "running"
        if save:
            save(run)
        try:
            red, black = spec.configurations(index // 2, entry.a_side)
            match = play_match(red, black, restore(spec.corpus.openings[index // 2].snapshot))
            complete = EvalGame(opening_id=entry.opening_id, a_side=entry.a_side, status="complete", match=match)
            run.validate_match(index // 2, complete)
            run.games[index] = complete
        except (Exception, KeyboardInterrupt) as exc:
            entry.status = "incomplete" if isinstance(exc, KeyboardInterrupt) else "failed"
            entry.error = f"{type(exc).__name__}: {exc}"
        if save:
            save(run)
        if run.games[index].status in ("failed", "incomplete"):
            break
    return run


def summarize_evaluation(run: EvalRun) -> EvalSummary:
    """Revalidate saved evidence and derive scores without invoking players."""
    run = EvalRun.model_validate(run.model_dump())
    players = {}
    for player in ("a", "b"):
        games = []
        for entry in run.games:
            result = None
            turns = []
            if entry.match is not None:
                side = entry.a_side if player == "a" else ("black" if entry.a_side == "red" else "red")
                winner = entry.match.winner
                result = "draw" if winner is None else "win" if winner == side else "loss"
                turns = [turn for turn in entry.match.turns if turn.side == side]
            games.append(
                GameScore(
                    pair_id=entry.opening_id,
                    a_side=entry.a_side,
                    status=entry.status,
                    result=result,
                    decisions=len(turns),
                    elapsed_ms=sum(turn.choice.elapsed_ms for turn in turns),
                )
            )
        players[player] = score_pairs(games)
    status = (
        "failed"
        if players["a"].failed_games
        else ("complete" if players["a"].completed_pairs == players["a"].planned_pairs else "incomplete")
    )
    return EvalSummary(spec_sha256=run.spec_sha256, status=status, players=players)


def evaluate_batch(corpus: Corpus, a: PlayerConfig, b: PlayerConfig) -> EvaluationRecord:
    # COMPAT: Keep the original successful batch shape and fail-fast CLI behavior.
    run = run_evaluation(EvalSpec(corpus=corpus, player_a=a, player_b=b))
    summary = summarize_evaluation(run)
    if summary.status != "complete":
        raise GameError("evaluation_failed", next(entry.error for entry in run.games if entry.error))
    games = [EvaluationGame(opening_id=entry.opening_id, a_side=entry.a_side, match=entry.match) for entry in run.games]
    return EvaluationRecord(
        corpus=run.spec.corpus,
        corpus_sha256=run.spec.corpus.digest,
        player_a=run.spec.player_a,
        player_b=run.spec.player_b,
        games=games,
        summary={player: summarize(games, player) for player in ("a", "b")},
        termination_reasons=dict(Counter(entry.match.reason for entry in games)),
        evaluation=summary,
    )
