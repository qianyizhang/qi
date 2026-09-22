"""Local artifacts must not make a broken checkout appear portable."""

import subprocess
from pathlib import Path

import pytest

from scripts.check_checkout_docs import copy_checkout
from scripts.check_docs import check_file, load_config


def test_checkout_check_exposes_ignored_links_and_uses_current_edits(tmp_path):
    root, checkout = tmp_path / "repo", tmp_path / "checkout"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text("artifacts/\n")
    (root / "guide.md").write_text("# Guide\n")
    (root / "alias.md").symlink_to("guide.md")
    readme = root / "README.md"
    header = (
        "---\ndescription: Fixture\nscope: fixture\nstatus: stable\n"
        "last_update: 2026-09-22\ndocument_class: coordination\n---\n"
    )
    readme.write_text(header + "[Guide](alias.md)\n")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    (root / "artifacts").mkdir()
    (root / "artifacts/local.json").write_text("{}")
    readme.write_text(readme.read_text() + "[Local evidence](artifacts/local.json)\n")
    (root / "new.md").write_text("Unstaged new file\n")
    config = load_config(Path(__file__).resolve().parents[1])
    assert check_file(readme, root, config) == ([], False)

    copy_checkout(root, checkout)
    errors, ignored = check_file(checkout / "README.md", checkout, config)
    assert not ignored
    assert len(errors) == 1 and "Broken local link to 'artifacts/local.json'" in errors[0]
    assert (checkout / "alias.md").is_symlink()
    assert (checkout / "new.md").read_text() == "Unstaged new file\n"
    assert not (checkout / "artifacts").exists()


@pytest.mark.parametrize("absolute", [False, True])
def test_checkout_rejects_host_dependent_symlinks(tmp_path, absolute):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    external = tmp_path / "host-only.md"
    external.write_text("Not part of the checkout\n")
    (root / "alias.md").symlink_to(external if absolute else Path("../host-only.md"))

    with pytest.raises(ValueError, match=r"Nonportable symlink: alias\.md"):
        copy_checkout(root, tmp_path / "checkout")


def test_checkout_rejects_absolute_links_even_to_repository_files(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    guide = root / "guide.md"
    guide.write_text("# Guide\n")
    (root / "alias.md").symlink_to(guide)

    with pytest.raises(ValueError, match=r"Nonportable symlink: alias\.md"):
        copy_checkout(root, tmp_path / "checkout")
