"""Bounded paired preparation comparison; keep raw outputs and timing-free content receipts."""

import argparse
import json
import platform
import shutil
import subprocess
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from qi.training_data.config import load_preparation, prepare_dataset
from qi.training_data.loading import load_dataset


def comparable_dataset(path: Path) -> dict:
    dataset = load_dataset(path).model_dump()
    for example in dataset["library"]["examples"]:
        analysis = example["analysis"]
        del analysis["elapsed_ms"]
        lines = []
        for line in analysis["search_info"]:
            tokens = iter(line.split())
            kept = []
            for token in tokens:
                if token in ("time", "nps"):
                    next(tokens, None)
                else:
                    kept.append(token)
            lines.append(" ".join(kept))
        analysis["search_info"] = lines
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = load_preparation(args.config)
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    source_paths = [Path(__file__), *sorted((root / "src/qi").rglob("*.py")), root / "pyproject.toml", root / "uv.lock"]
    source_hashes = {}
    for path in source_paths:
        relative = path.relative_to(root)
        target = args.output / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        source_hashes[str(relative)] = sha256(path.read_bytes()).hexdigest()
    evidence = {
        "schema_version": 1,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True),
        "source_sha256": source_hashes,
        "config": config.model_dump(),
        "comparison_exclusions": ["analysis.elapsed_ms", "analysis.search_info time/nps values"],
        "runs": [],
        "pairs": [],
        "complete": False,
    }
    summary = args.output / "comparison.json"

    def save() -> None:
        summary.write_text(json.dumps(evidence, indent=2) + "\n")

    save()
    for pair in range(3):
        payloads, times = {}, {}
        order = ("fresh", "persistent") if pair % 2 == 0 else ("persistent", "fresh")
        for mode in order:
            run_config = config.model_copy(update={"teacher_process": mode})
            output = args.output / f"pair-{pair}-{mode}"
            started = perf_counter()
            result = prepare_dataset(run_config, output)
            seconds = perf_counter() - started
            row = {"pair": pair, "mode": mode, "seconds": seconds, "result": result}
            evidence["runs"].append(row)
            save()
            if result["status"] != "complete":
                raise SystemExit(f"Incomplete preparation: {output}")
            dataset = load_dataset(output / "dataset.json")
            payloads[mode] = comparable_dataset(output / "dataset.json")
            times[mode] = seconds
            row.update(
                retained_examples=len(dataset.labels),
                retained_examples_per_second=len(dataset.labels) / seconds,
                semantic_sha256=sha256(json.dumps(payloads[mode], sort_keys=True).encode()).hexdigest(),
                files_sha256={p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob("*.json"))},
            )
            save()
            print(json.dumps({key: value for key, value in row.items() if key != "files_sha256"}), flush=True)
        matched = payloads["fresh"] == payloads["persistent"]
        evidence["pairs"].append(
            {"pair": pair, "content_equal": matched, "speedup": times["fresh"] / times["persistent"]}
        )
        save()
        if not matched:
            raise SystemExit("Content mismatch; raw outputs retained for diagnosis.")
    evidence["complete"] = True
    save()


if __name__ == "__main__":
    main()
