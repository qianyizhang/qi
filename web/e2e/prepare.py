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
