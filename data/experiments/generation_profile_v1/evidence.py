"""Fixed fixture and independent semantic checks for this experiment."""

import json
import re
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from qi_game.contracts import Snapshot
from qi_game.reference import legal_moves, restore

from qi.evaluation import Corpus, Opening
from qi.players.policy.encoding import input_key
from qi.teacher import TeacherAnalysis, TeacherIdentity
from qi.training_data.contracts import Example, classify_phase, state_fingerprint
from qi.training_data.generation_io import analysis_spec
from qi.training_data.generation_policies import ActorPolicy, SamplingPolicy
from qi.training_data.generation_runner import GenerationSource, GenerationTeacher, PolicyGenerationConfig


def write_new(path, value):
    content = json.dumps(value, indent=2, allow_nan=False) + "\n"
    with path.open("x") as stream:
        stream.write(content)


def fixture_provider(game, settings):
    identity = TeacherIdentity.read(settings)
    spec = analysis_spec(settings, identity).supervision
    return TeacherAnalysis(
        schema_version=int(spec["adapter"][-1]),
        adapter_version=spec["adapter"],
        snapshot=Snapshot(moves=list(game.moves)),
        state_hash=game.state_hash,
        move=sorted(game.legal_moves if hasattr(game, "legal_moves") else legal_moves(game.board, game.turn))[0],
        engine_name="deterministic-legal-fixture",
        engine_sha256=identity.engine_sha256,
        network_sha256=identity.network_sha256,
        settings=spec["settings"],
        requested_nodes=settings.nodes,
        requested_depth=settings.depth,
        timeout_seconds=settings.timeout_seconds,
        reported_nodes=settings.nodes,
        reported_depth=1,
        elapsed_ms=0.0,
        score=None,
        search_info=[],
    )


def semantic_records(store):
    games = []
    for row in store.db.execute("SELECT id,status,stop_reason,outcome FROM games ORDER BY id"):
        game = store.game(row[0])
        reference = restore(game.snapshot)
        expected_outcome = asdict(reference.outcome) if reference.outcome else None
        if (json.loads(row[3]) if row[3] else None) != expected_outcome:
            raise ValueError("Stored outcome differs from independent replay.")
        for decision in game.actor["generation_result"]["decisions"]:
            if decision["move"] != game.snapshot.moves[decision["ply"]]:
                raise ValueError("Actor decision differs from replay history.")
        games.append(
            {
                "game": game.model_dump(exclude={"actor_ms"}),
                "status": row[1],
                "stop_reason": row[2],
                "outcome": json.loads(row[3]) if row[3] else None,
                "state_hash": reference.state_hash,
            }
        )
    occurrences = [
        list(row)
        for row in store.db.execute(
            "SELECT game_id,ply_count,board,turn,state_hash,input_hash,phase,json(payload) "
            "FROM position_occurrences ORDER BY id"
        )
    ]
    for game_id, ply, board, turn, state_hash, input_hash, phase, _ in occurrences:
        snapshot = store.game(game_id).snapshot
        checked_snapshot = Snapshot(moves=snapshot.moves[:ply])
        checked = restore(checked_snapshot)
        if (board, turn, state_hash, input_hash, phase) != (
            checked.board,
            checked.turn,
            state_fingerprint(checked_snapshot),
            input_key(checked),
            classify_phase(checked),
        ):
            raise ValueError("Occurrence differs from independent replay.")
    analyses = []
    for row in store.db.execute("SELECT occurrence_id,status,json(payload) FROM analyses ORDER BY id"):
        payload = json.loads(row[2])
        answer = payload.get("answer")
        if answer:
            Example.model_validate({"analysis": answer, "source_ids": ["independent-verification"]})
            answer.pop("elapsed_ms", None)
            answer["settings"].pop("EvalFile", None)
            answer["search_info"] = [re.sub(r"\b(?:time|nps) \d+\s*", "", line) for line in answer["search_info"]]
            payload["raw"] = [re.sub(r"\b(?:time|nps) \d+\s*", "", line) for line in payload["raw"]]
        analyses.append([row[0], row[1], payload])
    if store.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("SQLite integrity check failed.")
    if store.db.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("SQLite foreign key check failed.")
    return {"games": games, "occurrences": occurrences, "analyses": analyses}


def prepare_controlled(output: Path):
    output.mkdir(parents=True, exist_ok=False)
    engine = output / "fixture-engine"
    network = output / "fixture-network"
    engine.write_text("controlled fixture, no executable teacher\n")
    network.write_text("controlled fixture, no learned network\n")
    teacher = GenerationTeacher(
        engine=str(engine.resolve()),
        network=str(network.resolve()),
        engine_sha256=sha256(engine.read_bytes()).hexdigest(),
        network_sha256=sha256(network.read_bytes()).hexdigest(),
        nodes=1000,
        timeout_seconds=5.0,
    )
    config = PolicyGenerationConfig(
        name="native-integration",
        seed=29,
        seconds=180.0,
        corpus=Corpus(
            id="initial-control",
            provenance="Standard initial position excluded from selections.",
            openings=[Opening(id="initial", description="Initial board", snapshot=Snapshot())],
        ),
        teachers={"teacher": teacher},
        actor_teacher="teacher",
        supervision=["teacher"],
        sources=[
            GenerationSource(
                id="controlled",
                games=64,
                split="train",
                additional_plies=300,
                actor=ActorPolicy(mode="random"),
                sampling=SamplingPolicy(),
            )
        ],
    )
    write_new(output / "controlled.json", config.model_dump())
