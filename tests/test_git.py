from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from codestrata.git import GitRepository


def run(path: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
    )


class GitRepositoryDisplayNameTests(unittest.TestCase):
    def display_name_for(self, remote: str | None) -> str:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "example-repository"
            root.mkdir()
            run(root, "init")
            if remote is not None:
                run(root, "remote", "add", "origin", remote)
            return GitRepository(root).display_name

    def test_preserves_normal_https_remote(self):
        remote = "https://github.com/owner/repo.git"
        self.assertEqual(self.display_name_for(remote), remote)

    def test_removes_https_username_and_token(self):
        self.assertEqual(
            self.display_name_for("https://usuario:token@github.com/owner/repo.git"),
            "https://github.com/owner/repo.git",
        )

    def test_removes_https_token_only(self):
        self.assertEqual(
            self.display_name_for("https://token@github.com/owner/repo.git"),
            "https://github.com/owner/repo.git",
        )

    def test_preserves_ssh_remote(self):
        remote = "git@github.com:owner/repo.git"
        self.assertEqual(self.display_name_for(remote), remote)

    def test_uses_directory_name_without_origin(self):
        self.assertEqual(self.display_name_for(None), "example-repository")


if __name__ == "__main__":
    unittest.main()
