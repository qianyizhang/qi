"""Verify and unpack the pinned official Apple Silicon teacher into local artifacts."""

import argparse
import json
import platform
import subprocess
from hashlib import file_digest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--destination", type=Path, default=ROOT / "artifacts/teachers/pikafish-2026-01-02")
    args = parser.parse_args()
    lock = json.loads((ROOT / "data/teachers/pikafish-2026-01-02.json").read_text())
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        parser.error("This pinned binary is for Apple Silicon macOS.")
    if digest(args.archive) != lock["archive_sha256"]:
        parser.error("Archive SHA-256 does not match the pinned official release.")
    args.destination.mkdir(parents=True, exist_ok=True)
    # CONTRACT: Extract only named entries from the hash-verified archive; retain upstream licenses.
    subprocess.run(
        [
            "tar",
            "-xf",
            str(args.archive.resolve()),
            "-C",
            str(args.destination.resolve()),
            lock["engine"],
            lock["network"],
            "Copying.txt",
            "NNUE-License.md",
            "AUTHORS",
            "README.md",
        ],
        check=True,
    )
    for key in ("engine", "network"):
        if digest(args.destination / lock[key]) != lock[key + "_sha256"]:
            parser.error(f"Extracted {key} does not match the lock.")
    engine = args.destination / lock["engine"]
    engine.chmod(engine.stat().st_mode | 0o100)
    print(f"Verified teacher: {engine.resolve()}")


if __name__ == "__main__":
    main()
