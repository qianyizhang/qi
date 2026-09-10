"""Run the locked teacher-quality comparison into a fresh evidence directory."""

import argparse
import json
import sys
from pathlib import Path

from qi.learning.teacher_quality import Study, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify:
            from qi.learning.teacher_quality_verify import verify

            result = verify(args.output, progress=lambda message: print(message, file=sys.stderr, flush=True))
            print(json.dumps(result, indent=2))
            return
        result = run(Study.model_validate_json(args.config.read_text()), args.output.resolve())
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None
    print(
        json.dumps({"status": result["status"], "summary": result["summary"], "error": result.get("error")}, indent=2)
    )
    raise SystemExit(0 if result["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
