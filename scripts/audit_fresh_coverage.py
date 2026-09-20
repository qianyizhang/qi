"""Data-only execution of the existing sampler; placeholder targets are never saved or trained."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from random import Random

from investigate_source_coverage import match_plies, ply
from qi_game.contracts import Snapshot
from qi_game.reference import legal_moves

from qi.evaluation import Corpus
from qi.teacher import TeacherAnalysis, TeacherConfig
from qi.training_data.v1 import generate


def placeholder(game, config):
    return TeacherAnalysis(
        snapshot=Snapshot(moves=list(game.moves)),
        state_hash=game.state_hash,
        move=sorted(legal_moves(game.board, game.turn))[0],
        engine_name="NO TEACHER QUERY - FEASIBILITY ONLY",
        engine_sha256="0" * 64,
        network_sha256="0" * 64,
        settings={},
        requested_nodes=config.nodes,
        requested_depth=config.depth,
        timeout_seconds=config.timeout_seconds,
        reported_nodes=None,
        reported_depth=None,
        score=None,
        elapsed_ms=0,
        search_info=[],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--games", type=int, default=512)
    args = parser.parse_args()
    p = args.output
    p.mkdir(parents=True, exist_ok=False)
    c = json.loads(args.config.read_text())
    c["generation"]["games"] = args.games
    teacher = TeacherConfig(
        Path(c["teacher"]["engine"]),
        Path(c["teacher"]["network"]),
        nodes=c["teacher"]["nodes"],
        depth=c["teacher"]["depth"],
    )
    corpus = Corpus.model_validate_json(Path(c["corpus"]).read_text())
    raw = [
        generate(corpus, teacher, seed=seed, **c["generation"], labeler=placeholder) for seed in c["generation_seeds"]
    ]
    old = set()
    for name in c["exclude_datasets"]:
        old.update(x["input_sha256"] for x in json.loads(Path(name).read_text())["labels"])
    counts = Counter(label.input_sha256 for d in raw for label in d.labels)
    old.update(k for k, v in counts.items() if v > 1)
    rows = []
    for block, d in enumerate(raw):
        groups = defaultdict(list)
        for label in d.split_labels("train"):
            if label.input_sha256 not in old:
                groups[label.source_id].append(label)
        full = {k: v for k, v in groups.items() if len(v) == 16}
        ids = sorted(full)
        Random(c["selection_seed"] + block).shuffle(ids)
        ids = ids[:192]
        if len(ids) != 192:
            raise ValueError(f"Block {block} has only {len(ids)} eligible sources; do not relax the quota.")
        concentrated = [label for sid in ids[:48] for label in full[sid]]
        broader = match_plies(full, ids, Counter(map(ply, concentrated)), c["matching_seed"] + block)
        rows.append(
            dict(
                block=block,
                eligible_sources=len(full),
                holdout_positions=sum(label.input_sha256 not in old for label in d.split_labels("validation")),
                generated_input_ids=sorted(label.input_sha256 for label in d.labels),
                concentrated=sorted(label.input_sha256 for label in concentrated),
                broader=sorted(label.input_sha256 for label in broader),
            )
        )
    result = dict(
        purpose=(
            "Data-only sampler feasibility; zero teacher queries or model predictions; placeholder targets discarded"
        ),
        games_per_block=args.games,
        blocks=rows,
    )
    with (p / "audit.json").open("x") as f:
        json.dump(result, f, indent=2)
    print(
        json.dumps(
            [{k: v for k, v in r.items() if k in ("block", "eligible_sources", "holdout_positions")} for r in rows]
        )
    )


if __name__ == "__main__":
    main()
