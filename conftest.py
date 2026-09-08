"""Small hermetic fixtures shared by data-contract and optional learning tests."""

import pytest

from qi.evaluation import Corpus, Opening
from qi.game import legal_moves
from qi.learning.data import generate
from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis, TeacherConfig


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
