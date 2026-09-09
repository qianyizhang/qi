"""Small hermetic fixtures shared by data-contract and optional learning tests."""

import pytest

from qi.evaluation import Corpus, Opening
from qi.game import legal_moves
from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis, TeacherConfig
from qi.training_data.contracts import GenerationRecipe, SourcePlan, StartingPosition
from qi.training_data.generation import generate_library, teacher_spec
from qi.training_data.v1 import generate


@pytest.fixture
def tiny_dataset(tmp_path):
    engine = tmp_path / "fake-engine"
    network = tmp_path / "fake-network"
    engine.touch()
    network.touch()
    corpus = Corpus(
        id="test-reserved",
        provenance="Hermetic test fixture",
        openings=[
            Opening(id="initial", description="Reserved initial board", snapshot=Snapshot()),
        ],
    )

    def labeler(game, config):
        return TeacherAnalysis(
            snapshot=Snapshot(moves=list(game.moves)),
            state_hash=game.state_hash,
            move=sorted(legal_moves(game.board, game.turn))[0],
            engine_name="test-teacher",
            engine_sha256="a" * 64,
            network_sha256="b" * 64,
            settings={"Threads": "1"},
            requested_nodes=config.nodes,
            requested_depth=config.depth,
            timeout_seconds=config.timeout_seconds,
            reported_nodes=1,
            reported_depth=1,
            score=None,
            elapsed_ms=0,
            search_info=[],
        )

    return generate(corpus, TeacherConfig(engine, network), games=4, plies=8, samples=3, labeler=labeler)


@pytest.fixture
def data_setup(tiny_dataset, tmp_path):
    teacher = TeacherConfig(tmp_path / "fake-engine", tmp_path / "fake-network", nodes=100, depth=2)
    calls = []

    def labeler(game, config):
        calls.append((game.state_hash, config.nodes))
        spec = teacher_spec(config)
        return tiny_dataset.labels[0].analysis.model_copy(
            update={
                "snapshot": Snapshot(moves=list(game.moves)),
                "state_hash": game.state_hash,
                "move": sorted(legal_moves(game.board, game.turn))[0],
                "engine_sha256": spec["engine_sha256"],
                "network_sha256": spec["network_sha256"],
                "settings": spec["settings"],
                "requested_nodes": config.nodes,
                "requested_depth": config.depth,
            }
        )

    plans = []
    for mode in ("random", "teacher-guided"):
        for split, move in (("train", "b0c2"), ("validation", "h0g2")):
            start = (
                StartingPosition(id="initial", version="1")
                if mode == "random"
                else StartingPosition(
                    id=f"teacher-{split}",
                    version="1",
                    family_id=f"family-{split}",
                    snapshot=Snapshot(moves=[move]),
                    themes=["development"],
                )
            )
            plans.append(
                SourcePlan(id=f"{mode}-{split}", mode=mode, split=split, start=start, additional_plies=8, samples=3)
            )
    recipe = GenerationRecipe(id="fixture", sources=plans)
    return recipe, tiny_dataset.reserved_corpus, teacher, labeler, calls


@pytest.fixture
def library(data_setup):
    recipe, corpus, teacher, labeler, _ = data_setup
    result = generate_library(recipe, corpus, teacher, labeler=labeler)
    assert result.status == "complete", result.failure
    return result
