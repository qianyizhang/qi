"""Resource limits stop resumably and fail closed when requested counters are absent."""

import importlib.util
from pathlib import Path

import pytest
from qi_game.core import GameError

spec = importlib.util.spec_from_file_location(
    "generation_pilot_command", Path(__file__).parents[1] / "scripts/run_generation_pilot.py"
)
command = importlib.util.module_from_spec(spec)
spec.loader.exec_module(command)


def sample(*, written=100, available=True):
    return {"disk_write_bytes": written, "process": {"available": available}, "peak_sampled_combined_rss_bytes": 200}


@pytest.mark.parametrize(
    "limits,data,free,reason",
    [
        ({"max_write_bytes": 100}, sample(), 1000, "write allowance"),
        ({"max_write_bytes": 100}, sample(written=None, available=False), 1000, "unavailable"),
        ({"max_rss_bytes": 200}, sample(), 1000, "RSS allowance"),
        ({"max_rss_bytes": 200}, sample(available=False), 1000, "unavailable"),
        ({"min_free_bytes": 1000}, sample(), 999, "Free disk"),
    ],
)
def test_guard_thresholds_and_unknown_counters(limits, data, free, reason):
    with pytest.raises(GameError, match=reason) as failure:
        command.enforce_resources(data, limits, free)
    assert failure.value.code == "resource_limit"


def test_explicit_headroom_and_optional_guards():
    command.enforce_resources(sample(), {"max_write_bytes": 101, "max_rss_bytes": 201, "min_free_bytes": 1000}, 1000)
    command.enforce_resources(sample(written=None, available=False), {}, 1000)


def test_resource_stop_keeps_game_and_resume_skips_its_queries(tmp_path, data_setup):
    from qi.teacher import TeacherIdentity, digest
    from qi.training_data.generation_io import analysis_spec
    from qi.training_data.generation_policies import ActorPolicy, SamplingPolicy
    from qi.training_data.generation_runner import (
        GenerationSource,
        GenerationTeacher,
        PolicyGenerationConfig,
        generate_policies,
    )
    from qi.training_data.store import Collection

    _, corpus, teacher, labeler, _calls = data_setup
    settings = GenerationTeacher(
        engine=str(teacher.engine),
        network=str(teacher.network),
        engine_sha256=digest(teacher.engine),
        network_sha256=digest(teacher.network),
        nodes=100,
        depth=2,
    )
    config = PolicyGenerationConfig(
        name="resource-resume",
        seconds=120.0,
        corpus=corpus,
        teachers={"main": settings},
        actor_teacher="main",
        supervision=["main"],
        sources=[
            GenerationSource(
                id="source",
                games=2,
                split="train",
                additional_plies=8,
                actor=ActorPolicy(mode="random"),
                sampling=SamplingPolicy(phase_counts={"opening": 1, "middlegame": 1}, min_spacing=1),
            )
        ],
    )

    def provider(game, cfg):
        expected = analysis_spec(cfg, TeacherIdentity.read(cfg))
        return labeler(game, cfg).model_copy(
            update={"settings": expected.supervision["settings"], "timeout_seconds": float(cfg.timeout_seconds)}
        )

    def stop(event):
        if event["kind"] == "completed-game":
            command.enforce_resources(sample(), {"max_write_bytes": 100}, 1000)

    with Collection(tmp_path / "collection.sqlite") as store:
        with pytest.raises(GameError, match="write allowance"):
            generate_policies(store, config, provider=provider, event=stop)
        assert store.db.execute("SELECT count(*) FROM games WHERE status='complete'").fetchone()[0] == 1
        assert store.db.execute("SELECT status FROM generation_runs").fetchone()[0] == "failed"
        result = generate_policies(store, config, provider=provider)
        assert result["reused_games"] == 1 and result["games"] == 2
        assert store.counts()["games"] == 2
