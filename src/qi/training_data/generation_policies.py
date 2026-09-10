"""Pure, seeded actor and per-trajectory selection policies for bounded generation."""

from random import Random
from typing import Literal, Self

from pydantic import Field, model_validator

from qi.game import Game, GameError, legal_moves
from qi.players.policy.encoding import input_key
from qi.teacher import TeacherAnalysis
from qi.training_data.candidate_evidence import parse_candidates
from qi.training_data.contracts import Contract, Phase, classify_phase


class ActorPolicy(Contract):
    mode: Literal["random", "plausible", "intervention"] = "plausible"
    candidate_count: int = Field(default=3, ge=1, le=256)
    max_cp_gap: int = Field(default=50, ge=0, le=100_000)
    intervention_min_ply: int = Field(default=8, ge=0, le=299)
    intervention_max_ply: int = Field(default=80, ge=0, le=299)
    probability_rule: Literal["uniform-eligible-v1"] = "uniform-eligible-v1"

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.intervention_min_ply > self.intervention_max_ply:
            raise ValueError("Intervention window must be nonempty.")
        return self


class SamplingPolicy(Contract):
    phase_counts: dict[Phase, int] = Field(default_factory=lambda: {"opening": 2, "middlegame": 4, "endgame": 2})
    min_spacing: int = Field(default=4, ge=1, le=300)
    min_ply: int = Field(default=1, ge=0, le=299)
    max_ply: int = Field(default=299, ge=0, le=299)
    algorithm: Literal["seeded-greedy-phase-v1"] = "seeded-greedy-phase-v1"

    @model_validator(mode="after")
    def validate_sampling(self) -> Self:
        if self.min_ply > self.max_ply:
            raise ValueError("Sampling window must be nonempty.")
        if any(count < 0 for count in self.phase_counts.values()) or not 1 <= sum(self.phase_counts.values()) <= 256:
            raise ValueError("Phase counts must be nonnegative with a total from 1 to 256.")
        return self


class ActorDecision(Contract):
    move: str
    reason: str
    eligible_moves: list[str]
    depth: int | None = Field(default=None, ge=0)
    intervention: bool = False


class SamplingResult(Contract):
    selected: list[int]
    requested: dict[Phase, int]
    actual: dict[Phase, int]
    available: dict[Phase, int]
    shortfall: dict[Phase, int]
    excluded: int = Field(default=0, ge=0)
    duplicates: int = Field(default=0, ge=0)


def choose_plausible(game: Game, answer: TeacherAnalysis, policy: ActorPolicy, rng: Random) -> ActorDecision:
    """Uniformly sample compatible candidates, or explicitly use a legal teacher fallback.

    All evidence is parsed before fallbacks, so malformed or illegal observations
    never become an apparently successful teacher-best decision. An older complete
    depth can be used only while later rank-one observations still support its best
    move and later candidate evidence has not introduced mate scores.
    """
    legal = set(legal_moves(game.board, game.turn))
    if (
        game.outcome
        or answer.move not in legal
        or answer.state_hash != game.state_hash
        or tuple(answer.snapshot.moves) != game.moves
    ):
        raise GameError("invalid_supervision", "Actor answer must match the exact nonterminal state and a legal move.")
    try:
        candidates = parse_candidates(answer)
    except ValueError as exc:
        raise GameError("invalid_supervision", str(exc)) from exc

    def fallback(reason: str) -> ActorDecision:
        return ActorDecision(move=answer.move, reason=reason, eligible_moves=[answer.move])

    if answer.score is not None and answer.score.kind == "mate":
        return fallback("mate-score")
    if not candidates:
        return fallback("missing-candidates")
    rank_one = [candidate for candidate in candidates if candidate.rank == 1]
    if not rank_one or rank_one[-1].move != answer.move:
        return fallback("latest-best-mismatch")
    needed = min(policy.candidate_count, len(legal))
    depths = sorted({c.depth for c in candidates if c.depth is not None}, reverse=True)
    for depth in depths:
        rows = [c for c in candidates if c.depth == depth and c.rank <= needed]
        if len(rows) != needed or {c.rank for c in rows} != set(range(1, needed + 1)):
            continue
        rows.sort(key=lambda c: c.rank)
        if len({c.move for c in rows}) != needed:
            return fallback("duplicate-candidate-roots")
        if rows[0].move != answer.move:
            return fallback("complete-best-mismatch")
        later = [c for c in candidates if c.depth is not None and c.depth >= depth]
        if any(c.score is not None and c.score.kind == "mate" for c in later):
            return fallback("mate-score")
        if any(c.rank == 1 and c.move != answer.move and c.depth > depth for c in candidates if c.depth is not None):
            return fallback("later-best-changed")
        if any(c.score is None or c.score.kind != "cp" or c.score.bound != "exact" for c in rows):
            return fallback("incompatible-scores")
        if len({(c.score.perspective, c.score.semantics) for c in rows}) != 1:
            return fallback("incompatible-perspective")
        if rows[0].score.value != max(c.score.value for c in rows):
            return fallback("inconsistent-ranks")
        best = rows[0].score.value
        eligible = sorted(c.move for c in rows if best - c.score.value <= policy.max_cp_gap)
        return ActorDecision(move=rng.choice(eligible), reason="uniform-eligible", eligible_moves=eligible, depth=depth)
    return fallback("incomplete-common-depth")


def sample_positions(
    games: list[Game], policy: SamplingPolicy, rng: Random, excluded_inputs: set[str] | None = None
) -> SamplingResult:
    """Select candidate states from ONE trajectory; return exact absolute plies.

    Quotas are per trajectory. Spacing is enforced across all selected phases.
    Candidates are ordered canonically before shuffling, independent of caller
    iteration order. Greedy underfill is reported, not claimed infeasible. Repeated
    observations and exclusions count before spacing/quota selection. The caller
    retains the full trajectory and occurrence provenance, including duplicates.
    """
    requested = dict(sorted(policy.phase_counts.items()))
    actual = dict.fromkeys(requested, 0)
    available = dict.fromkeys(requested, 0)
    selected: list[int] = []
    seen: set[str] = set()
    excluded = duplicates = 0
    candidates: list[tuple[int, Phase]] = []
    excluded_inputs = excluded_inputs or set()
    if games:
        trajectory = max(games, key=lambda g: len(g.moves)).moves
        if any(game.moves != trajectory[: len(game.moves)] for game in games):
            raise ValueError("Sampling candidates must belong to one replay trajectory.")
    for game in sorted(games, key=lambda g: len(g.moves)):
        ply = len(game.moves)
        phase = classify_phase(game)
        if game.outcome or not policy.min_ply <= ply <= policy.max_ply or not requested.get(phase, 0):
            continue
        key = input_key(game)
        if key in excluded_inputs:
            excluded += 1
            continue
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        candidates.append((ply, phase))
        available[phase] += 1
    rng.shuffle(candidates)
    for ply, phase in candidates:
        if actual[phase] < requested[phase] and all(abs(ply - previous) >= policy.min_spacing for previous in selected):
            selected.append(ply)
            actual[phase] += 1
    return SamplingResult(
        selected=sorted(selected),
        requested=requested,
        actual=actual,
        available=available,
        shortfall={phase: requested[phase] - actual[phase] for phase in requested},
        excluded=excluded,
        duplicates=duplicates,
    )
