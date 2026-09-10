"""Regenerate the synthetic reference dataset; no teacher, torch or network needed."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from qi.evaluation import Corpus, Opening
from qi.game import legal_moves
from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis, TeacherConfig
from qi.training_data.assembly import Bucket, MixtureRecipe, assemble
from qi.training_data.contracts import GenerationRecipe, SourcePlan, StartingPosition
from qi.training_data.generation import generate_library, teacher_spec


def build_fixture():
    # These text markers satisfy the existing teacher-shaped fixture contract.
    # Their hashes identify synthetic markers, never an engine or neural network.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        engine, network = root / "synthetic-labeler", root / "no-network"
        engine.write_text("synthetic-sorted-first-legal-v1\n")
        network.write_text("synthetic-fixture-no-network-v1\n")
        teacher = TeacherConfig(engine, network, nodes=1, depth=1)
        spec = teacher_spec(teacher)

        def labeler(game, config):
            return TeacherAnalysis(
                snapshot=Snapshot(moves=list(game.moves)),
                state_hash=game.state_hash,
                move=sorted(legal_moves(game.board, game.turn))[0],
                engine_name="synthetic-sorted-first-legal-v1 (not an engine)",
                engine_sha256=spec["engine_sha256"],
                network_sha256=spec["network_sha256"],
                settings=spec["settings"],
                requested_nodes=1,
                requested_depth=1,
                timeout_seconds=10.0,
                reported_nodes=None,
                reported_depth=None,
                score=None,
                elapsed_ms=0.0,
                search_info=[],
            )

        library = generate_library(
            GenerationRecipe(
                id="reference-synthetic-v1",
                sources=[
                    SourcePlan(
                        id=split,
                        mode="random",
                        split=split,
                        start=StartingPosition(id="initial", version="1"),
                        games=2,
                        additional_plies=8,
                        samples=4,
                    )
                    for split in ("train", "validation")
                ],
            ),
            Corpus(
                id="reference-reserved-v1",
                provenance="Synthetic workflow fixture; sorted-first legal labels, no teacher or strength claim.",
                openings=[Opening(id="initial", description="Reserved initial board", snapshot=Snapshot())],
            ),
            teacher,
            labeler=labeler,
        )
    dataset = assemble(
        library,
        MixtureRecipe(
            id="reference-synthetic-v1",
            supervision_fingerprint=library.examples[0].supervision_fingerprint,
            buckets=[Bucket(id="train", split="train", count=8), Bucket(id="validation", split="validation", count=4)],
        ),
    )
    dataset.require_complete()
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    dataset = build_fixture()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(dataset.model_dump_json(indent=2) + "\n")
    print(dataset.digest)
