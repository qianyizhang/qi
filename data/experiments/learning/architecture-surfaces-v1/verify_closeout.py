"""Independently check the complete architecture matrix and retained teacher evidence."""

import argparse
import json
from pathlib import Path

import torch

from qi.artifacts import write_json
from qi.evaluation import Corpus
from qi.game import Game
from qi.learning.snapshot import SnapshotTensors
from qi.players.policy.encoding import input_key
from qi.teacher import digest
from qi.training_data.v1 import reserved_inputs

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "artifacts/learning"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(config_path, output):
    require(not output.exists(), "Choose a fresh closeout output directory.")
    inputs = {}

    def receipt(path):
        path = Path(path).resolve()
        value = digest(path)
        inputs[str(path.relative_to(ROOT))] = value
        return value

    def read(path):
        receipt(path)
        return json.loads(Path(path).read_text())

    def fresh_verification(study, expected):
        candidates = [(p, read(p)) for p in study.glob("verification-*.json")]
        candidates = [(p, v) for p, v in candidates if v.get("status") == "verified"]
        require(bool(candidates), "Missing completed fresh-process verification.")
        path, value = max(candidates, key=lambda pair: pair[1]["finished"])
        require(value["pid"] != read(study / "lineage.json")["pid"], "Verification reused the training process.")
        require(value["source_run_status"] == "complete", "Verification preceded complete execution.")
        require(value["verified_observations"] == len(value["checkpoints"]) == expected, "Reload count mismatch.")
        return path, value

    torch.set_num_threads(1)
    config = read(config_path)
    study, teacher, smoke = (
        BASE / name
        for name in (
            "architecture-surfaces-v1/study",
            "architecture-surfaces-v1-teacher",
            "architecture-surfaces-v1-smoke",
        )
    )
    report, lineage = read(study / "report.json"), read(study / "lineage.json")
    require(report["status"] == "complete" and report["completed_fits"] == 15, "Scientific matrix is incomplete.")
    require(
        receipt(config_path) == receipt(study / "submitted-config.json") == lineage["submitted_config_sha256"],
        "Protocol SHA mismatch.",
    )
    resolved = read(study / "config.json")
    require(all(resolved[k] == value for k, value in config.items()), "Resolved settings changed.")
    for name, expected in lineage["files"].items():
        require(
            receipt(ROOT / name) == receipt(study / "lineage" / name) == expected, f"Training source changed: {name}"
        )
    cache_path = ROOT / config["data"]["cache"]
    require(receipt(cache_path / "manifest.json") == config["data"]["manifest_sha256"], "Cache manifest changed.")
    cache = SnapshotTensors(cache_path)
    sealed_path = ROOT / config["data"]["sealed_inputs"]
    require(receipt(sealed_path) == config["data"]["sealed_sha256"], "Sealed identity file changed.")
    sealed = {row["input"] for row in read(sealed_path)}
    snapshot = read(Path(cache.manifest["snapshot"]) / "manifest.json")
    reserved = reserved_inputs(Corpus.model_validate(snapshot["recipe"]["reserved_corpus"]))
    exact, canonical = {"train": set(), "validation": set()}, {"train": set(), "validation": set()}
    for row in cache.rows():
        original = input_key(Game(board=row["board"], turn=row["turn"]))
        opposite = input_key(Game(board=row["board"][::-1].swapcase(), turn="black" if row["turn"] == "red" else "red"))
        require(
            original == row["input_hash"] and original not in exact[row["split"]],
            "Duplicate or invalid input identity.",
        )
        require(not {original, opposite} & (sealed | reserved), "Original/opposite input intersects protected data.")
        exact[row["split"]].add(original)
        canonical[row["split"]].add(min(original, opposite))
    require((len(exact["train"]), len(exact["validation"]), len(sealed)) == (4000, 373, 3900), "Input counts changed.")
    require(
        not exact["train"] & exact["validation"] and not canonical["train"] & canonical["validation"], "Split overlap."
    )
    require(all(len(canonical[s]) == len(exact[s]) for s in exact), "Canonical duplicates within a split.")
    audit = read(BASE / "architecture-surfaces-v1-data-verified/data-audit.json")["datasets"]["mixed-4000"]
    require(
        audit["cache_fingerprint"] == cache.manifest["fingerprint"] and audit["inputs_unchanged"],
        "Audit cache mismatch.",
    )
    equivalence = audit["input_equivalence"]
    require(
        not equivalence["original_cross_split"] and not equivalence["canonical_cross_split"],
        "Persisted audit reports overlap.",
    )
    require(
        all(not v["original_matches"] and not v["opposite_color_matches"] for v in equivalence["exclusions"].values()),
        "Persisted exclusion audit failed.",
    )
    expected_fits = {f"{case}-seed-{seed}" for case in config["cases"] for seed in config["seeds"]}
    require(
        len(expected_fits) == 15 and {p.name for p in (study / "fits").iterdir()} == expected_fits,
        "Fit matrix mismatch.",
    )
    expected_checkpoints = set()
    for name in sorted(expected_fits):
        fit_path = study / "fits" / name
        fit = read(fit_path / "report.json")
        require(
            fit["status"] == "complete" and fit["completed_updates"] == 200 and fit["observations"] == [50, 200],
            "Incomplete fit.",
        )
        checkpoints = sorted(fit_path.glob("checkpoint-*"))
        require(
            [p.name for p in checkpoints] == ["checkpoint-0050", "checkpoint-0200"], "Checkpoint inventory mismatch."
        )
        for checkpoint in checkpoints:
            expected_checkpoints.add(checkpoint.resolve())
            observation = read(checkpoint / "observation.json")
            require(receipt(checkpoint / "model.pt") == observation["checkpoint_sha256"], "Checkpoint hash mismatch.")
            predictions_path = checkpoint / "dev-predictions.jsonl"
            require(receipt(predictions_path) == observation["dev_predictions_sha256"], "Prediction hash mismatch.")
            predictions = [json.loads(line) for line in predictions_path.read_text().splitlines()]
            require(
                len(predictions) == 373 and {r["input_hash"] for r in predictions} == exact["validation"],
                "Scored input set mismatch.",
            )
    verification_path, reloads = fresh_verification(study, 30)
    require(
        {Path(item["path"]).resolve() for item in reloads["checkpoints"]} == expected_checkpoints,
        "Reload matrix mismatch.",
    )
    for item in reloads["checkpoints"]:
        checkpoint = Path(item["path"])
        require(
            item["status"] == "exact_reload_equal" and receipt(checkpoint / "model.pt") == item["checkpoint_sha256"],
            "Reload checkpoint changed.",
        )
        require(
            receipt(checkpoint / f"verified-dev-{reloads['pid']}.jsonl")
            == receipt(checkpoint / "dev-predictions.jsonl"),
            "Fresh reload predictions changed.",
        )
    baseline_parity = []
    for seed in config["seeds"]:
        new = study / "fits" / f"absolute_mlp64-seed-{seed}" / "checkpoint-0200/model.pt"
        old = BASE / "generated-followups-v1/scaling/study" / f"mixed-4000-updates-200-seed-{seed}/policy.pt"
        current, previous = (torch.load(p, map_location="cpu", weights_only=True)["state_dict"] for p in (new, old))
        require(
            current.keys() == previous.keys() and all(torch.equal(current[k], previous[k]) for k in current),
            "Historical baseline tensor mismatch.",
        )
        baseline_parity.append(
            {"seed": seed, "tensor_equal": True, "current_sha256": receipt(new), "historical_sha256": receipt(old)}
        )
    teacher_verification, teacher_status = read(teacher / "verification.json"), read(teacher / "status.json")
    require(read(teacher / "config.json") == config, "Teacher protocol differs from the study.")
    require(
        teacher_verification["verified"]
        and teacher_verification["successful_queries"] == teacher_verification["queries"] == 144,
        "Teacher verification incomplete.",
    )
    require(
        teacher_status["status"] == "complete" and teacher_status["successful_queries"] == 144,
        "Teacher execution incomplete.",
    )
    for name, expected in read(teacher / "receipts.json").items():
        require(receipt(teacher / name) == expected, f"Teacher receipt changed: {name}")
    selected = read(teacher / "selection.json")
    require(
        len(selected) == len({r["row"]["input_hash"] for r in selected}) == 48
        and {r["row"]["input_hash"] for r in selected} <= exact["validation"],
        "Teacher selection is not 48 unique development inputs.",
    )
    smoke_report = read(smoke / "report.json")
    require(
        smoke_report["status"] == "complete"
        and len(smoke_report["fits"]) == 5
        and {f["case"] for f in smoke_report["fits"]} == set(config["cases"]),
        "Smoke matrix mismatch.",
    )
    require(
        all(
            f["status"] == "complete" and f["completed_updates"] == 1 and f["observations"] == [1]
            for f in smoke_report["fits"]
        ),
        "Smoke was not five one-update fits.",
    )
    smoke_verification, _ = fresh_verification(smoke, 5)
    model_seconds, teacher_seconds = report["elapsed_seconds"], teacher_status["seconds"]
    require(
        model_seconds < config["execution"]["total_seconds"] == 1800
        and teacher_seconds < config["teacher"]["total_seconds"] == 900
        and model_seconds + teacher_seconds < 2700,
        "Separate or combined study allowance exceeded.",
    )
    result = {
        "verified": True,
        "fits": 15,
        "checkpoint_observations": 30,
        "development_inputs": 373,
        "sealed_scored": 0,
        "baseline_tensor_parity": baseline_parity,
        "runner_verification": str(verification_path),
        "teacher_queries": 144,
        "teacher_inputs": 48,
        "model_seconds": model_seconds,
        "teacher_seconds": teacher_seconds,
        "combined_charged_seconds": model_seconds + teacher_seconds,
        "smoke_seconds_separate": smoke_report["elapsed_seconds"],
        "smoke_verification": str(smoke_verification),
        "limitations": "Host-contended timing; figures and analysis postprocessors are separate from training lineage.",
    }
    output.mkdir(parents=True)
    write_json(output / "verification.json", result, indent=2)
    receipt(Path(__file__))
    write_json(
        output / "receipts.json",
        {"inputs": inputs, "verification_sha256": digest(output / "verification.json")},
        indent=2,
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.config.resolve(), args.output.resolve())))
