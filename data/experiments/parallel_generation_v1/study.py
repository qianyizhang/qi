"""Matched production serial/parallel CLI runs, including combined publication."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from time import monotonic, sleep

from checks import combined

from qi.artifacts import provenance, write_json
from qi.training_data.parallel_generation import archive_sources, pool_resources, stop_workers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    origin = provenance()
    write_json(output / "runtime.json", {"runtime": origin, "files": archive_sources(output / "source")}, indent=2)
    for path in Path(__file__).parent.glob("*.py"):
        shutil.copyfile(path, output / path.name)
    # Resolve asset paths against the original recipe; freeze the same 180-second allowance for both arms.
    from qi.training_data.generation_runner import PolicyGenerationConfig

    config = PolicyGenerationConfig.model_validate_json(args.config.read_text()).resolve(args.config.resolve().parent)
    config.seconds = 180.0
    write_json(output / "config.json", config.model_dump(), indent=2)
    rows, signature = [], None
    deadline = monotonic() + 1200
    try:
        for round_id in range(1, 4):
            for workers in (1, 2) if round_id % 2 else (2, 1):
                cell = output / f"round-{round_id}-workers-{workers}"
                tick = monotonic()
                peak = 0
                with cell.with_suffix(".log").open("x") as log:
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "scripts/run_generation_pilot.py",
                            "--config",
                            str(output / "config.json"),
                            "--output",
                            str(cell),
                            "--workers",
                            str(workers),
                        ],
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                    try:
                        while process.poll() is None:
                            if monotonic() >= min(deadline, tick + 180):
                                raise TimeoutError("Confirmation allowance exhausted")
                            sample = pool_resources([process], peak)
                            if not sample["process"]["available"]:
                                raise RuntimeError("RSS sampling unavailable; run with process-table access")
                            peak = sample["peak_sampled_combined_rss_bytes"]
                            sleep(0.1)
                        if process.returncode:
                            raise RuntimeError(f"CLI exited {process.returncode}: {cell.with_suffix('.log')}")
                    finally:
                        stop_workers([process])
                seconds = monotonic() - tick
                verified = combined([cell / "collection.sqlite"])
                signature = signature or verified
                if verified != signature:
                    raise ValueError(f"Output mismatch: {cell}")
                latest = json.loads((cell / "latest.json").read_text())
                summary = json.loads((Path(latest["execution"]) / "summary.json").read_text())
                rows.append(
                    {
                        "round": round_id,
                        "workers": workers,
                        "wall_seconds": seconds,
                        "peak_sampled_rss_bytes": peak,
                        "combine_seconds": summary.get("combine_seconds"),
                        "verified": verified,
                        "path": str(cell),
                    }
                )
                write_json(output / "summary.json", {"status": "running", "results": rows}, indent=2)
                print(json.dumps(rows[-1]), flush=True)
        if provenance()["source_sha256"] != origin["source_sha256"]:
            raise ValueError("Source changed during confirmation")
        write_json(output / "summary.json", {"status": "complete", "results": rows}, indent=2)
    except BaseException as exc:
        write_json(output / "summary.json", {"status": "incomplete", "error": str(exc), "results": rows}, indent=2)
        raise


if __name__ == "__main__":
    main()
