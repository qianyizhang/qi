"""Select an existing production policy on one frozen development set; no training."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import torch

from qi.learning.snapshot import SnapshotTensors
from qi.players.policy.runtime import load_checkpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("artifacts/learning"))
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a fresh selection output.")
    torch.set_num_threads(1)
    data = SnapshotTensors(args.cache)
    batches = list(data.batches("validation", 256))
    inputs = {row["input_hash"] for rows, _ in batches for row in rows}
    if len(inputs) != 373 or sum(len(rows) for rows, _ in batches) != 373:
        raise ValueError("Expected the frozen 373-position development set.")
    inventory, ranked, seen = [], [], {}
    for path in sorted(args.root.rglob("*.pt")):
        if "source" in path.parts:
            continue
        raw_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        record = {"path": str(path), "sha256": raw_digest}
        inventory.append(record)
        try:
            loaded = load_checkpoint(str(path.resolve()), raw_digest)
        except Exception as exc:
            record.update(status="incompatible", reason=str(exc))
            continue
        if set(loaded.metadata.train_inputs) & inputs:
            record.update(status="training_overlap", overlap=len(set(loaded.metadata.train_inputs) & inputs))
            load_checkpoint.cache_clear()
            continue
        state_hash = hashlib.sha256()
        for name, tensor in sorted(loaded.model.state_dict().items()):
            state_hash.update(json.dumps([name, str(tensor.dtype), list(tensor.shape)]).encode())
            state_hash.update(tensor.detach().numpy().tobytes())
        state_id = state_hash.hexdigest()
        record["state_sha256"] = state_id
        if state_id in seen:
            record.update(status="duplicate", duplicate_of=seen[state_id])
            load_checkpoint.cache_clear()
            continue
        seen[state_id] = str(path)
        cells = defaultdict(lambda: [0, 0])
        predictions, loss_sum = [], 0.0
        with torch.inference_mode():
            for rows, (features, mask, targets) in batches:
                logits = loaded.model(features).masked_fill(~mask, -torch.inf)
                if not torch.isfinite(logits[mask]).all():
                    raise ValueError("Nonfinite legal scores.")
                choices = logits.argmax(1)
                loss_sum += float(torch.nn.functional.cross_entropy(logits, targets, reduction="sum"))
                for row, choice, target in zip(rows, choices.tolist(), targets.tolist(), strict=True):
                    cell = row["bucket"]
                    cells[cell][0] += int(choice == target)
                    cells[cell][1] += 1
                    predictions.append([row["input_hash"], choice])
        if len(cells) != 6:
            raise ValueError("Expected six source/phase cells.")
        record.update(
            status="scored",
            seed=loaded.metadata.seed,
            updates=loaded.metadata.steps,
            macro_agreement=sum(c / n for c, n in cells.values()) / len(cells),
            micro_agreement=sum(c for c, _ in cells.values()) / 373,
            cross_entropy=loss_sum / 373,
            cells={k: {"correct": c, "positions": n} for k, (c, n) in cells.items()},
            predictions=predictions,
        )
        ranked.append(record)
        load_checkpoint.cache_clear()
    ranked.sort(key=lambda r: (-r["macro_agreement"], r["cross_entropy"], r["path"]))
    if not ranked:
        raise ValueError("No compatible checkpoint without development training overlap.")
    result = {
        "schema_version": 1,
        "produced_by": "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-14",
        "criterion": "Highest six-cell macro teacher agreement; tie: lower cross entropy, then path.",
        "scope": "Production policy-mlp-v1 checkpoints under artifacts/learning; prototype formats excluded.",
        "interpretation": "Exploratory candidate selection, not a playing-strength ranking.",
        "cache": str(args.cache),
        "cache_fingerprint": data.manifest["fingerprint"],
        "development_inputs": sorted(inputs),
        "counts": dict(Counter(r["status"] for r in inventory)),
        "selected": ranked[0],
        "ranking": [r["path"] for r in ranked],
        "inventory": inventory,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "counts": result["counts"],
                "top_five": [
                    {k: r[k] for k in ("path", "macro_agreement", "micro_agreement", "cross_entropy")}
                    for r in ranked[:5]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
