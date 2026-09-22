"""Run the documentation gate without ignored local artifacts masking broken links."""

import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


def copy_checkout(root: Path, destination: Path) -> None:
    """Copy current tracked and unignored files, including edits not yet staged."""
    root = root.resolve()
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        check=True,
        capture_output=True,
    )
    for entry in sorted(set(result.stdout.split(b"\0")) - {b""}):
        relative = Path(entry.decode())
        source, target = root / relative, destination / relative
        if not source.is_symlink() and not source.is_file():
            continue  # A tracked deletion must also be absent from the check.
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            link = source.readlink()
            if link.is_absolute() or not source.resolve().is_relative_to(root):
                raise ValueError(f"Nonportable symlink: {relative} -> {link}")
            target.symlink_to(link)
        else:
            shutil.copyfile(source, target)


def main() -> int:
    from check_docs import run

    root = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix="qi-checkout-docs-") as directory:
        checkout = Path(directory)
        try:
            copy_checkout(root, checkout)
        except ValueError as error:
            print(error)
            return 1
        print("Checking documentation in a portable checkout (ignored local artifacts excluded).")
        return run(checkout)


if __name__ == "__main__":
    raise SystemExit(main())
