"""Summarize independently verified mixture evidence without changing selection."""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

from qi.artifacts import write_json
from qi.teacher import digest


def action_diagnostics(root):
    """Post-screen description of legal-choice constraints; not a selection metric."""
    path = root / "tensors/block-0-plausible"
    manifest = json.loads((path / "manifest.json").read_text())
    for name in ("mask.npy", "rows.jsonl"):
        if digest(path / name) != manifest["files"][name]:
            raise ValueError("Frozen development evidence changed.")
    mask = np.load(path / "mask.npy", mmap_mode="r", allow_pickle=False)
    groups = defaultdict(list)
    for line in (path / "rows.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["split"] == "validation":
            count = int(mask[row["ordinal"]].sum())
            for key in ["all", row["bucket"]] + row["semantic_tags"]:
                groups[key].append(count)
    result = {
        key: {
            "positions": len(values),
            "mean_legal_moves": statistics.mean(values),
            "single_legal_move_positions": values.count(1),
            "uniform_legal_expected_agreement": statistics.mean(1 / n for n in values),
        }
        for key, values in groups.items()
    }
    return result


def summarize(root):
    verification = json.loads((root / "verification.json").read_text())
    if verification["status"] != "verified" or verification["complete_fits"] != 36:
        raise ValueError("Require the complete independently verified screen.")
    for name, expected in json.loads((root / "receipts.json").read_text()).items():
        if digest(root / name) != expected:
            raise ValueError("Verified evidence changed before summarization.")
    summary = json.loads((root / "study/summary.json").read_text())
    plan = json.loads((root / "plan/manifest.json").read_text())
    cases = {}
    for case, primary in verification["cases"].items():
        trials = [t for t in summary["trials"] if t["case"] == case]
        reports = [json.loads((root / "study" / t["name"] / "report.json").read_text()) for t in trials]
        slices = {}
        keys = [
            k for k in reports[0]["stats"] if k == "validation" or k.startswith(("validation:", "bucket:development-"))
        ]
        for key in keys:
            values = [r["stats"][key] for r in reports]
            if len({v["positions"] for v in values}) != 1:
                raise ValueError("Evaluation slice denominators changed.")
            slices[key] = {
                "positions_per_fit": values[0]["positions"],
                "mean_agreement": statistics.mean(v["agreement"] for v in values),
                "mean_cross_entropy": statistics.mean(v["cross_entropy"] for v in values),
                "correct_per_fit": [v["correct"] for v in values],
            }
        selected = [p for p in plan["plans"] if p["case"] == case]
        cases[case] = {
            **primary,
            "fits": len(trials),
            "train_mean_agreement": statistics.mean(r["stats"]["train"]["agreement"] for r in reports),
            "train_mean_cross_entropy": statistics.mean(r["stats"]["train"]["cross_entropy"] for r in reports),
            "fit_seconds": [r["elapsed_seconds"] for r in reports],
            "peak_process_rss_bytes": max(r["process_peak_rss_bytes"] for r in reports),
            "source_trajectories_by_block": [p["trajectories"] for p in selected],
            "max_inputs_per_trajectory_by_block": [p["max_inputs_per_trajectory"] for p in selected],
            "slices": slices,
        }
    pilot = json.loads((root / "pilot/report.json").read_text())
    result = {
        "experiment": "generated-source-mixing-v1",
        "execution": "complete",
        "complete_fits": 36,
        "train_inputs_per_fit": 4000,
        "development_inputs": verification["development_inputs"],
        "sealed_test_inputs": plan["sealed_test_inputs"],
        "sealed_test_scored": False,
        "training_blocks": 3,
        "initialization_seeds": [7, 17, 27],
        "primary": "equal-weight mean of six development policy/phase agreements",
        "advance": verification["advance"],
        "cases": cases,
        "post_screen_development_action_diagnostics": action_diagnostics(root),
        "matrix_elapsed_seconds": summary["elapsed_seconds"],
        "calibrated_fit_seconds": summary["fit_seconds"],
        "source": summary["source"],
        "resource_pilot": {
            k: pilot[k]
            for k in (
                "status",
                "completed_updates",
                "elapsed_seconds",
                "optimization_seconds",
                "process_peak_rss_bytes",
            )
        },
        "raw_evidence": str(root),
        "receipts": {
            name: digest(root / name)
            for name in (
                "config.json",
                "verification.json",
                "receipts.json",
                "plan/manifest.json",
                "study/summary.json",
                "study/source-files.json",
            )
        },
        "summarizer_sha256": digest(Path(__file__)),
        "limits": [
            "Exploratory teacher imitation, not playing strength or a correctness label.",
            "Three training blocks share one generation seed and the same development benchmark.",
            "Initialization seeds do not create independent datasets; "
            "all-block positivity is a decision rule, not a significance test.",
            "Trajectory cap is fixed, but mixtures change total source coverage.",
            "In-check development slice has only 35 positions; semantic slices are descriptive.",
            "Process RSS is a lifetime high-water mark including earlier fits and imports.",
            "Fixed 4000-input screen does not measure data scaling.",
        ],
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a fresh summary path.")
    result = summarize(args.evidence.resolve())
    write_json(args.output, result, indent=2)
    print(json.dumps({"advance": result["advance"], "complete_fits": result["complete_fits"]}))
