"""Bounded real-teacher Training Data pilot; artifacts stay local and explicit."""

import argparse
import json
from pathlib import Path
from random import Random
from time import perf_counter

from qi.evaluation import Corpus
from qi.game import Game, legal_moves
from qi.learning.train import train
from qi.protocol import Snapshot
from qi.teacher import TeacherConfig
from qi.training_data.assembly import Bucket, MixtureRecipe, assemble
from qi.training_data.contracts import (
    GenerationRecipe,
    SamplingWindow,
    SourcePlan,
    StartingPosition,
    classify_phase,
    fingerprint,
)
from qi.training_data.generation import generate_library, teacher_spec


def starting_position(phase: str, seed: int) -> Snapshot:
    for attempt in range(100):
        rng, game = Random(seed + attempt), Game()
        for _ in range(299):
            if game.outcome:
                break
            if len(game.moves) >= 2 and classify_phase(game) == phase:
                return Snapshot(moves=list(game.moves))
            game = game.apply(rng.choice(sorted(legal_moves(game.board, game.turn))))
    raise ValueError(f"No reachable {phase} start found.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "mps"], default="cpu")
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--network", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    def write(name, value):
        (args.output / name).write_text(json.dumps(value, indent=2) + "\n")

    teacher = TeacherConfig(args.engine, args.network, nodes=1000, depth=3)
    corpus = Corpus.model_validate_json(Path("data/evaluation/search-positions-v1.json").read_text())
    plans = []
    buckets = []
    for phase_index, phase in enumerate(("opening", "middlegame", "endgame")):
        for split_index, split in enumerate(("train", "validation")):
            for mode_index, mode in enumerate(("random", "teacher-guided")):
                snapshot = starting_position(phase, 901 + phase_index * 100 + split_index * 20 + mode_index * 11)
                name = f"{phase}-{mode}-{split}"
                start = StartingPosition(
                    id=f"pilot-{name}",
                    version="1",
                    snapshot=snapshot,
                    family_id=f"pilot-family-{name}",
                    themes=[f"from-{phase}"],
                )
                plans.append(
                    SourcePlan(
                        id=name,
                        split=split,
                        mode=mode,
                        start=start,
                        additional_plies=16,
                        samples=8,
                        window=SamplingWindow(phases=[phase]),
                    )
                )
                buckets.append(
                    Bucket(id=name, split=split, count=1 if phase == "opening" else 3, modes=[mode], phases=[phase])
                )
    recipe = GenerationRecipe(id="training-data-pilot-v2", seed=901, seconds=240, sources=plans)
    mixture = MixtureRecipe(
        id="training-data-pilot-mixture-v2",
        seed=7,
        supervision_fingerprint=fingerprint("supervision-v1", teacher_spec(teacher)),
        buckets=buckets,
    )
    write("generation.json", recipe.model_dump())
    write("mixture.json", mixture.model_dump())
    started = perf_counter()
    library = generate_library(
        recipe, corpus, teacher, checkpoint=lambda value: write("library.json", value.model_dump())
    )
    write("library.json", library.model_dump())
    generation_seconds = perf_counter() - started
    dataset = assemble(library, mixture)
    write("dataset.json", dataset.model_dump())
    write("identities.json", library.identities())
    write("coverage.json", {name: len(keys) for name, keys in dataset.slice_inputs().items()})
    dataset.require_complete()
    result = train(dataset, args.output / "policy.pt", steps=30, seconds=30, device=args.device)
    result["generation_seconds"] = generation_seconds
    result["library_examples"] = len(library.examples)
    result["manifest"] = dataset.manifest.model_dump()
    write("report.json", result)
    print(
        json.dumps(
            {
                "generation_seconds": generation_seconds,
                "library_examples": len(library.examples),
                "manifest_status": dataset.manifest.status,
                "train": result["train"],
                "validation": result["validation"],
                "reload_equal": result["reload_predictions_equal"],
            }
        )
    )


if __name__ == "__main__":
    main()
