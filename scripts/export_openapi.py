"""Generate the frontend schema from Python-owned HTTP contracts."""

import json
from pathlib import Path

from qi.api import create_app

if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "web/openapi.json"
    target.write_text(json.dumps(create_app().openapi(), indent=2) + "\n")
