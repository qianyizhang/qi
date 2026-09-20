"""Public CLI and portable human-game book reconstruction."""

import json
import subprocess
from pathlib import Path

from qi_game.contracts import Snapshot
from qi_game.reference import restore

from qi.benchmark.books import SourceGame, build_books
from qi.benchmark.models import BenchmarkSeries, BenchmarkSpec, Book, BookStart, Entrant
from qi.players import PlayerConfig


def test_benchmark_cli_run_and_offline_summary(tmp_path):
    book = Book(
        id="cli",
        use="smoke",
        provenance="CLI test",
        selection="One start",
        starts=[
            BookStart(
                id="horse",
                family="one",
                source_game="one",
                source_url="test:one",
                description="Horse",
                snapshot=Snapshot(moves=["b0c2", "b9c7"]),
            )
        ],
    )
    series = BenchmarkSeries(
        id="cli",
        label="CLI benchmark",
        book=book,
        anchor="a",
        references=[
            Entrant(id="a", label="A", config=PlayerConfig("random", seed=7)),
            Entrant(id="b", label="B", config=PlayerConfig("random", seed=17)),
        ],
    )
    path = tmp_path / "spec.json"
    path.write_text(BenchmarkSpec(series=series, starts=["horse"]).model_dump_json())
    run = tmp_path / "run"

    def command(*args):
        return subprocess.run(["qi", "bench", *map(str, args)], capture_output=True, text=True, check=True)

    assert json.loads(command("preview", "--spec", path).stdout)["games"] == 4
    result = json.loads(command("run", "--spec", path, "--output", run).stdout)
    assert result["completed_games"] == 4
    assert json.loads(command("summarize", "--run", run).stdout) == result
    assert json.loads(command("resume", "--run", run).stdout) == result


def test_sourced_books_reproduce_and_keep_families_games_and_starts_separate():
    root = Path(__file__).resolve().parents[1] / "data/evaluation/human-openings-v1"
    source = json.loads((root / "sources.json").read_text())
    dev, locked, audit = build_books(
        [SourceGame.model_validate(g) for g in source["games"]], id="ccpd-openings-v1", provenance=source["provenance"]
    )
    assert dev == Book.model_validate_json((root / "development.json").read_text())
    assert locked == Book.model_validate_json((root / "locked-test.json").read_text())
    assert audit["accepted"] == {"development": 170, "locked-test": 30}
    for field in ("family", "source_game"):
        assert not {getattr(s, field) for s in dev.starts} & {getattr(s, field) for s in locked.starts}
    assert not {restore(s.snapshot).board for s in dev.starts} & {restore(s.snapshot).board for s in locked.starts}
