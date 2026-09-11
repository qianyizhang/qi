"""Audit retained follow-up runs, sealed-input exclusion and the resource pilot."""

import hashlib
import json
from pathlib import Path
from time import perf_counter

import torch

from qi.learning.snapshot import SnapshotTensors, evaluate
from qi.players.policy.runtime import load_checkpoint

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "artifacts/learning/generated-followups-v1"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    started = perf_counter()
    output = RUN / "closeout-audit.json"
    pilot_predictions = RUN / "scaling/pilot-independent-predictions.jsonl"
    if output.exists() or pilot_predictions.exists():
        raise ValueError("Retain existing closeout evidence; choose a new audit implementation if needed.")
    config = read(RUN / "config.json")
    collection_sha = digest(ROOT / config["collection"])
    if collection_sha != config["collection_sha256"]:
        raise ValueError("Original collection changed after selection/preparation.")
    for name, sha in config["frozen_files"].items():
        if digest(ROOT / name) != sha:
            raise ValueError(f"Frozen input changed: {name}")
    sealed = {r["input"] for r in read(ROOT / config["parent"] / "plan/sealed-test-inputs.json")}
    semantic, scaling = [read(RUN / study / "verification.json") for study in ("semantic", "scaling")]
    if (semantic["status"], semantic["complete_fits"], scaling["status"], scaling["complete_fits"]) != (
        "verified",
        18,
        "verified",
        30,
    ):
        raise ValueError("Both matrices must be independently verified before closeout.")
    for study in ("semantic", "scaling"):
        for name, sha in read(RUN / study / "receipts.json").items():
            if digest(RUN / name) != sha:
                raise ValueError("A receipted run artifact changed.")
    charged = scaling["elapsed_seconds"] + scaling["prior_stage_seconds"] + scaling["prior_attempt_seconds"]
    if scaling["prior_stage_seconds"] != semantic["elapsed_seconds"] + semantic["prior_attempt_seconds"]:
        raise ValueError("Earlier attempts were not charged exactly once.")
    if charged > config["execution"]["total_seconds"]:
        raise ValueError("Combined elapsed allowance exceeded.")
    runs = []
    for study in ("semantic", "scaling"):
        for path in sorted((RUN / study).glob("study*/*/report.json")):
            report, cfg = read(path), read(path.parent / "config.json")
            if report["status"] != "complete" or report["completed_updates"] != cfg["training"]["updates"]:
                raise ValueError("A retained fit is incomplete.")
            if report["process_peak_rss_bytes"] > config["execution"]["max_rss_bytes"]:
                raise ValueError("Retained process peak RSS exceeds the frozen ceiling.")
            if cfg["execution"]["fit_seconds"] > config["execution"]["fit_seconds"]:
                raise ValueError("A retained fit changed its configured deadline.")
            predictions = path.parent / "predictions.jsonl"
            scored = {json.loads(line)["input_hash"] for line in predictions.read_text().splitlines()}
            if scored & sealed:
                raise ValueError("A retained fit scored a sealed input.")
            runs.append(
                {
                    "path": str(path.relative_to(RUN)),
                    "report_sha256": digest(path),
                    "predictions_sha256": digest(predictions),
                    "scored_inputs": len(scored),
                    "updates": report["completed_updates"],
                    "elapsed_seconds": report["elapsed_seconds"],
                    "process_peak_rss_bytes": report["process_peak_rss_bytes"],
                }
            )
    if len(runs) != 52:
        raise ValueError("Expected 48 comparative fits, one pilot and three retained earlier controls.")
    pilot = RUN / "scaling/study/resource-pilot"
    report = read(pilot / "report.json")
    torch.set_num_threads(1)
    loaded = load_checkpoint(str(pilot / "policy.pt"), digest(pilot / "policy.pt"))
    if loaded.metadata.seed != 917 or loaded.metadata.steps != 200:
        raise ValueError("Resource pilot metadata changed.")
    data = SnapshotTensors(RUN / "scaling/tensors/mixed-16000")
    stats = evaluate(loaded.model, data, pilot_predictions, chunk_size=config["chunk_size"])
    if stats != report["stats"] or digest(pilot_predictions) != digest(pilot / "predictions.jsonl"):
        raise ValueError("Independent resource-pilot reload differs from retained predictions.")
    result = {
        "status": "verified",
        "collection_sha256": collection_sha,
        "frozen_files": len(config["frozen_files"]),
        "sealed_inputs": len(sealed),
        "sealed_inputs_scored": 0,
        "comparative_fits": 48,
        "resource_pilots": 1,
        "retained_prior_control_fits": 3,
        "charged_elapsed_seconds": charged,
        "allowance_seconds": config["execution"]["total_seconds"],
        "pilot_independent_predictions_sha256": digest(pilot_predictions),
        "runs": runs,
        "audit_source_sha256": digest(Path(__file__)),
        "audit_elapsed_seconds": perf_counter() - started,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "runs"}))


if __name__ == "__main__":
    main()
