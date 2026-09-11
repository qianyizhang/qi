"""Summarize verified follow-ups and optionally plot the two scaling views."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aggregate(rows):
    keys = set(rows[0]["stats"])
    if any(set(r["stats"]) != keys for r in rows):
        raise ValueError("Slice inventory changed between matched initialization seeds.")
    slices = {}
    for key in sorted(keys):
        values = [r["stats"][key] for r in rows]
        # Semantic training tag counts vary by block; retain the full denominators.
        slices[key] = {
            "positions_per_fit": [v["positions"] for v in values],
            "mean_agreement": statistics.mean(v["agreement"] for v in values),
            "mean_cross_entropy": statistics.mean(v["cross_entropy"] for v in values),
        }
    return {
        "fits": len(rows),
        "mean_primary": statistics.mean(r["primary"] for r in rows),
        "primary_values": [r["primary"] for r in rows],
        "trial_names": [r["name"] for r in rows],
        "mean_fit_seconds": statistics.mean(r["seconds"] for r in rows),
        "fit_seconds_range": [min(r["seconds"] for r in rows), max(r["seconds"] for r in rows)],
        "peak_process_rss_bytes": max(r["peak_rss_bytes"] for r in rows),
        "slices": slices,
    }


def summarize(root, study):
    stage = root / study
    result = json.loads((stage / "verification.json").read_text())
    if result["status"] != "verified" or result["complete_fits"] != (18 if study == "semantic" else 30):
        raise ValueError("Only a complete independently verified matrix can be summarized.")
    for name, sha in json.loads((stage / "receipts.json").read_text()).items():
        if digest(root / name) != sha:
            raise ValueError("Verified evidence changed before summarization.")
    rows = result["trials"]
    if study == "semantic":
        groups = {case: aggregate([r for r in rows if r["case"] == case]) for case in ("natural", "enriched")}
    else:
        groups = {
            f"{case}-{n}-{u}": aggregate(
                [r for r in rows if r["case"] == case and r["size"] == n and r["updates"] == u]
            )
            for case in ("plausible", "mixed")
            for n in (1000, 4000, 16000)
            for u in sorted({200, 800000 // n})
        }
    return {
        "study": study,
        "execution": "complete",
        "complete_fits": result["complete_fits"],
        "development_inputs": result["development_inputs"],
        "sealed_test_scored": False,
        "assessment": result["assessment"],
        "groups": groups,
        "elapsed_seconds": result["elapsed_seconds"],
        "prior_stage_seconds": result["prior_stage_seconds"],
        "prior_attempt_seconds": result["prior_attempt_seconds"],
        "prior_attempts": result["prior_attempts"],
        "execution_dir": result["execution_dir"],
        "source": result["source"],
        "raw_evidence": str(stage.resolve()),
        "receipts": {
            str(p.relative_to(root)): digest(p)
            for p in (
                root / "config.json",
                stage / "verification.json",
                stage / "receipts.json",
                stage / "plan/manifest.json",
                stage / "preparation.json",
            )
        },
        "summarizer_sha256": digest(Path(__file__)),
        "limits": [
            "Exploratory teacher imitation on the reused 373-position development set; no playing-strength claim.",
            "One generation seed; initialization seeds are not independent training datasets.",
            "All-block or all-seed positivity is a decision rule, not a significance test.",
            "Fixed presentations change Adam update count and do not guarantee equal runtime or FLOPs.",
            "Semantic enrichment preserves source contributions; scaling changes source coverage and concentration.",
            "The six 4k/200-update scaling fits are shared between the two views.",
            "Process RSS is a lifetime high-water mark, not isolated per-fit memory.",
        ],
    }


def plot(result, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if result["study"] != "scaling":
        raise ValueError("The curve plot requires the scaling summary.")
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True, layout="constrained")
    sizes = [1000, 4000, 16000]
    labels = {"plausible": "100% plausible", "mixed": "80/10/10 mixture"}
    colors = {"plausible": "#52677D", "mixed": "#167A6E"}
    for ax, regime, title in zip(
        axes, ("passes", "presentations"), ("200 full-batch updates", "800,000 example presentations"), strict=True
    ):
        for case in ("plausible", "mixed"):
            points = result["assessment"]["curves"][regime][case]["points"]
            means = [100 * points[str(n)]["mean"] for n in sizes]
            ax.plot(sizes, means, marker="o", color=colors[case], label=labels[case], linewidth=2)
            for seed_index in range(3):
                ax.plot(
                    sizes,
                    [100 * points[str(n)]["seed_values"][seed_index] for n in sizes],
                    color=colors[case],
                    alpha=0.22,
                    linewidth=0.8,
                )
        ax.set_xscale("log", base=4)
        ax.set_xticks(sizes, ["1k", "4k", "16k"])
        ax.set_title(title, pad=12)
        ax.set_xlabel("Distinct training inputs")
        ax.grid(axis="y", alpha=0.2)
        ax.legend(frameon=False, fontsize=10)
    axes[0].set_ylabel("Balanced development agreement (%)")
    fig.suptitle("Generated-data scaling · fixed model and teacher", fontsize=16)
    fig.supxlabel(
        "Faint lines: initialization seeds, not confidence intervals. "
        "373 reused development inputs; sealed test unscored.",
        fontsize=9,
    )
    for suffix in ("png", "svg"):
        fig.savefig(output.with_suffix(f".{suffix}"), dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--study", choices=("semantic", "scaling"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--plot-summary", type=Path)
    parser.add_argument("--plot-output", type=Path)
    args = parser.parse_args()
    if args.plot_summary:
        plot(json.loads(args.plot_summary.read_text()), args.plot_output)
    else:
        if args.output.exists():
            raise ValueError("Choose a fresh summary path.")
        summary = summarize(args.root.resolve(), args.study)
        args.output.write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps({k: summary[k] for k in ("study", "complete_fits", "assessment")}))
