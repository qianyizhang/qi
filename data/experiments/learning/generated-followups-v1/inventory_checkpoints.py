"""Inventory completed generated-data fits without rescoring or changing them."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[4]
MIX = ROOT / "artifacts/learning/generated-source-mixing-v1-run3"
FOLLOWUPS = ROOT / "artifacts/learning/generated-followups-v1"
STUDIES = {
    "source-mixing": (MIX / "study", 36),
    "semantic-enrichment": (FOLLOWUPS / "semantic/study-retry-1", 18),
    "data-scaling": (FOLLOWUPS / "scaling/study", 30),
}


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


def inventory():
    expected = {}
    for study, (directory, count) in STUDIES.items():
        summary = read(directory / "summary.json")
        if summary["status"] != "complete" or len(summary["trials"]) != count:
            raise ValueError(f"Incomplete matrix: {study}")
        for trial in summary["trials"]:
            expected[directory / trial["name"] / "policy.pt"] = (study, "comparative")
    expected[MIX / "pilot/policy.pt"] = ("source-mixing", "resource-pilot")
    expected[FOLLOWUPS / "scaling/study/resource-pilot/policy.pt"] = ("data-scaling", "resource-pilot")
    for seed in (7, 17, 27):
        path = FOLLOWUPS / f"semantic/study/block-0-natural-updates-200-seed-{seed}/policy.pt"
        expected[path] = ("semantic-enrichment", "retained-earlier-control")
    found = set(MIX.rglob("policy.pt")) | set(FOLLOWUPS.rglob("policy.pt"))
    if len(expected) != 89 or found != set(expected):
        raise ValueError("Retained checkpoint files differ from the expected 89-fit inventory.")
    sealed = {row["input"] for row in read(MIX / "plan/sealed-test-inputs.json")}
    entries, groups, development_inputs = [], defaultdict(list), None
    for path, (study, role) in sorted(expected.items()):
        report, config = read(path.parent / "report.json"), read(path.parent / "config.json")
        sha = digest(path)
        if report["status"] != "complete" or report["checkpoint_sha256"] != sha:
            raise ValueError(f"Incomplete fit or changed checkpoint: {path}")
        if report["completed_updates"] != config["training"]["updates"]:
            raise ValueError(f"Update count differs from config: {path}")
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        if set(checkpoint) != {"metadata", "state_dict"}:
            raise ValueError(f"Unexpected checkpoint contents: {path}")
        state_sha = hashlib.sha256()
        for name, tensor in sorted(checkpoint["state_dict"].items()):
            header = json.dumps([name, str(tensor.dtype), list(tensor.shape)], separators=(",", ":"))
            state_sha.update(header.encode() + b"\n")
            state_sha.update(tensor.detach().cpu().contiguous().numpy().tobytes())
        predictions = path.parent / "predictions.jsonl"
        rows = [json.loads(line) for line in predictions.read_text().splitlines()]
        if {row["input_hash"] for row in rows} & sealed:
            raise ValueError(f"Sealed input was scored: {path}")
        development = sorted((row["input_hash"], row["prediction"]) for row in rows if row["split"] == "validation")
        inputs = [key for key, _ in development]
        if len(inputs) != 373 or len(set(inputs)) != 373:
            raise ValueError(f"Development denominator differs: {path}")
        if development_inputs is None:
            development_inputs = inputs
        elif inputs != development_inputs:
            raise ValueError(f"Development inputs differ: {path}")
        entry = {
            "directory": str(path.parent.relative_to(ROOT)),
            "study": study,
            "role": role,
            "seed": config["training"]["seed"],
            "updates": report["completed_updates"],
            "checkpoint_bytes": path.stat().st_size,
            "checkpoint_sha256": sha,
            "state_dict_sha256": state_sha.hexdigest(),
            "config_sha256": digest(path.parent / "config.json"),
            "report_sha256": digest(path.parent / "report.json"),
            "predictions_sha256": digest(predictions),
            "development_choices_sha256": canonical_sha(development),
        }
        entries.append(entry)
        if role == "comparative":
            groups[entry["state_dict_sha256"]].append(entry["directory"])
    return {
        "status": "verified",
        "scope": "Final checkpoints of AB-LEARN-012, AB-LEARN-013 and AB-LEARN-014 only.",
        "checkpoint_contents": ["metadata", "state_dict"],
        "optimizer_state_saved": False,
        "intermediate_update_checkpoints_saved": False,
        "storage": "Local ignored artifacts; this inventory is not a backup of weights.",
        "counts_by_role": dict(Counter(row["role"] for row in entries)),
        "counts_by_study": dict(Counter(row["study"] for row in entries)),
        "checkpoint_bytes": sum(row["checkpoint_bytes"] for row in entries),
        "distinct_comparative_state_dicts": len(groups),
        "distinct_comparative_development_choice_vectors": len(
            {row["development_choices_sha256"] for row in entries if row["role"] == "comparative"}
        ),
        "development_inputs": len(development_inputs),
        "sealed_inputs": len(sealed),
        "sealed_inputs_scored": 0,
        "state_digest_method": (
            "Sorted tensor names; compact JSON [name,dtype,shape] plus LF, "
            "then contiguous native NumPy bytes; audited on little-endian macOS arm64."
        ),
        "comparative_duplicate_state_groups": [paths for paths in groups.values() if len(paths) > 1],
        "inventory_source_sha256": digest(Path(__file__)),
        "entries": entries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve the existing inventory; choose a fresh output path.")
    result = inventory()
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in {"entries", "comparative_duplicate_state_groups"}
            }
        )
    )


if __name__ == "__main__":
    main()
