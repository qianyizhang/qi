"""Interrupt one real worker after durable moves, then verify resume and reuse."""

import argparse
import json
from pathlib import Path

from checks import combined
from study import write

from qi.training_data.generation_runner import PolicyGenerationConfig, generate_policies
from qi.training_data.store import Collection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    config = PolicyGenerationConfig.model_validate_json(args.config.read_text()).resolve(args.config.parent)
    completed, appended, interrupted = [], 0, False

    class Interrupted(Collection):
        def append(self, *a, **kw):
            nonlocal appended, interrupted
            super().append(*a, **kw)
            if completed and not interrupted:
                appended += 1
                if appended == 5:
                    interrupted = True
                    raise KeyboardInterrupt("Injected interruption after five durable moves in the second game.")

    def event(value):
        if value["kind"] == "completed-game":
            completed.append(value["game_id"])

    path = args.output / "collection.sqlite"
    with Interrupted(path) as store:
        try:
            generate_policies(store, config, event=event)
        except KeyboardInterrupt:
            pass
        else:
            raise ValueError("Interruption was not reached.")
        if len(completed) != 1 or appended != 5:
            raise ValueError("Unexpected interruption boundary.")
        retained = tuple(store.db.execute("SELECT * FROM games WHERE id=?", (completed[0],)).fetchone())
        failed = store.db.execute("SELECT count(*) FROM games WHERE status='interrupted'").fetchone()[0]
    with Collection(path) as store:
        resumed = generate_policies(store, config)
        if tuple(store.db.execute("SELECT * FROM games WHERE id=?", (completed[0],)).fetchone()) != retained:
            raise ValueError("Completed game was rewritten on resume.")
        counts = store.counts()
        reused = generate_policies(store, config)
        if store.counts() != counts or reused["reused_games"] != sum(s.games for s in config.sources):
            raise ValueError("Completed-run reuse created new work.")
        if (
            store.db.execute("SELECT count(*) FROM games WHERE status='interrupted'").fetchone()[0] != failed
            or failed != 1
        ):
            raise ValueError("Interrupted attempt was not retained.")
    actual, expected = combined([path]), combined([args.reference])
    if actual != expected:
        raise ValueError(f"Resumed outputs differ: {actual} != {expected}")
    write(
        args.output / "result.json",
        {
            "resumed": resumed,
            "reused": reused,
            "completed": actual,
            "interrupted_attempts_retained": failed,
            "interrupted_after_appends": appended,
        },
    )
    print(json.dumps(actual))


if __name__ == "__main__":
    main()
