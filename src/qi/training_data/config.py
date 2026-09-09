"""Complete file-based preparation recipes; training consumes their frozen output."""

import json
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from typing import Literal

from pydantic import Field

from qi.evaluation import Corpus
from qi.game import Game, GameError
from qi.teacher import TeacherAnalysis, TeacherConfig, TeacherIdentity, TeacherSession, analyze
from qi.training_data.assembly import MixtureRecipe, assemble
from qi.training_data.contracts import Contract, GenerationRecipe, Library, fingerprint
from qi.training_data.generation import generate_library, teacher_spec


class SupervisionSettings(Contract):
    target: Literal["legal-teacher-move-v1"] = "legal-teacher-move-v1"
    authority: Literal["teacher-preference"] = "teacher-preference"
    engine: str = Field(min_length=1)
    network: str = Field(min_length=1)
    engine_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    network_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    nodes: int = Field(default=1000, ge=1)
    depth: int = Field(default=3, ge=1, le=64)
    timeout_seconds: float = Field(default=10.0, gt=0, le=120)

    def teacher(self, identity: TeacherIdentity | None = None) -> TeacherConfig:
        config = TeacherConfig(Path(self.engine), Path(self.network), self.nodes, self.depth, self.timeout_seconds)
        identity = identity or TeacherIdentity.read(config)
        identity.require(config)
        if identity.engine_sha256 != self.engine_sha256 or identity.network_sha256 != self.network_sha256:
            raise GameError("teacher_mismatch", "Engine or network bytes differ from the preparation config.")
        return config


class PreparationConfig(Contract):
    schema_version: Literal["dataset-preparation-v1"] = "dataset-preparation-v1"
    corpus: str = Field(min_length=1)
    corpus_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation: GenerationRecipe
    supervision: SupervisionSettings
    actor_teacher: SupervisionSettings | None = None
    teacher_process: Literal["fresh", "persistent"] = "fresh"
    assembly: MixtureRecipe

    def resolve(self, base: Path) -> "PreparationConfig":
        config = self.model_copy(deep=True)
        config.corpus = str((base / config.corpus).resolve())
        for settings in (config.supervision, config.actor_teacher):
            if settings is not None:
                settings.engine = str((base / settings.engine).resolve())
                settings.network = str((base / settings.network).resolve())
        return config


def load_preparation(path: Path) -> PreparationConfig:
    return PreparationConfig.model_validate_json(path.read_text()).resolve(path.parent)


def prepare_dataset(
    config: PreparationConfig,
    output: Path,
    *,
    labeler: Callable[[Game, TeacherConfig], TeacherAnalysis] = analyze,
) -> dict:
    """Pin inputs before execution and retain incomplete generation/assembly evidence."""
    config = PreparationConfig.model_validate(config.model_dump())
    config.generation.require_current()
    if output.exists():
        raise GameError("output_exists", "Choose a fresh preparation directory.")
    corpus = Corpus.model_validate_json(Path(config.corpus).read_text())
    if corpus.digest != config.corpus_sha256:
        raise GameError("corpus_mismatch", "Reserved corpus differs from the preparation config.")
    persistent = config.teacher_process == "persistent"
    if persistent and labeler is not analyze:
        raise GameError("invalid_teacher", "Persistent preparation cannot override the session labeler.")
    if (
        persistent
        and config.actor_teacher
        and (Path(config.actor_teacher.engine).resolve(), Path(config.actor_teacher.network).resolve())
        != (Path(config.supervision.engine).resolve(), Path(config.supervision.network).resolve())
    ):
        raise GameError("teacher_mismatch", "Persistent preparation requires the same actor and supervisor files.")
    teacher = config.supervision.teacher()
    identity = TeacherIdentity(
        teacher.engine.resolve(),
        teacher.network.resolve(),
        config.supervision.engine_sha256,
        config.supervision.network_sha256,
    )
    actor = config.actor_teacher.teacher(identity if persistent else None) if config.actor_teacher else None
    if config.assembly.supervision_fingerprint != fingerprint("supervision-v1", teacher_spec(teacher, identity)):
        raise GameError("supervision_mismatch", "Assembly must select the configured supervision specification.")
    output.mkdir(parents=True, exist_ok=False)
    (output / "config.json").write_text(config.model_dump_json(indent=2) + "\n")

    def save(library: Library) -> None:
        pending = output / "library.pending.json"
        with pending.open("x") as stream:
            stream.write(library.model_dump_json() + "\n")
        pending.replace(output / "library.json")

    save(Library(recipe=config.generation, reserved_corpus=corpus))
    with TeacherSession(teacher, identity=identity) if persistent else nullcontext() as session:
        library = generate_library(
            config.generation,
            corpus,
            teacher,
            actor_teacher=actor,
            labeler=session.analyze if session else labeler,
            checkpoint=save,
            teacher_identity=identity if persistent else None,
        )
    save(library)
    result = {
        "status": "incomplete",
        "generation_status": library.status,
        "examples": len(library.examples),
        "failure": library.failure,
    }
    if library.status == "complete":
        try:
            dataset = assemble(library, config.assembly)
        except ValueError as exc:
            result["failure"] = str(exc)
        else:
            (output / "dataset.json").write_text(dataset.model_dump_json() + "\n")
            result.update(
                status=dataset.manifest.status,
                actual=dataset.manifest.actual,
                dataset_sha256=dataset.digest,
                dataset_manifest_fingerprint=dataset.manifest.fingerprint,
            )

    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
