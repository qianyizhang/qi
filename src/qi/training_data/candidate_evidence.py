"""Typed, partial UCI candidate observations; absent coverage is never a zero target."""

from pydantic import Field
from qi_game.execution import ReplaySession
from qi_game.reference import legal_moves, restore

from qi.teacher import TeacherAnalysis, TeacherScore
from qi.training_data.contracts import Contract


class CandidateEvidence(Contract):
    move: str
    depth: int | None = Field(default=None, ge=0)
    rank: int = Field(default=1, ge=1)
    score: TeacherScore | None = None
    wdl: list[int] | None = None
    pv: list[str]


def parse_candidates(answer: TeacherAnalysis, *, execution: ReplaySession | None = None) -> list[CandidateEvidence]:
    if execution is None:
        game = restore(answer.snapshot)
        legal = set(legal_moves(game.board, game.turn))
    else:
        legal = set(execution.inspect(answer.snapshot).legal_moves)
    result = []
    for line in answer.search_info:
        tokens = line.split()
        if tokens[:1] != ["info"] or tokens[1:2] == ["string"] or "pv" not in tokens:
            continue
        try:
            pv = tokens[tokens.index("pv") + 1 :]
            if not pv or pv[0] not in legal:
                raise ValueError("Illegal root candidate.")
            score = None
            if "score" in tokens:
                i = tokens.index("score")
                score = TeacherScore(
                    kind=tokens[i + 1],
                    value=int(tokens[i + 2]),
                    bound=next((b for b in ("lowerbound", "upperbound") if b in tokens), "exact"),
                )
            wdl = None
            if "wdl" in tokens:
                i = tokens.index("wdl")
                wdl = [int(v) for v in tokens[i + 1 : i + 4]]
                if len(wdl) != 3 or min(wdl) < 0 or sum(wdl) != 1000:
                    raise ValueError("Invalid WDL evidence.")
            result.append(
                CandidateEvidence(
                    move=pv[0],
                    pv=pv,
                    score=score,
                    wdl=wdl,
                    depth=int(tokens[tokens.index("depth") + 1]) if "depth" in tokens else None,
                    rank=int(tokens[tokens.index("multipv") + 1]) if "multipv" in tokens else 1,
                )
            )
        except (IndexError, ValueError) as exc:
            raise ValueError("Malformed candidate evidence; raw response must be retained as a failure.") from exc
    return result
