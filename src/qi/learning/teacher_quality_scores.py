"""Read common-depth all-move reference estimates; missing evidence stays unknown."""

from qi.game import legal_moves
from qi.teacher import TeacherAnalysis, TeacherScore


def candidates(analysis: TeacherAnalysis) -> dict:
    legal = set(legal_moves(analysis.snapshot.game().board, analysis.snapshot.game().turn))
    if analysis.settings.get("MultiPV") != str(len(legal)) or analysis.settings.get("UCI_ShowWDL") != "true":
        raise ValueError("Candidate assessment requires all legal moves and WDL output.")
    tables: dict[int, dict[int, dict]] = {}
    for line in analysis.search_info:
        tokens = line.split()
        if not tokens or tokens[0] != "info" or "string" in tokens[:2] or "pv" not in tokens:
            continue
        if not all(key in tokens for key in ("depth", "multipv", "score", "wdl")):
            continue
        try:
            depth = int(tokens[tokens.index("depth") + 1])
            rank = int(tokens[tokens.index("multipv") + 1])
            move = tokens[tokens.index("pv") + 1]
            start = tokens.index("score")
            score = TeacherScore(
                kind=tokens[start + 1],
                value=int(tokens[start + 2]),
                bound=next((b for b in ("lowerbound", "upperbound") if b in tokens), "exact"),
            )
            start = tokens.index("wdl")
            wdl = list(map(int, tokens[start + 1 : start + 4]))
            if depth < 0 or rank < 1 or len(wdl) != 3 or min(wdl) < 0 or sum(wdl) != 1000:
                raise ValueError("Invalid candidate counters or WDL distribution.")
        except (ValueError, IndexError) as exc:
            raise ValueError("Malformed candidate reference information.") from exc
        tables.setdefault(depth, {})[rank] = {"move": move, "score": score.model_dump(), "wdl": wdl}
    complete = [
        depth
        for depth, rows in tables.items()
        if set(rows) == set(range(1, len(legal) + 1))
        and {row["move"] for row in rows.values()} == legal
        and all(row["score"]["bound"] == "exact" for row in rows.values())
    ]
    if not complete:
        return {"status": "unknown", "reason": "No complete common-depth exact candidate set.", "moves": {}}
    depth = max(complete)
    return {"status": "complete", "depth": depth, "moves": {row["move"]: row for row in tables[depth].values()}}


def disadvantage(reference: dict, move: str) -> dict:
    if reference["status"] != "complete":
        return {"status": "unknown", "expected_score_loss": None, "cp_gap": None, "mate": None}
    rows = reference["moves"]
    if move not in rows:
        raise ValueError("Student prediction is outside the reference legal support.")

    def expected(row):
        win, draw, _ = row["wdl"]
        return (win + 0.5 * draw) / 1000

    chosen = rows[move]
    scores = [row["score"] for row in rows.values()]
    cp_only = all(score["kind"] == "cp" for score in scores)
    return {
        "status": "complete",
        "expected_score_loss": max(map(expected, rows.values())) - expected(chosen),
        "cp_gap": max(score["value"] for score in scores) - chosen["score"]["value"] if cp_only else None,
        "mate": chosen["score"]["value"] if chosen["score"]["kind"] == "mate" else None,
        "reference_contains_mate": not cp_only,
    }
