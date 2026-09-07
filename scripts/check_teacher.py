"""Explicit real-engine smoke: pinned identity, both turns, history, and legal proposals."""

import argparse
import json
from pathlib import Path

from qi.evaluation import Corpus
from qi.game import replay
from qi.teacher import TeacherConfig, analyze

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--network", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads((ROOT / "data/teachers/pikafish-2026-01-02.json").read_text())
    config = TeacherConfig(args.engine, args.network, nodes=1000, depth=3)
    corpus = Corpus.model_validate_json((ROOT / "data/evaluation/openings-v1.json").read_text())
    games = [opening.snapshot.game() for opening in corpus.openings]
    games += [replay(("b2e2",)), replay(("b0c2", "b9c7", "c2b0", "c7b9"))]
    records = []
    for game in games:
        first, second = analyze(game, config), analyze(game, config)
        if first.engine_sha256 != lock["engine_sha256"] or first.network_sha256 != lock["network_sha256"]:
            raise SystemExit("Smoke target differs from the pinned binary/network.")
        if first.move != second.move:
            raise SystemExit("Repeated fresh-process analysis selected different moves.")
        game.apply(first.move, first.state_hash)
        records.append(first.model_dump())
    print(json.dumps({"positions": len(games), "queries": len(games) * 2, "analyses": records}))


if __name__ == "__main__":
    main()
