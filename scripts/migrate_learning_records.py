"""Project existing local learning evidence into additive, retrospective records.

This is a one-time bounded migration, not a generic artifact importer. Original
runs are never modified. --check verifies the projections against their sources.
"""

import argparse
import json
from pathlib import Path

from qi.learning.config import Recipe

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/experiments/learning"


def read(relative: str):
    return json.loads((ROOT / "artifacts/learning" / relative).read_text())


def emit(path: Path, value, check: bool) -> None:
    content = value if isinstance(value, bytes) else (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Projection differs: {path}")
    elif check:
        raise ValueError(f"Missing projection: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)


def curve(folder: str, name: str, check: bool) -> int:
    manifest, result = read(f"{folder}/manifest.json"), read(f"{folder}/summary.json")
    plan = manifest["plan"]
    dataset = f"artifacts/learning/{folder}/dataset.json"
    recipe = Recipe.model_validate(
        {
            "name": name,
            "derived_from": f"../../../artifacts/learning/{folder}/manifest.json",
            "data": {"dataset": f"../../../{dataset}", "subset_seed": plan["subset_seed"]},
            "optimizer": {"learning_rate": plan["learning_rate"]},
            "training": {"updates": plan["steps"]},
            "execution": {key: plan[key] for key in ("device", "threads", "fit_seconds", "total_seconds")},
            "cases": [{"name": f"size-{size}", "overrides": {"data": {"train_size": size}}} for size in plan["sizes"]],
            "seeds": plan["seeds"],
        }
    )
    emit(DEST / f"{name}.json", recipe.model_dump(), check)
    observations = []
    for trial in result["trials"]:
        report = trial["report"]
        meta = report["metadata"]
        assert meta["train_inputs"] == manifest["ordered_train_inputs"][: trial["size"]]
        assert meta["validation_inputs"] == manifest["validation_inputs"]
        assert meta["seed"] == trial["seed"] and meta["learning_rate"] == plan["learning_rate"]
        assert report["requested_steps"] == plan["steps"]
        assert meta["dataset_sha256"] == manifest["dataset_sha256"]
        observations.append(
            {
                "size": trial["size"],
                "seed": trial["seed"],
                "status": report["status"],
                "completed_updates": report["completed_steps"],
                "fit_seconds": report["optimization_budget_seconds"],
                "checkpoint": report["checkpoint"],
                "train_agreement": report["train"]["agreement"],
                "validation_agreement": report["validation"]["agreement"],
                "validation_cross_entropy": report["validation"]["cross_entropy"],
            }
        )
    emit(
        DEST / "history" / f"{name}.json",
        {
            "retrospective": True,
            "recipe": f"../{name}.json",
            "sources": [f"artifacts/learning/{folder}/{file}" for file in ("manifest.json", "summary.json")],
            "unknowns": [],
            "limitations": [
                "Recipe reconstructs declared settings; "
                "original implementation identity remains in the source manifest. Rerunning uses current code."
            ],
            "status": result["status"],
            "error": result.get("error"),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "planned_trials": result["planned_trials"],
            "dataset_sha256": manifest["dataset_sha256"],
            "source_sha256": manifest["source_sha256"],
            "observations": observations,
            "curve": result["curve"],
        },
        check,
    )
    return len(observations)


def sweep(folder: str, check: bool) -> int:
    manifest, results = read(f"{folder}/manifest.json"), read(f"{folder}/results.json")
    cases = []
    for config in manifest["configs"]:
        cases.append(
            {
                "name": config["id"],
                "model": {"hidden_width": config["width"], "encoding": config.get("encoding", "absolute")},
                "optimizer": {"learning_rate": config["lr"], "weight_decay": config["decay"]},
                "objective": {"legal_label_smoothing": config["smooth"]},
            }
        )
    emit(
        DEST / "history" / f"{folder}.json",
        {
            "retrospective": True,
            "runnable_by_current_config": False,
            "dataset_sha256": manifest["dataset_sha256"],
            "script_sha256": manifest["script_sha256"],
            "sources": [
                f"artifacts/learning/{folder}/{file}" for file in ("manifest.json", "results.json", "sweep.py")
            ],
            "unknowns": [
                "Full repository source identity was not recorded by the prototype; "
                "the script digest is retained in its original manifest."
            ],
            "limitations": [
                "50/200/800-update observations are checkpoints along each continuous fit, "
                "not independent training runs. Prototype architecture/loss variants remain historical."
            ],
            "shared_config": {
                "data": {
                    "dataset": "artifacts/learning/generalization-v1-data.json",
                    "train_size": 768,
                    "selection": "source-order",
                },
                "model": {"family": "one-hidden-layer-relu-mlp", "input_size": 1261, "output_size": 8100},
                "objective": {"name": "legal-masked-teacher-move"},
                "optimizer": {"name": "adam"},
                "training": {"batching": "full", "updates": 800, "precision": "float32"},
                "evaluation": {
                    "split": "tuning (original dataset validation)",
                    "metrics": ["agreement", "cross_entropy"],
                    "checkpoint_updates": manifest["checkpoints"],
                },
                "execution": {"device": manifest["device"], "threads": 1, "total_seconds": 600, "fit_seconds": None},
            },
            "cases": cases,
            "seeds": manifest["seeds"],
            "observations": results,
        },
        check,
    )
    return len(results)


def migrate(check: bool) -> None:
    counts = {}
    for folder, name in [
        ("generalization-v1", "generalization-v1"),
        ("data-scaling-v1/curve", "data-scaling-interrupted"),
        ("data-scaling-v1/curve-cached", "data-scaling-v1"),
    ]:
        counts[name] = curve(folder, name, check)
    for folder in ("tuning-v1", "tuning-perspective-v1"):
        counts[folder] = sweep(folder, check)
    smoke = []
    for name in ("diagnostic-v1", "policy-v1"):
        report = read(f"{name}-report.json")
        meta = report["metadata"]
        smoke.append(
            {
                "name": name,
                "config": {
                    "data": {
                        "dataset": "artifacts/learning/smoke-v1.json",
                        "selection": "source-order",
                        "train_size": len(meta["train_inputs"]),
                    },
                    "model": {"architecture": meta["architecture"], "encoding": meta["encoding"]},
                    "objective": {"name": meta["objective"]},
                    "optimizer": {"name": "adam", "learning_rate": meta["learning_rate"]},
                    "training": {
                        "batching": "full",
                        "updates": report["requested_steps"],
                        "seed": meta["seed"],
                        "precision": "float32",
                    },
                    "evaluation": {"split": "validation", "metrics": ["agreement"]},
                    "execution": {
                        "device": "cpu",
                        "threads": 1,
                        "fit_seconds": report["optimization_budget_seconds"],
                        "total_seconds": None,
                    },
                },
                "completed_updates": report["completed_steps"],
                "train": report["train"],
                "validation": report["validation"],
            }
        )
    emit(
        DEST / "history/smoke-v1.json",
        {
            "retrospective": True,
            "runnable_by_current_config": False,
            "sources": [
                "artifacts/learning/diagnostic-v1-report.json",
                "artifacts/learning/policy-v1-report.json",
                "git:58b64de:src/qi/learning/train.py",
            ],
            "unknowns": ["Original reports did not record a complete source/environment identity."],
            "limitations": [
                "CPU/full-batch/float32/one-thread settings recovered from the original trainer source. "
                "Original evaluation did not report cross-entropy. No outer deadline existed."
            ],
            "runs": smoke,
        },
        check,
    )
    final = read("tuning-v1/final-test-report.json")
    final.pop("retained_test_inputs")
    emit(
        DEST / "history/tuning-final-test.json",
        {
            "retrospective": True,
            "sources": [
                "artifacts/learning/tuning-v1/selection.json",
                "artifacts/learning/tuning-v1/final-test-report.json",
            ],
            "unknowns": [],
            "limitations": [
                "Evaluation of preselected existing prototype checkpoints; no new training. "
                "Exact test inputs remain in the local source report."
            ],
            "selection": read("tuning-v1/selection.json"),
            "result": final,
        },
        check,
    )
    scripts = {
        "generalization-v1": ["verify.py"],
        "tuning-v1": ["sweep.py", "final_test.py"],
        "tuning-perspective-v1": ["sweep.py", "encoding.py"],
        "data-scaling-v1": ["generate.py", "prepare.py", "verify.py", "plot.py"],
        "device-benchmark": ["benchmark.py"],
        "framework-benchmark": [
            "compare.py",
            "run_all.py",
            "run_full_precision.py",
            "verify_math.py",
            "verify_exports.py",
        ],
    }
    for folder, files in scripts.items():
        for file in files:
            emit(
                DEST / "legacy-scripts" / folder / file,
                (ROOT / "artifacts/learning" / folder / file).read_bytes(),
                check,
            )
    for folder in ("device-benchmark", "framework-benchmark"):
        emit(
            DEST / "history" / f"{folder}.json",
            {
                "retrospective": True,
                "runnable_by_current_config": False,
                "sources": [f"artifacts/learning/{folder}/summary.md"],
                "limitations": [
                    "Specialized platform benchmark; preserved in its original format, not a training recipe."
                ],
                "summary": (ROOT / "artifacts/learning" / folder / "summary.md").read_text(),
            },
            check,
        )
    print(
        json.dumps(
            {"checked" if check else "migrated": counts, "smoke_runs": len(smoke), "original_runs_modified": False}
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    migrate(parser.parse_args().check)
