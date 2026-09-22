"""Create disposable browser evidence before starting the isolated test server."""

import base64
import hashlib
import json
import os
import shutil
from pathlib import Path

from qi_game.contracts import Snapshot

from qi.benchmark.models import BenchmarkSeries, BenchmarkSpec, Book, BookStart, Entrant
from qi.benchmark.runner import run_benchmark
from qi.benchmark.summary import summarize_benchmark
from qi.experiments.catalog import ExperimentEntry
from qi.experiments.inspect import inspect_decision
from qi.experiments.model import Plan
from qi.experiments.report import report
from qi.experiments.research import present
from qi.experiments.runner import run as run_experiment
from qi.players import PlayerConfig
from qi.test_collection_view import build_review_collection

ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / ".test-artifacts"


def reset_artifacts(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()


def prepare_experiment_runs(root: Path) -> None:
    plan = Plan(
        name="Browser report fixture",
        question="</script><script>alert('bad')</script>",
        corpus={
            "id": "fixture",
            "provenance": "Hermetic browser fixture",
            "openings": [
                {
                    "id": "initial",
                    "description": "Initial board",
                    "snapshot": Snapshot(),
                }
            ],
        },
        players=["alphabeta-enhanced", "mcts"],
        budgets=[64],
        pairs=[("alphabeta-enhanced", "mcts")],
        game_openings=["initial"],
    )
    complete_run = root / "runs" / "complete"
    run_experiment(plan, complete_run)
    inspect_decision(complete_run, "unit-00000", 0, complete_run / "traces/alpha.json")
    inspect_decision(complete_run, "unit-00001", 0, complete_run / "traces/mcts.json")
    inspect_decision(
        complete_run,
        "unit-00000",
        0,
        complete_run / "traces/limited.json",
        limit=3,
    )
    (complete_run / "narrative.md").write_text(
        "# Observations\n\n"
        "Authored interpretation beside measured evidence.\n\n"
        "[First unit](units/unit-00000.json)\n\n"
        "<script>alert('narrative')</script>",
        encoding="utf-8",
    )
    report(complete_run, complete_run / "report.html")
    run_experiment(
        plan.model_copy(update={"name": "Incomplete fixture"}),
        root / "runs" / "incomplete",
        seconds=0.001,
    )

    for name, manifest in (("unsupported", {"kind": "learning-v9"}), ("invalid", {})):
        target = root / "runs" / name
        target.mkdir()
        content = json.dumps(manifest) if name == "unsupported" else "{"
        (target / "manifest.json").write_text(content, encoding="utf-8")


def prepare_catalog(root: Path) -> None:
    """Create catalog fixtures without a run manifest or raw results."""

    owner = root / "records/reports/catalog-fixture.md"
    owner.parent.mkdir(parents=True)
    fixture = ExperimentEntry(
        id="teacher-budget-fixture",
        title="Teacher budget recall fixture",
        question="Does a stronger teacher agree more with a 1M reference?",
        kind="teacher",
        topics=["teacher quality", "stronger teacher", "1M reference"],
        execution="complete",
        conclusion="inconclusive",
        finding="24/36 agreement; no student training.",
        conditions="36 correlated positions.",
        limitations="Reference is an estimate, not ground truth.",
        decision="Keep defaults.",
        revisit="Independent source games and student outcomes.",
        evidence=[
            {"path": "artifacts/missing.json", "role": "results"},
            {"path": "data/compact.json", "role": "results"},
        ],
        novelty="Historical registration, not a new run.",
    )
    owner.write_text(
        "# Historical teacher pilot\n\n```experiment\n" + fixture.model_dump_json() + "\n```\n",
        encoding="utf-8",
    )
    (root / "data").mkdir()
    (root / "data/compact.json").write_text(
        '{"agreement":24,"positions":36}',
        encoding="utf-8",
    )


def prepare_collection(root: Path) -> None:
    """Create a read-only review fixture without a teacher or training process."""

    build_review_collection(root / "collections/review.sqlite")


def prepare_benchmarks(root: Path) -> None:
    """Run real lightweight players against an isolated pool registry."""

    os.environ["QI_BENCHMARK_STATE"] = str(root / "benchmark-state")
    book = Book(
        id="browser-fixture",
        use="smoke",
        provenance="Hermetic browser benchmark",
        selection="One fixed start",
        starts=[
            BookStart(
                id="horse",
                family="fixture-horse",
                source_game="fixture-game",
                source_url="test:browser",
                description="Horse development",
                snapshot=Snapshot(moves=["b0c2", "b9c7"]),
            )
        ],
    )
    entrants = [
        Entrant(
            id="baseline",
            label="Baseline random",
            config=PlayerConfig("random", seed=7),
        ),
        Entrant(
            id="candidate",
            label="Candidate random",
            config=PlayerConfig("random", seed=17),
        ),
    ]
    specification = BenchmarkSpec(
        series=BenchmarkSeries(
            id="browser-benchmark",
            label="Benchmark browser fixture",
            book=book,
            references=entrants,
            anchor="baseline",
        ),
        starts=["horse"],
    )
    complete_run = root / "benchmarks/complete"
    run_benchmark(specification, complete_run)
    summarize_benchmark(complete_run, persist=True)

    locked_specification = specification.model_copy(deep=True)
    locked_specification.series.label = "Locked benchmark fixture"
    locked_specification.series.book.use = "locked-test"
    run_benchmark(locked_specification, root / "benchmarks/locked")


def prepare_research(root: Path) -> None:
    """Render authored research from tiny, pinned fixture evidence."""

    research = root / "research"
    research.mkdir()
    research_owner = research / "report.md"
    research_owner.write_text(
        "---\ndescription: A synthetic study for offline reading checks.\n"
        "last_update: 2026-09-12\nreport_outcome: inconclusive\n---\n\n"
        "# Research presentation fixture\n\n"
        "The original preamble stays available.\n\n"
        "## Observations and limits\n\n"
        "A controlled comparison does not establish playing strength.\n\n"
        "| Observation | Limitation |\n| --- | --- |\n"
        "| Shared inputs | Correlated outcomes |\n\n"
        "[Recorded values](results.json), [Earlier interpretation](previous.md), "
        "and [Missing source](missing.json).\n\n"
        "![Fixture diagram](diagram.png)\n\n"
        "![External illustration](https://example.invalid/should-not-load.png)\n\n"
        "<script>alert('narrative should be inert')</script>\n\n"
        "## Next focus\n\nSeparate coverage from representation under stable optimization.\n",
        encoding="utf-8",
    )
    (research / "previous.md").write_text(
        "# Earlier interpretation\n\nA retained, inconclusive fixture finding.\n\n"
        "| Evidence | Scope |\n| --- | --- |\n| One pool | Exploratory |\n",
        encoding="utf-8",
    )
    (research / "diagram.png").write_bytes(
        base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")
    )

    research_results = research / "results.json"
    research_results.write_text(
        json.dumps(
            {
                "fits": 6,
                "rows": [
                    {
                        "case": case,
                        "update": update,
                        "agreement": agreement,
                        "loss": loss,
                        "n": count,
                    }
                    for update, observations in (
                        (50, (("b", 0.25, 2.5, 12), ("a", 0, 1.5, 12), ("c", None, None, 0))),
                        (200, (("b", 0.5, 3.5, 12), ("a", 0.125, 2.0, 12), ("c", None, None, 0))),
                    )
                    for case, agreement, loss, count in observations
                ],
            }
        ),
        encoding="utf-8",
    )
    research_view = research / "view.json"
    research_view.write_text(
        json.dumps(
            {
                "version": "research-view-v1",
                "summary": "Investigate coverage and optimization together.",
                "section_notes": {
                    "observations-and-limits": ("Presentation note: original interpretation retained for review.")
                },
                "data_sources": {
                    "findings": {
                        "path": "research/results.json",
                        "sha256": hashlib.sha256(research_results.read_bytes()).hexdigest(),
                    }
                },
                "stats": [
                    {
                        "label": "Recorded fits",
                        "value": {"source": "findings", "pointer": "/fits"},
                        "note": "Synthetic fixture observations",
                    }
                ],
                "takeaways": [
                    {
                        "title": "Check the denominator",
                        "body": "Unknown is different from observed zero.",
                    }
                ],
                "explorers": [
                    {
                        "id": "recorded-models",
                        "title": "Recorded model contrasts",
                        "description": "Synthetic fixed-order observations.",
                        "caveat": "Imitation agreement does not establish playing strength.",
                        "source": "findings",
                        "rows_pointer": "/rows",
                        "label_pointer": "/case",
                        "labels": {"a": "Model A", "b": "Model B", "c": "Model C"},
                        "facets": [
                            {
                                "key": "update",
                                "label": "Training updates",
                                "pointer": "/update",
                                "initial": 200,
                            }
                        ],
                        "metrics": [
                            {
                                "key": "agreement",
                                "label": "Target agreement",
                                "pointer": "/agreement",
                                "format": "percent",
                                "note": "Same inspected target pool; unknown remains unknown.",
                                "denominator_pointer": "/n",
                            },
                            {
                                "key": "loss",
                                "label": "Cross-entropy",
                                "pointer": "/loss",
                                "format": "decimal",
                                "unit": "nats",
                                "precision": 3,
                                "note": "Micro mean; lower values need their stated conditions.",
                                "denominator_pointer": "/n",
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    present(research_owner, research / "enhanced.html", research_view, root=root)
    present(research_owner, research / "plain.html", root=root)


def main() -> None:
    reset_artifacts(ARTIFACT_ROOT)
    prepare_experiment_runs(ARTIFACT_ROOT)
    prepare_catalog(ARTIFACT_ROOT)
    prepare_collection(ARTIFACT_ROOT)
    prepare_benchmarks(ARTIFACT_ROOT)
    prepare_research(ARTIFACT_ROOT)


if __name__ == "__main__":
    main()
