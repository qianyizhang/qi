"""Fixed-input, paired teacher-label study; saved results never select the next fit."""

import json
import shutil
from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from statistics import mean
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qi.artifacts import digest, write_json
from qi.game import legal_moves
from qi.learning.config import DataSettings, ExecutionSettings, Recipe, TrainingSettings
from qi.learning.experiment import source_identity
from qi.learning.teacher_quality_scores import candidates, disadvantage
from qi.teacher import TeacherConfig, TeacherIdentity, TeacherSession
from qi.training_data.loading import load_dataset
from qi.training_data.relabel import relabel, select_validation

ROOT = Path(__file__).resolve().parents[3]


class Study(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = "teacher-quality-v1"
    datasets: list[str] = Field(min_length=1)
    dataset_file_sha256: list[str] = Field(min_length=1)
    engine: str
    network: str
    engine_sha256: str
    network_sha256: str
    train_positions: int = Field(default=768, ge=1)
    train_games: int = Field(default=192, ge=1)
    validation_games: int = Field(default=128, ge=1)
    seeds: list[int] = Field(default_factory=lambda: [7, 17, 27], min_length=1)
    selection_seed: int = 910
    updates: int = Field(default=200, ge=1, le=2000)
    seconds: float = Field(default=7200, gt=0, le=7200)

    @model_validator(mode="after")
    def identities(self):
        if len(self.datasets) != len(self.dataset_file_sha256) or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Require one digest per dataset and distinct training seeds.")
        return self


def prepare_inputs(study: Study) -> tuple[list, dict]:
    """Data-only selection and exact isolation checks, before any engine/model work."""
    selected, blocks = [], []
    all_inputs, all_histories = set(), set()
    for block, (name, expected) in enumerate(zip(study.datasets, study.dataset_file_sha256, strict=True)):
        path = (ROOT / name).resolve()
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Parent dataset bytes changed: {name}")
        parent = load_dataset(path)
        for label in parent.labels:
            teacher = label.analysis
            if (teacher.engine_sha256, teacher.network_sha256, teacher.requested_nodes, teacher.requested_depth) != (
                study.engine_sha256,
                study.network_sha256,
                1000,
                3,
            ):
                raise ValueError("Parent labels differ from the locked shallow teacher.")
            if any(
                teacher.settings.get(key) != value
                for key, value in {"Threads": "1", "Hash": "16", "MultiPV": "1", "Ponder": "false"}.items()
            ):
                raise ValueError("Parent labels differ from the locked teacher settings.")
        groups = defaultdict(list)
        for label in parent.split_labels("validation"):
            groups[label.source_id].append(label)
        keys = [
            min(labels, key=lambda label: digest([study.selection_seed, block, sid, label.input_sha256])).input_sha256
            for sid, labels in sorted(groups.items())
        ]
        subset = select_validation(parent, keys, selection_id=f"{study.name}-block-{block}")
        train = subset.split_labels("train")
        if (
            len(train) != study.train_positions
            or len({label.source_id for label in train}) != study.train_games
            or len(keys) != study.validation_games
        ):
            raise ValueError("Frozen dataset does not satisfy the planned position/source counts.")
        observations = {label.input_sha256 for label in subset.labels}
        histories = {tuple(source.snapshot.moves) for source in subset.sources}
        if len(histories) != len(subset.sources) or observations & all_inputs or histories & all_histories:
            raise ValueError("Selected inputs or source trajectories overlap across blocks/splits.")
        all_inputs.update(observations)
        all_histories.update(histories)
        selected.append(subset)
        blocks.append(
            {
                "block": block,
                "parent_path": str(path),
                "parent_sha256": parent.digest,
                "parent_file_sha256": expected,
                "selected_sha256": subset.digest,
                "train_inputs": [label.input_sha256 for label in train],
                "validation_inputs": [label.input_sha256 for label in subset.split_labels("validation")],
                "train_ply_counts": {
                    str(k): v for k, v in Counter(len(label.analysis.snapshot.moves) for label in train).items()
                },
            }
        )
    # All plans/identities are frozen before label acquisition; timing never selects inputs.
    return selected, {
        "study": study.model_dump(),
        "blocks": blocks,
        "reference": {"nodes": 1_000_000, "depth": None, "multipv": 1},
        "treatment": {"nodes": 100_000, "depth": None},
        "support": {
            "nodes": 1_000_000,
            "depth": None,
            "multipv": "all-legal",
            "wdl": True,
            "measure": "mean expected-score loss W+0.5D against common-depth complete exact candidates",
            "coverage": "all evaluation positions required for a promising conclusion",
            "mate": "retain separately; never convert to cp; WDL remains an engine estimate",
        },
        "selection": "minimum SHA256 of canonical [selection_seed, block, source_id, input_sha256] per validation game",
        "test_status": "exploratory: previously inspected validation source games",
        "decision_rule": (
            "all block seed-mean agreement deltas > 0, complete support, no all-block disadvantage increase"
        ),
    }


def summarize(trials: list[dict], study: Study) -> dict:
    blocks = []
    for block in range(len(study.datasets)):
        rows = [row for row in trials if row["block"] == block]
        expected = {(case, seed) for case in ("baseline", "strong") for seed in study.seeds}
        if len(rows) != len(expected) or {(r["case"], r["seed"]) for r in rows} != expected:
            continue
        if any(row["status"] != "complete" for row in rows):
            continue
        by_case = {case: {r["seed"]: r for r in rows if r["case"] == case} for case in ("baseline", "strong")}
        pairs = []
        for seed in study.seeds:
            a, b = by_case["baseline"][seed], by_case["strong"][seed]
            if a["evaluation_inputs"] != b["evaluation_inputs"]:
                raise ValueError("Paired students were evaluated on different inputs.")
            # Match coverage within the pair; unknown entries never become zero loss.
            losses = [
                (x["expected_score_loss"], y["expected_score_loss"])
                for x, y in zip(a["disadvantages"], b["disadvantages"], strict=True)
                if x["status"] == y["status"] == "complete"
            ]
            pairs.append(
                {
                    "seed": seed,
                    "agreement_delta": b["evaluation"]["agreement"] - a["evaluation"]["agreement"],
                    "cross_entropy_delta": b["evaluation"]["cross_entropy"] - a["evaluation"]["cross_entropy"],
                    "matched_support": len(losses),
                    "expected_support": study.validation_games,
                    "disadvantage_delta": mean(y - x for x, y in losses) if losses else None,
                }
            )
        complete_support = all(p["matched_support"] == study.validation_games for p in pairs)
        blocks.append(
            {
                "block": block,
                "pairs": pairs,
                "agreement_delta": mean(p["agreement_delta"] for p in pairs),
                "cross_entropy_delta": mean(p["cross_entropy_delta"] for p in pairs),
                "support_complete": complete_support,
                "disadvantage_delta": mean(p["disadvantage_delta"] for p in pairs) if complete_support else None,
                "baseline_agreement": mean(r["evaluation"]["agreement"] for r in by_case["baseline"].values()),
                "strong_agreement": mean(r["evaluation"]["agreement"] for r in by_case["strong"].values()),
            }
        )
    complete = len(blocks) == len(study.datasets)
    support = complete and all(b["support_complete"] for b in blocks)
    promising = (
        support
        and all(b["agreement_delta"] > 0 for b in blocks)
        and not all(b["disadvantage_delta"] > 0 for b in blocks)
    )
    return {
        "planned_fits": len(study.datasets) * 2 * len(study.seeds),
        "completed_fits": sum(row["status"] == "complete" for row in trials),
        "planned_blocks": len(study.datasets),
        "complete_blocks": len(blocks),
        "blocks": blocks,
        "agreement_delta": mean(b["agreement_delta"] for b in blocks) if complete else None,
        "outcome": "promising" if promising else "inconclusive",
        "interpretation": "exploratory reference imitation; not playing strength or independent seed datasets",
    }


def archive_source(output: Path) -> dict:
    files = [
        *sorted((ROOT / "src/qi").rglob("*.py")),
        ROOT / "scripts/run_teacher_quality.py",
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
    ]
    hashes = {}
    for path in files:
        rel = path.relative_to(ROOT)
        target = output / "source" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        hashes[str(rel)] = sha256(target.read_bytes()).hexdigest()
    return {**source_identity(), "preserved_files_sha256": hashes}


def run(study: Study, output: Path) -> dict:
    from qi.learning.train import measure, train
    from qi.players.policy.runtime import load_checkpoint

    # Fresh output only, including preflight failures and frozen selection receipts.
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    deadline = started + study.seconds
    state = {"status": "running", "phase": "preflight", "queries": 0, "trials": [], "phases_seconds": {}}

    def save():
        state["seconds"] = perf_counter() - started
        state["summary"] = summarize(state["trials"], study)
        write_json(output / "status.json", state, indent=2)

    def remaining():
        value = deadline - perf_counter()
        if value <= 0:
            raise TimeoutError("Study reached its total wall-time allowance.")
        return value

    try:
        save()
        write_json(output / "study.json", study.model_dump(), indent=2)
        selected, protocol = prepare_inputs(study)
        write_json(output / "protocol.json", protocol, indent=2)
        write_json(output / "source.json", archive_source(output), indent=2)
        for block, dataset in enumerate(selected):
            write_json(output / f"block-{block}-baseline.json", dataset.model_dump(), indent=2)
        config = TeacherConfig(
            (ROOT / study.engine).resolve(),
            (ROOT / study.network).resolve(),
            depth=None,
            nodes=100_000,
            timeout_seconds=60,
        )
        identity = TeacherIdentity.read(config)
        if (identity.engine_sha256, identity.network_sha256) != (study.engine_sha256, study.network_sha256):
            raise ValueError("Teacher resources differ from the pinned protocol.")
        prepared = []
        with (output / "answers.jsonl").open("x") as log, TeacherSession(config, identity=identity) as session:

            def query(label, block, phase, settings):
                state["phase"] = phase
                tick = perf_counter()
                analysis = session.analyze(
                    label.analysis.snapshot.game(), replace(settings, timeout_seconds=min(60, remaining()))
                )
                log.write(
                    json.dumps(
                        {
                            "block": block,
                            "phase": phase,
                            "input_sha256": label.input_sha256,
                            "analysis": analysis.model_dump(),
                        }
                    )
                    + "\n"
                )
                log.flush()
                state["queries"] += 1
                state["phases_seconds"][phase] = state["phases_seconds"].get(phase, 0) + perf_counter() - tick
                if state["queries"] % 64 == 0:
                    save()
                    print(
                        json.dumps(
                            {"phase": phase, "queries": state["queries"], "seconds": round(state["seconds"], 1)}
                        ),
                        flush=True,
                    )
                return analysis

            for block, baseline in enumerate(selected):
                strong = relabel(
                    baseline,
                    {label.input_sha256: query(label, block, "strong-labels", config) for label in baseline.labels},
                )
                write_json(output / f"block-{block}-strong.json", strong.model_dump(), indent=2)
                references, assessments = [], {}
                for label in baseline.split_labels("validation"):
                    ref_config = replace(config, nodes=1_000_000)
                    references.append(
                        label.model_copy(update={"analysis": query(label, block, "reference", ref_config)})
                    )
                    game = label.analysis.snapshot.game()
                    multi = replace(ref_config, multipv=len(legal_moves(game.board, game.turn)), show_wdl=True)
                    assessments[label.input_sha256] = candidates(query(label, block, "candidate-reference", multi))
                write_json(output / f"block-{block}-reference.json", [r.model_dump() for r in references], indent=2)
                write_json(output / f"block-{block}-candidates.json", assessments, indent=2)
                prepared.append((baseline, strong, references, assessments))
        # No outcome-dependent decisions: all labels and reference data precede every fit.
        if TeacherIdentity.read(config) != identity:
            raise ValueError("Teacher resources changed during preparation.")
        state["phase"] = "fitting"
        save()
        for block, (baseline, strong, references, assessments) in enumerate(prepared):
            games = [label.analysis.snapshot.game() for label in references]
            for seed_index, seed in enumerate(study.seeds):
                # Alternate treatment order to avoid assigning all background drift to one case.
                cases = [("baseline", baseline), ("strong", strong)]
                if (block + seed_index) % 2:
                    cases.reverse()
                for case, dataset in cases:
                    remaining()
                    name = f"block-{block}-{case}-seed-{seed}"
                    recipe = Recipe(
                        name=name,
                        data=DataSettings(
                            dataset=str((output / f"block-{block}-{case}.json").resolve()),
                            train_size=study.train_positions,
                            selection="source-order",
                        ),
                        training=TrainingSettings(seed=seed, updates=study.updates),
                        execution=ExecutionSettings(
                            fit_seconds=min(600, remaining()), total_seconds=min(7200, remaining())
                        ),
                    )
                    write_json(output / f"{name}.config.json", recipe.model_dump(), indent=2)
                    row = {"block": block, "case": case, "seed": seed, "name": name, "status": "running"}
                    state["trials"].append(row)
                    save()
                    tick = perf_counter()
                    result = train(
                        dataset,
                        output / f"{name}.pt",
                        seed=seed,
                        steps=study.updates,
                        seconds=min(600, remaining()),
                        train_inputs=recipe.training_inputs(dataset),
                    )
                    write_json(output / f"{name}.report.json", result, indent=2)
                    if result["status"] != "complete":
                        row["status"] = "incomplete"
                        raise TimeoutError("A fit exhausted its allowance before all fixed updates completed.")
                    remaining()
                    policy = load_checkpoint(result["checkpoint"], result["checkpoint_sha256"])
                    metrics, predictions = measure(policy, references, games)
                    row.update(
                        status="complete",
                        checkpoint_sha256=result["checkpoint_sha256"],
                        evaluation_inputs=[label.input_sha256 for label in references],
                        evaluation=metrics,
                        predictions=predictions,
                        disadvantages=[
                            disadvantage(assessments[label.input_sha256], move)
                            for label, move in zip(references, predictions, strict=True)
                        ],
                        seconds=perf_counter() - tick,
                    )
                    write_json(output / f"{name}.evaluation.json", row, indent=2)
                    save()
                    print(
                        json.dumps(
                            {"trial": name, "agreement": metrics["agreement"], "seconds": round(state["seconds"], 1)}
                        ),
                        flush=True,
                    )
        remaining()
        state["status"] = "complete"
        state["phase"] = "complete"
    except BaseException as exc:
        state["status"] = (
            "deadline"
            if isinstance(exc, TimeoutError)
            else "interrupted"
            if isinstance(exc, KeyboardInterrupt)
            else "failed"
        )
        state["error"] = f"{type(exc).__name__}: {exc}"
        for row in state["trials"]:
            if row["status"] == "running":
                row["status"] = "incomplete" if state["status"] in ("deadline", "interrupted") else "failed"
        save()
        if not isinstance(exc, (Exception, KeyboardInterrupt)):
            raise
    save()
    receipts = {
        str(path.relative_to(output)): sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.rglob("*"))
        if path.is_file() and "source" not in path.relative_to(output).parts
    }
    write_json(output / "receipts.json", receipts, indent=2)
    return state
