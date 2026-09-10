"""Recompute completed study evidence without querying a teacher or fitting weights."""

import json
from hashlib import sha256
from math import isclose
from pathlib import Path

from qi.learning.config import Recipe
from qi.learning.teacher_quality import Study, prepare_inputs, summarize
from qi.learning.teacher_quality_scores import candidates, disadvantage
from qi.teacher import TeacherAnalysis
from qi.training_data.loading import load_dataset
from qi.training_data.relabel import relabel
from qi.training_data.v1 import Label


def verify(output: Path) -> dict:
    from qi.learning.train import measure
    from qi.players.policy.runtime import load_checkpoint

    def read(name):
        return json.loads((output / name).read_text())

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    receipts = read("receipts.json")
    for name, expected in receipts.items():
        require(sha256((output / name).read_bytes()).hexdigest() == expected, f"Receipt mismatch: {name}")
    for name, expected in read("source.json")["preserved_files_sha256"].items():
        require(sha256((output / "source" / name).read_bytes()).hexdigest() == expected, f"Source mismatch: {name}")
    study = Study.model_validate(read("study.json"))
    state = read("status.json")
    selected, protocol = prepare_inputs(study)
    require(protocol == read("protocol.json"), "Frozen selection/protocol mismatch")
    answers = {}
    for line in (output / "answers.jsonl").read_text().splitlines():
        record = json.loads(line)
        key = (record["block"], record["phase"], record["input_sha256"])
        require(key not in answers, "Duplicate teacher query")
        analysis = TeacherAnalysis.model_validate(record["analysis"])
        require(
            (analysis.engine_sha256, analysis.network_sha256) == (study.engine_sha256, study.network_sha256)
            and analysis.requested_depth is None
            and analysis.requested_nodes == (100_000 if record["phase"] == "strong-labels" else 1_000_000),
            "Teacher identity or budget mismatch",
        )
        answers[key] = analysis
    require(len(answers) == state["queries"], "Query denominator mismatch")
    for block, baseline in enumerate(selected):
        require(load_dataset(output / f"block-{block}-baseline.json") == baseline, "Baseline selection mismatch")
        if not (output / f"block-{block}-strong.json").exists():
            continue  # Interrupted preparation is evidence, not a completed block.
        strong = load_dataset(output / f"block-{block}-strong.json")
        rebuilt = relabel(
            baseline,
            {label.input_sha256: answers[block, "strong-labels", label.input_sha256] for label in baseline.labels},
        )
        require(strong == rebuilt, "Relabel lineage mismatch")
        rows = [r for r in state["trials"] if r["block"] == block and r["status"] == "complete"]
        if not rows:
            continue
        references = [Label.model_validate(row) for row in read(f"block-{block}-reference.json")]
        expected_refs = [
            label.model_copy(update={"analysis": answers[block, "reference", label.input_sha256]})
            for label in baseline.split_labels("validation")
        ]
        require(references == expected_refs, "Shared reference identity mismatch")
        assessments = {
            label.input_sha256: candidates(answers[block, "candidate-reference", label.input_sha256])
            for label in references
        }
        require(assessments == read(f"block-{block}-candidates.json"), "Candidate projection mismatch")
        for row in rows:
            name = row["name"]
            require(row == read(f"{name}.evaluation.json"), "Trial projection mismatch")
            dataset = baseline if row["case"] == "baseline" else strong
            config = Recipe.model_validate(read(f"{name}.config.json"))
            report = read(f"{name}.report.json")
            policy = load_checkpoint(str(output / f"{name}.pt"), row["checkpoint_sha256"])
            metadata = policy.metadata
            require(
                metadata.dataset_sha256 == dataset.digest
                and metadata.train_inputs == config.training_inputs(dataset)
                and metadata.seed == row["seed"] == config.training.seed
                and metadata.steps == study.updates == report["completed_steps"]
                and metadata.learning_rate == 0.01
                and metadata.training_device == "cpu"
                and metadata.training_threads == 1
                and report["reload_predictions_equal"],
                "Checkpoint recipe or lineage mismatch",
            )
            require(row["evaluation_inputs"] == [r.input_sha256 for r in references], "Evaluation inputs mismatch")
            metrics, predictions = measure(policy, references)
            require(predictions == row["predictions"], "Checkpoint predictions mismatch")
            for key, value in metrics.items():
                if key != "mean_inference_ms":
                    require(isclose(value, row["evaluation"][key], abs_tol=1e-6), f"Metric mismatch: {key}")
            losses = [
                disadvantage(assessments[label.input_sha256], move)
                for label, move in zip(references, predictions, strict=True)
            ]
            require(losses == row["disadvantages"], "Move disadvantage mismatch")
    summary = summarize(state["trials"], study)
    require(summary == state["summary"], "Summary mismatch")
    if state["status"] == "complete":
        require(summary["completed_fits"] == summary["planned_fits"], "Incomplete planned fits")
        require(len(answers) == len(selected) * (study.train_positions + 3 * study.validation_games), "Missing queries")
    return {"verified": True, "status": state["status"], "queries": len(answers), "summary": summary}
