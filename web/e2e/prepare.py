"""Create disposable browser evidence before starting the isolated test server."""

import json
import shutil
from pathlib import Path

from qi.experiments.inspect import inspect_decision
from qi.experiments.model import Plan
from qi.experiments.report import report
from qi.experiments.runner import run
from qi.protocol import Snapshot

root = Path(__file__).resolve().parents[1] / ".test-artifacts"
if root.exists():
    shutil.rmtree(root)
root.mkdir()
p = Plan(name="Browser report fixture", question="</script><script>alert('bad')</script>",
         corpus={"id":"fixture", "provenance":"Hermetic browser fixture", "openings":[{"id":"initial", "description":"Initial board", "snapshot":Snapshot()}]},
         players=["alphabeta-enhanced", "mcts"], budgets=[64], pairs=[("alphabeta-enhanced", "mcts")], game_openings=["initial"])
d = root / "runs" / "complete"
run(p, d)
inspect_decision(d, "unit-00000", 0, d / "traces/alpha.json")
inspect_decision(d, "unit-00001", 0, d / "traces/mcts.json")
inspect_decision(d, "unit-00000", 0, d / "traces/limited.json", limit=3)
(d / "narrative.md").write_text("# Observations\n\nAuthored interpretation beside measured evidence.\n\n[First unit](units/unit-00000.json)\n\n<script>alert('narrative')</script>")
report(d, d / "report.html")
run(p.model_copy(update={"name":"Incomplete fixture"}), root / "runs" / "incomplete", seconds=0.001)
for name, value in (("unsupported", {"kind":"learning-v9"}), ("invalid", {})):
    target = root / "runs" / name
    target.mkdir()
    (target / "manifest.json").write_text(json.dumps(value) if name == "unsupported" else "{")

# Catalog fixtures intentionally have no run manifest or raw results.
from qi.experiments.catalog import ExperimentEntry
owner = root / "records/reports/catalog-fixture.md"
owner.parent.mkdir(parents=True)
fixture = ExperimentEntry(
    id="teacher-budget-fixture", title="Teacher budget recall fixture",
    question="Does a stronger teacher agree more with a 1M reference?",
    kind="teacher", topics=["teacher quality", "stronger teacher", "1M reference"],
    execution="complete", conclusion="inconclusive",
    finding="24/36 agreement; no student training.", conditions="36 correlated positions.",
    limitations="Reference is an estimate, not ground truth.", decision="Keep defaults.",
    revisit="Independent source games and student outcomes.",
    evidence=[{"path":"artifacts/missing.json", "role":"results"},
              {"path":"data/compact.json", "role":"results"}],
    novelty="Historical registration, not a new run.",
)
owner.write_text("# Historical teacher pilot\n\n```experiment\n" + fixture.model_dump_json() + "\n```\n")
(root / "data").mkdir()
(root / "data/compact.json").write_text('{"agreement":24,"positions":36}')

# Read-only collection review fixtures, without a teacher process or training.
from qi.test_collection_view import build_review_collection
build_review_collection(root / "collections/review.sqlite")

# Paired benchmark evidence uses real lightweight players and an isolated pool registry.
import os
from qi.benchmark.models import BenchmarkSpec, BenchmarkSeries, Book, BookStart, Entrant
from qi.benchmark.runner import run_benchmark
from qi.benchmark.summary import summarize_benchmark
from qi.players import PlayerConfig
os.environ["QI_BENCHMARK_STATE"] = str(root / "benchmark-state")
book = Book(id="browser-fixture", use="smoke", provenance="Hermetic browser benchmark",
            selection="One fixed start", starts=[BookStart(id="horse", family="fixture-horse",
            source_game="fixture-game", source_url="test:browser", description="Horse development",
            snapshot=Snapshot(moves=["b0c2", "b9c7"]))])
panel = [Entrant(id="baseline", label="Baseline random", config=PlayerConfig("random", seed=7)),
         Entrant(id="candidate", label="Candidate random", config=PlayerConfig("random", seed=17))]
spec = BenchmarkSpec(series=BenchmarkSeries(id="browser-benchmark", label="Benchmark browser fixture",
                     book=book, references=panel, anchor="baseline"), starts=["horse"])
run_benchmark(spec, root / "benchmarks/complete")
summarize_benchmark(root / "benchmarks/complete", persist=True)
locked = spec.model_copy(deep=True)
locked.series.label = "Locked benchmark fixture"
locked.series.book.use = "locked-test"
run_benchmark(locked, root / "benchmarks/locked")

# Authored research is a read-only presentation of tiny pinned fixture evidence.
import base64
import hashlib
from qi.experiments.research import present

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
    "## Next focus\n\nSeparate coverage from representation under stable optimization.\n"
)
(research / "previous.md").write_text(
    "# Earlier interpretation\n\nA retained, inconclusive fixture finding.\n\n"
    "| Evidence | Scope |\n| --- | --- |\n| One pool | Exploratory |\n"
)
(research / "diagram.png").write_bytes(base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
))
research_results = research / "results.json"
research_results.write_text(json.dumps({
    "fits": 6,
    "rows": [
        {"case": case, "update": update, "agreement": agreement,
         "loss": loss, "n": n}
        for update, observations in (
            (50, (("b", 0.25, 2.5, 12), ("a", 0, 1.5, 12), ("c", None, None, 0))),
            (200, (("b", 0.5, 3.5, 12), ("a", 0.125, 2.0, 12), ("c", None, None, 0))),
        )
        for case, agreement, loss, n in observations
    ],
}))
research_view = research / "view.json"
research_view.write_text(json.dumps({
    "version": "research-view-v1",
    "summary": "Investigate coverage and optimization together.",
    "section_notes": {"observations-and-limits": "Presentation note: original interpretation retained for review."},
    "data_sources": {"findings": {
        "path": "research/results.json",
        "sha256": hashlib.sha256(research_results.read_bytes()).hexdigest(),
    }},
    "stats": [{"label": "Recorded fits", "value": {"source": "findings", "pointer": "/fits"},
               "note": "Synthetic fixture observations"}],
    "takeaways": [{"title": "Check the denominator", "body": "Unknown is different from observed zero."}],
    "explorers": [{
        "id": "recorded-models", "title": "Recorded model contrasts",
        "description": "Synthetic fixed-order observations.",
        "caveat": "Imitation agreement does not establish playing strength.",
        "source": "findings", "rows_pointer": "/rows", "label_pointer": "/case",
        "labels": {"a": "Model A", "b": "Model B", "c": "Model C"},
        "facets": [{"key": "update", "label": "Training updates", "pointer": "/update", "initial": 200}],
        "metrics": [
            {"key": "agreement", "label": "Target agreement", "pointer": "/agreement", "format": "percent",
             "note": "Same inspected target pool; unknown remains unknown.", "denominator_pointer": "/n"},
            {"key": "loss", "label": "Cross-entropy", "pointer": "/loss", "format": "decimal", "unit": "nats", "precision": 3,
             "note": "Micro mean; lower values need their stated conditions.", "denominator_pointer": "/n"},
        ],
    }],
}))
present(research_owner, research / "enhanced.html", research_view, root=root)
present(research_owner, research / "plain.html", root=root)
