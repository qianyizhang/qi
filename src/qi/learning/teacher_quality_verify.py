"""Recompute completed study evidence without querying a teacher or fitting weights."""

import json
from collections.abc import Callable
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


def verify(output: Path, *, progress: Callable[[str], None] | None = None) -> dict:
    """Verify saved evidence with one CPU thread, restoring the caller's setting."""
    import torch

    threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        return _verify(output.resolve(), progress or (lambda _message: None))
    finally:
        torch.set_num_threads(threads)


def _verify(output: Path, progress: Callable[[str], None]) -> dict:
    from qi.learning.train import measure
    from qi.players.policy.runtime import load_checkpoint

    def read(name):
        if name not in receipts:
            raise ValueError(f"Missing file receipt: {name}")
        return json.loads((output / name).read_text())

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    progress("Checking saved file receipts")
    receipts = json.loads((output / "receipts.json").read_text())
    for name, expected in receipts.items():
        require(sha256((output / name).read_bytes()).hexdigest() == expected, f"Receipt mismatch: {name}")
    study = Study.model_validate(read("study.json"))
    state = read("status.json")
    if state["phase"] == "preflight" and state["status"] in ("failed", "deadline", "interrupted"):
        require(
            not state["trials"] and state["queries"] == 0 and bool(state.get("error")),
            "Missing frozen protocol for a started study",
        )
        summary = summarize([], study)
        require(summary == state["summary"], "Summary mismatch")
        return {
            "verified": True,
            "scope": "preflight-failure-receipts",
            "status": state["status"],
            "queries": 0,
            "summary": summary,
        }
    require("protocol.json" in receipts, "Missing frozen protocol for a started study")
    for name, expected in read("source.json")["preserved_files_sha256"].items():
        require(sha256((output / "source" / name).read_bytes()).hexdigest() == expected, f"Source mismatch: {name}")
    progress("Replaying parent data and frozen input selection")
    selected, protocol = prepare_inputs(study)
    require(protocol == read("protocol.json"), "Frozen selection/protocol mismatch")
    answers = {}
    require("answers.jsonl" in receipts, "Missing file receipt: answers.jsonl")
    lookup = {(block, label.input_sha256): label for block, dataset in enumerate(selected) for label in dataset.labels}
    for line in (output / "answers.jsonl").read_text().splitlines():
        record = json.loads(line)
        key = (record["block"], record["phase"], record["input_sha256"])
        require(key not in answers, "Duplicate teacher query")
        require(record["phase"] in ("strong-labels", "reference", "candidate-reference"), "Unknown query phase")
        label = lookup.get((record["block"], record["input_sha256"]))
        require(label is not None, "Unknown query input")
        analysis = TeacherAnalysis.model_validate(record["analysis"])
        require(
            analysis.snapshot == label.analysis.snapshot and analysis.state_hash == label.analysis.state_hash,
            "Teacher query changed the frozen input",
        )
        require(
            (analysis.engine_sha256, analysis.network_sha256) == (study.engine_sha256, study.network_sha256)
            and analysis.requested_depth is None
            and analysis.requested_nodes == (100_000 if record["phase"] == "strong-labels" else 1_000_000),
            "Teacher identity or budget mismatch",
        )
        answers[key] = analysis
    require(len(answers) == state["queries"], "Query denominator mismatch")
    for block, baseline in enumerate(selected):
        progress(f"Checking block {block + 1}/{len(selected)} data and checkpoints")
        require(f"block-{block}-baseline.json" in receipts, "Missing baseline receipt")
        require(load_dataset(output / f"block-{block}-baseline.json") == baseline, "Baseline selection mismatch")
        if not (output / f"block-{block}-strong.json").exists():
            require(
                state["status"] != "complete" and not any(r["block"] == block for r in state["trials"]),
                "Missing relabeled dataset for started fits",
            )
            continue  # Interrupted preparation is evidence, not a completed block.
        require(f"block-{block}-strong.json" in receipts, "Missing relabeled dataset receipt")
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
            require(f"{name}.pt" in receipts, "Missing checkpoint receipt")
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
        require(
            summary["completed_fits"] == summary["planned_fits"]
            and summary["complete_blocks"] == summary["planned_blocks"],
            "Incomplete planned fits or blocks",
        )
        require(len(answers) == len(selected) * (study.train_positions + 3 * study.validation_games), "Missing queries")
    return {"verified": True, "status": state["status"], "queries": len(answers), "summary": summary}
