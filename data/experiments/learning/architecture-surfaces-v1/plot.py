"""Standalone descriptive study figure; reads retained analysis and fit receipts only."""

import argparse
import hashlib
import json
import os
import platform
import statistics
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/qi-architecture-mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CASES = (
    "absolute_mlp64",
    "absolute_mlp128",
    "canonical_mlp64",
    "canonical_pair64",
    "canonical_conv32",
)
LABELS = ("Abs MLP64", "Abs MLP128", "Can MLP64", "Can Pair64", "Can CNN32")
COLORS = ("#346A85", "#CC8C37", "#427C60", "#8863A0", "#BA5C63")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compact_count(value):
    return f"{value / 1e6:.2f}M" if value >= 1_000_000 else f"{value / 1000:.1f}k"


def observations_for(analysis, case, update):
    return sorted(
        (row for row in analysis["observations"] if row["case"] == case and row["update"] == update),
        key=lambda row: row["seed"],
    )


def jitter(n):
    return np.linspace(-0.105, 0.105, n) if n > 1 else np.zeros(n)


def mean(values):
    return statistics.mean(values)


def style_axis(ax, title, labels=LABELS, *, percentage=False):
    ax.set_title(title, loc="left", fontsize=12, fontweight="semibold", pad=13)
    ax.set_yticks(range(len(CASES)), labels)
    ax.set_ylim(len(CASES) - 0.45, -0.65)
    ax.tick_params(axis="both", length=0, labelsize=10, pad=7)
    ax.grid(axis="x", color="#E1E6E9", linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    if percentage:
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100])


def paired_panel(ax, analysis, update, value_a, value_b, marker_a, marker_b, *, scale=1):
    for y, case in enumerate(CASES):
        rows = observations_for(analysis, case, update)
        if not rows:
            ax.text(0.02, y, "No retained observation", transform=ax.get_yaxis_transform(), color="#66757F")
            continue
        first = [scale * value_a(row) for row in rows]
        second = [scale * value_b(row) for row in rows]
        for a, b, offset in zip(first, second, jitter(len(rows)), strict=True):
            ax.plot([a, b], [y + offset, y + offset], color=COLORS[y], alpha=0.18, linewidth=1)
            ax.scatter(a, y + offset, s=19, marker=marker_a, facecolors="white", edgecolors=COLORS[y], alpha=0.5)
            ax.scatter(b, y + offset, s=19, marker=marker_b, color=COLORS[y], alpha=0.5)
        ax.plot([mean(first), mean(second)], [y, y], color=COLORS[y], linewidth=2)
        ax.scatter(
            mean(first), y, s=62, marker=marker_a, facecolors="white", edgecolors=COLORS[y], linewidths=1.7, zorder=4
        )
        ax.scatter(
            mean(second), y, s=62, marker=marker_b, color=COLORS[y], edgecolors="white", linewidths=0.6, zorder=5
        )


def legend(ax, first, second, marker_a="o", marker_b="o"):
    handles = [
        plt.Line2D(
            [], [], marker=marker_a, markerfacecolor="white", markeredgecolor="#475863", linestyle="none", label=first
        ),
        plt.Line2D([], [], marker=marker_b, color="#475863", linestyle="none", label=second),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=8.5, frameon=False, handletextpad=0.4, ncol=2)


def plot(analysis_path, study, prefix):
    outputs = {
        name: Path(f"{prefix}.{suffix}") for name, suffix in (("png", "png"), ("svg", "svg"), ("env", "plot-env.json"))
    }
    if any(path.exists() for path in outputs.values()):
        raise ValueError("Choose a fresh figure prefix; previous figures and receipts are preserved.")
    analysis_raw = analysis_path.read_bytes()
    analysis = json.loads(analysis_raw)
    report_path = study / "report.json"
    report_raw = report_path.read_bytes()
    report = json.loads(report_raw)
    if analysis["version"] != "architecture-surfaces-analysis-v1" or not analysis["observations"]:
        raise ValueError("Expected nonempty architecture-surfaces analysis.")
    keys = [(row["case"], row["seed"], row["update"]) for row in analysis["observations"]]
    if len(keys) != len(set(keys)) or any(case not in CASES for case, _, _ in keys):
        raise ValueError("Unknown model or duplicate observation.")
    # Check the plotted seed means against the separately retained aggregate projection.
    for aggregate in analysis["aggregates"]:
        rows = observations_for(analysis, aggregate["case"], aggregate["update"])
        if not rows or not np.isclose(
            mean(r["macro_agreement"] for r in rows), aggregate["macro_agreement"], atol=1e-12
        ):
            raise ValueError("Aggregate macro agreement differs from seed observations.")
    updates = sorted({row["update"] for row in analysis["observations"]})
    earliest, final = updates[0], updates[-1]
    seed_counts = {len(observations_for(analysis, case, final)) for case in CASES}
    seed_label = str(next(iter(seed_counts))) if len(seed_counts) == 1 else "/".join(map(str, sorted(seed_counts)))
    sample_sizes = {row["slices"]["all"]["positions"] for row in analysis["observations"]}
    if len(sample_sizes) != 1:
        raise ValueError("Development denominators differ across plotted observations.")
    dev_n = next(iter(sample_sizes))
    costs = {}
    for case in CASES:
        fits = [fit for fit in report["fits"] if fit["case"] == case]
        if not fits:
            continue
        counts = {fit["model"]["parameters"] for fit in fits}
        if len(counts) != 1:
            raise ValueError("Parameter counts differ within a case.")
        costs[case] = {
            "parameters": next(iter(counts)),
            "mean_fit_seconds": mean(fit["elapsed_seconds"] for fit in fits),
            "fit_statuses": [fit["status"] for fit in fits],
            "completed_updates": [fit["completed_updates"] for fit in fits],
        }
    plt.rcParams.update(
        {"font.family": "DejaVu Sans", "svg.fonttype": "none", "axes.labelcolor": "#354650", "text.color": "#253945"}
    )
    fig, axes = plt.subplots(2, 2, figsize=(14, 9.5))
    fig.subplots_adjust(left=0.115, right=0.965, top=0.855, bottom=0.185, hspace=0.5, wspace=0.42)
    fig.patch.set_facecolor("white")
    title = "Architecture changes expose different failure modes"
    if report["status"] != "complete":
        title = "INTERIM — retained observations from an incomplete study"
    if final < 50:
        title = "SMOKE FIGURE — execution check; no architecture conclusion"
    fig.suptitle(title, x=0.04, y=0.965, ha="left", fontsize=19, fontweight="semibold")
    fig.text(
        0.04,
        0.918,
        f"Reused development: {dev_n} inputs · {seed_label} initialization seeds on one dataset · "
        "small marks = individual seeds; large marks = their mean",
        fontsize=10.2,
        color="#586C78",
    )

    ax = axes[0, 0]
    style_axis(ax, f"A  Development macro agreement: updates {earliest} → {final}", percentage=True)
    for y, case in enumerate(CASES):
        early = observations_for(analysis, case, earliest)
        late = observations_for(analysis, case, final)
        if not late:
            continue
        for rows, offset, filled in ((early, -0.09, False), (late, 0.09, True)):
            xs = [100 * row["macro_agreement"] for row in rows]
            if not xs:
                continue
            ax.scatter(
                xs,
                y + offset + jitter(len(xs)) * 0.6,
                s=20,
                facecolors=COLORS[y] if filled else "white",
                edgecolors=COLORS[y],
                alpha=0.5,
            )
            ax.scatter(
                mean(xs),
                y + offset,
                s=65,
                facecolors=COLORS[y] if filled else "white",
                edgecolors=COLORS[y],
                linewidths=1.6,
                zorder=4,
            )
        if early:
            ax.plot(
                [
                    100 * mean(row["macro_agreement"] for row in early),
                    100 * mean(row["macro_agreement"] for row in late),
                ],
                [y - 0.09, y + 0.09],
                color=COLORS[y],
                linewidth=1.7,
            )
    legend(ax, f"Update {earliest}", f"Update {final}")
    ax.set_xlabel("Agreement (%) · each of six development cells weighted equally", fontsize=9.2)

    ax = axes[0, 1]
    style_axis(ax, f"B  Training fit versus development: update {final}", percentage=True)
    paired_panel(
        ax,
        analysis,
        final,
        lambda r: r["train"]["agreement"],
        lambda r: r["slices"]["all"]["agreement"],
        "s",
        "o",
        scale=100,
    )
    legend(ax, "Train", "Development", "s", "o")
    ax.set_xlabel("Agreement (%) · micro means on each split's own positions", fontsize=9.2)

    ax = axes[1, 0]
    style_axis(ax, f"C  Fixed confidence rescaling: update {final}")
    paired_panel(
        ax,
        analysis,
        final,
        lambda r: r["slices"]["all"]["cross_entropy"],
        lambda r: r["slices"]["all"]["cross_entropy_temperature2"],
        "o",
        "^",
    )
    ax.set_xlim(left=0)
    legend(ax, "T = 1", "T = 2", "o", "^")
    ax.set_xlabel("Development cross-entropy (nats) · identical argmax moves", fontsize=9.2)

    ax = axes[1, 1]
    labels = []
    unseen_denominators = {}
    for y, case in enumerate(CASES):
        rows = observations_for(analysis, case, final)
        values = [row["slices"].get("coordinate_unseen") for row in rows]
        coordinate = "canonical" if case.startswith("canonical_") else "absolute"
        denominators = {value["positions"] for value in values if value}
        if len(denominators) > 1:
            raise ValueError("Unseen-action subset changed across seeds.")
        n = next(iter(denominators)) if denominators else 0
        unseen_denominators[case] = {"positions_per_seed": n, "coordinate": coordinate}
        labels.append(f"{LABELS[y]}\nn = {n}; {coordinate}")
        xs = [100 * value["agreement"] for value in values if value and value["agreement"] is not None]
        if xs:
            ax.scatter(xs, y + jitter(len(xs)), s=21, color=COLORS[y], alpha=0.5)
            ax.scatter(mean(xs), y, s=65, color=COLORS[y], edgecolors="white", linewidths=0.6, zorder=4)
    style_axis(ax, f"D  Unseen target actions: update {final}", labels, percentage=True)
    ax.tick_params(axis="y", labelsize=8.8)
    ax.set_xlabel("Agreement (%) · absolute and canonical subsets differ", fontsize=9.2)

    cost_parts = []
    for case, label in zip(CASES, LABELS, strict=True):
        if case in costs:
            cost = costs[case]
            cost_parts.append(f"{label}: {compact_count(cost['parameters'])} / {cost['mean_fit_seconds']:.0f}s")
    fig.text(
        0.04, 0.103, "Parameters / mean fit wall time:  " + "  ·  ".join(cost_parts), fontsize=8.6, color="#586C78"
    )
    fig.text(
        0.04,
        0.06,
        "Seed variation is not uncertainty across datasets. "
        "Training and development contain different position mixtures.\n"
        "Unseen means absent as a training target in that model's coordinates; "
        "these conditional subsets cannot establish a general ranking.",
        fontsize=9,
        color="#586C78",
        linespacing=1.65,
    )
    # Keep complete point symbols visible at the meaningful 0% and 100% axis endpoints.
    for panel in axes.flat:
        for points in panel.collections:
            points.set_clip_on(False)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outputs["png"], dpi=180, facecolor="white", metadata={"Software": "matplotlib"})
    fig.savefig(outputs["svg"], facecolor="white", metadata={"Creator": "matplotlib"})
    plt.close(fig)
    environment = {
        "created": datetime.now(timezone.utc).isoformat(),
        "analysis": {"path": str(analysis_path.resolve()), "sha256": hashlib.sha256(analysis_raw).hexdigest()},
        "study_report": {
            "path": str(report_path.resolve()),
            "sha256": hashlib.sha256(report_raw).hexdigest(),
            "status": report["status"],
        },
        "script": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__))},
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "updates_shown": [earliest, final],
        "development_positions": dev_n,
        "final_seed_counts": sorted(seed_counts),
        "costs": costs,
        "unseen_denominators": unseen_denominators,
        "figures": {
            kind: {"path": str(outputs[kind].resolve()), "sha256": digest(outputs[kind])} for kind in ("png", "svg")
        },
    }
    with outputs["env"].open("x") as stream:
        json.dump(environment, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return {kind: str(path.resolve()) for kind, path in outputs.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Fresh output prefix for PNG, SVG, and receipt.")
    args = parser.parse_args()
    print(json.dumps(plot(args.analysis, args.study, args.output)), flush=True)


if __name__ == "__main__":
    main()
