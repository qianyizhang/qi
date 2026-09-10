"""Run the locked teacher-quality comparison into a fresh evidence directory."""

import argparse
import json
from pathlib import Path

from qi.learning.teacher_quality import Study, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        from qi.learning.teacher_quality_verify import verify

        print(json.dumps(verify(args.output.resolve()), indent=2))
        return
    if args.config is None:
        parser.error("--config is required when running a study")
    result = run(Study.model_validate_json(args.config.read_text()), args.output.resolve())
    print(json.dumps({"status": result["status"], "summary": result["summary"]}, indent=2))
    raise SystemExit(0 if result["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
