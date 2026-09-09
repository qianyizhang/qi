"""Fresh, predeclared source blocks for AB-LEARN-007; no outcome-based selection."""

import argparse
import json
import shutil
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from random import Random
from threading import Lock
from time import perf_counter

from investigate_source_coverage import match_plies, ply
from run_source_coverage import write

from qi.evaluation import Corpus
from qi.learning.config import DataSettings, ExecutionSettings, Recipe, TrainingSettings
from qi.learning.experiment import source_identity
from qi.teacher import TeacherConfig, analyze, digest
from qi.training_data.selection import select_training
from qi.training_data.v1 import Dataset, generate, teacher_identity


def archive_source(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    for name in ("src", "scripts"):
        shutil.copytree(name, output / name, ignore=shutil.ignore_patterns("__pycache__", "static"))
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy2(name, output / name)
    write(output / "identity.json", source_identity())


def generate_blocks(config: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    write(output / "protocol.json", config)
    archive_source(output / "generation-source")
    teacher = TeacherConfig(
        **{
            **config["teacher"],
            "engine": Path(config["teacher"]["engine"]),
            "network": Path(config["teacher"]["network"]),
        }
    )
    if {name: digest(getattr(teacher, name)) for name in ("engine", "network")} != config["teacher_hashes"]:
        raise ValueError("Teacher bytes differ from the locked protocol.")
    corpus = Corpus.model_validate_json(Path(config["corpus"]).read_text())
    if corpus.digest != config["corpus_sha256"]:
        raise ValueError("Reserved corpus differs from protocol.")
    previous = {}
    for name in config["exclude_datasets"]:
        path = Path(name)
        raw = path.read_bytes()
        previous[name] = {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
    write(output / "excluded-artifacts.json", previous)
    audit = None
    if "sampler_audit" in config:
        audit_bytes = Path(config["sampler_audit"]).read_bytes()
        if sha256(audit_bytes).hexdigest() != config["sampler_audit_sha256"]:
            raise ValueError("Data-only sampler audit changed.")
        audit = json.loads(audit_bytes)
        write(output / "sampler-audit.json", audit)
    for block, seed in enumerate(config["generation_seeds"]):
        started, lock, count = perf_counter(), Lock(), 0
        with (output / f"block-{block}-answers.jsonl").open("x") as answers:

            def labeler(game, settings, *, lock=lock, block=block, started=started):
                nonlocal count
                result = analyze(game, settings)
                with lock:
                    answers.write(result.model_dump_json() + "\n")
                    answers.flush()
                    count += 1
                    if count % 256 == 0:
                        print(
                            json.dumps(
                                {"block": block, "answers": count, "seconds": round(perf_counter() - started, 2)}
                            ),
                            flush=True,
                        )
                return result

            try:
                dataset = generate(corpus, teacher, seed=seed, **config["generation"], labeler=labeler)
            except Exception as exc:
                write(output / f"block-{block}-failure.json", {"error": str(exc), "answers": count})
                raise
        write(output / f"block-{block}-raw.json", dataset.model_dump())
        if (
            audit
            and sorted(label.input_sha256 for label in dataset.labels) != audit["blocks"][block]["generated_input_ids"]
        ):
            raise ValueError("Generated inputs differ from the data-only sampler audit; stop before training.")
        write(
            output / f"block-{block}-generation.json",
            {
                "seed": seed,
                "seconds": perf_counter() - started,
                "labels": len(dataset.labels),
                "dataset_sha256": dataset.digest,
            },
        )
        print(f"Generated block {block}: {len(dataset.labels)} labels", flush=True)


def prepare(output: Path) -> None:
    config = json.loads((output / "protocol.json").read_text())
    sampler_audit = json.loads((output / "sampler-audit.json").read_text()) if "sampler_audit" in config else None
    raw = [Dataset.model_validate_json((output / f"block-{i}-raw.json").read_text()) for i in range(3)]
    excluded, prior_histories = set(), set()
    evidence = json.loads((output / "excluded-artifacts.json").read_text())
    for name, identity in evidence.items():
        payload = Path(name).read_bytes()
        if sha256(payload).hexdigest() != identity["sha256"]:
            raise ValueError("Previously inspected artifact changed during generation.")
        data = json.loads(payload)
        excluded.update(label["input_sha256"] for label in data["labels"])
        prior_histories.update(tuple(source["snapshot"]["moves"]) for source in data["sources"])
    reference = Dataset.model_validate_json(Path(config["exclude_datasets"][-1]).read_text())
    expected_teacher = teacher_identity(reference.labels[0].analysis)
    counts = Counter(label.input_sha256 for dataset in raw for label in dataset.labels)
    excluded.update(key for key, count in counts.items() if count > 1)
    histories = set(prior_histories)
    trials, audits, parents, holdout_counts = [], [], {}, {}
    study_dir = output / "study"
    if study_dir.exists():
        raise ValueError("Choose a fresh study; do not overwrite prepared data.")
    for block, dataset in enumerate(raw):
        if any(teacher_identity(label.analysis) != expected_teacher for label in dataset.labels):
            raise ValueError("Teacher identity changed from the exploratory comparison.")
        for source in dataset.sources:
            history = tuple(source.snapshot.moves)
            if history in histories:
                raise ValueError("A new source duplicates an old or another new complete trajectory.")
            histories.add(history)
        kept = [label for label in dataset.labels if label.input_sha256 not in excluded]
        parent = Dataset.model_validate(dataset.model_copy(update={"labels": kept}).model_dump())
        write(output / f"block-{block}-filtered.json", parent.model_dump())
        parents[str(block)] = parent.digest
        holdout_counts[str(block)] = len(parent.split_labels("validation"))
        groups = defaultdict(list)
        for label in parent.split_labels("train"):
            groups[label.source_id].append(label)
        full = {key: labels for key, labels in groups.items() if len(labels) == 16}
        ids = sorted(full)
        Random(config["selection_seed"] + block).shuffle(ids)
        if len(ids) < 192:
            raise ValueError(f"Block {block} has only {len(ids)} eligible sources; stop, do not relax.")
        ids = ids[:192]
        concentrated = [label for sid in ids[:48] for label in full[sid]]
        target = Counter(map(ply, concentrated))
        broader = match_plies(full, ids, target, config["matching_seed"] + block)
        audit = {
            "block": block,
            "generation_seed": config["generation_seeds"][block],
            "eligible_sources": len(full),
            "source_ids": ids,
            "removed_inputs": len(dataset.labels) - len(kept),
            "ply_counts": dict(sorted(target.items())),
            "holdout_inputs": [label.input_sha256 for label in parent.split_labels("validation")],
            "cases": {},
        }
        for case, labels, games, quota in (("concentrated", concentrated, 48, 16), ("broader", broader, 192, 4)):
            keys = [label.input_sha256 for label in labels]
            if sampler_audit and sorted(keys) != sampler_audit["blocks"][block][case]:
                raise ValueError("Selected inputs differ from the prelabel feasibility audit.")
            per_source = Counter(label.source_id for label in labels)
            if (
                len(set(keys)) != 768
                or len(per_source) != games
                or set(per_source.values()) != {quota}
                or Counter(map(ply, labels)) != target
                or set(keys) & set(audit["holdout_inputs"])
            ):
                raise ValueError("Exact selection contract failed.")
            name = f"block-{block}-{case}"
            selected = select_training(parent, sorted(keys), selection_id=name)
            path = study_dir / "datasets" / f"{name}.json"
            write(path, selected.model_dump())
            audit["cases"][case] = {"input_ids": sorted(keys), "games": games, "labels": len(keys)}
            for seed in config["training_seeds"]:
                trial = f"{name}-seed-{seed}"
                recipe = Recipe(
                    name=name,
                    data=DataSettings(dataset=str(path.resolve()), train_size=768, selection="source-order"),
                    training=TrainingSettings(seed=seed),
                    execution=ExecutionSettings(fit_seconds=600.0, total_seconds=600.0),
                )
                write(study_dir / "configs" / f"{trial}.json", recipe.model_dump())
                trials.append({"name": trial, "block": block, "case": case, "seed": seed})
        audits.append(audit)
    write(output / "selection-audit.json", {"excluded_observations": len(excluded), "blocks": audits})
    write(
        study_dir / "study.json",
        {
            "work_id": "AB-LEARN-007",
            "parent_dataset_sha256": parents,
            "trials": trials,
            "holdout_counts": holdout_counts,
            "holdout_status": "fresh block-specific holdouts; protocol locked before predictions",
            "decision_rule": config["decision_rule"],
        },
    )
    archive_source(output / "training-source")
    print(json.dumps({"prepared_fits": len(trials), "holdout_counts": holdout_counts}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["generate", "prepare"])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.stage == "generate":
        if args.config is None:
            parser.error("generate requires --config")
        generate_blocks(json.loads(args.config.read_text()), args.output)
    else:
        prepare(args.output)


if __name__ == "__main__":
    main()
