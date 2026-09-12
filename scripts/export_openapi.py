"""Generate or check the frontend contracts without touching live lab state."""

import argparse
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from qi.api import create_app


def check_contracts(web: Path, schema: str) -> None:
    if (web / "openapi.json").read_text() != schema:
        raise ValueError("OpenAPI is stale; run npm run generate:api --prefix web.")
    with TemporaryDirectory(prefix="qi-api-check-") as directory:
        target = Path(directory) / "generated-api.ts"
        subprocess.run(
            [str(web / "node_modules/.bin/openapi-typescript"), str(web / "openapi.json"), "-o", str(target)],
            cwd=web,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [str(web / "node_modules/.bin/prettier"), "--write", str(target)],
            cwd=web,
            check=True,
            capture_output=True,
        )
        if target.read_bytes() != (web / "src/generated-api.ts").read_bytes():
            raise ValueError("TypeScript API declarations are stale; run npm run generate:api --prefix web.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare both generated files without modifying them")
    args = parser.parse_args()
    web = Path(__file__).resolve().parents[1] / "web"
    schema = json.dumps(create_app().openapi(), indent=2) + "\n"
    if args.check:
        try:
            check_contracts(web, schema)
        except ValueError as exc:
            parser.exit(1, f"{exc}\n")
        print("Python, OpenAPI and TypeScript contracts agree.")
    else:
        (web / "openapi.json").write_text(schema)


if __name__ == "__main__":
    main()
