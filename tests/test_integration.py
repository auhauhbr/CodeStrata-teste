from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from codestrata.analyzer import Archaeologist
from codestrata.git import GitRepository
from codestrata.models import EventKind


def run(path: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, env=env)


def commit(path: Path, message: str, date: str) -> None:
    run(path, "add", ".")
    env = os.environ.copy()
    env.update({"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
    run(path, "commit", "-m", message, env=env)


class IntegrationTests(unittest.TestCase):
    def test_reconstructs_framework_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run(root, "init", "-b", "main")
            run(root, "config", "user.name", "CodeStrata Test")
            run(root, "config", "user.email", "test@example.invalid")

            (root / "package.json").write_text('{"dependencies":{"jquery":"^2.2.4"}}')
            (root / "package-lock.json").write_text("{}")
            commit(root, "legacy frontend", "2018-02-10T12:00:00+00:00")

            (root / "package.json").write_text('{"dependencies":{"react":"^16.8.0"},"devDependencies":{"webpack":"^4.0"}}')
            (root / "webpack.config.js").write_text("module.exports = {}")
            commit(root, "migrate frontend to react", "2020-05-20T12:00:00+00:00")

            (root / "Dockerfile").write_text("FROM python:3.13-slim\n")
            commit(root, "containerize app", "2023-09-01T12:00:00+00:00")

            report = Archaeologist(min_confidence=40).analyze(
                GitRepository(root), granularity="year", max_snapshots=10
            )

            self.assertEqual(len(report.snapshots), 3)
            events = {(event.kind, event.technology) for event in report.events}
            self.assertIn((EventKind.INTRODUCED, "jQuery"), events)
            self.assertIn((EventKind.REMOVED, "jQuery"), events)
            self.assertIn((EventKind.INTRODUCED, "React"), events)
            self.assertIn((EventKind.INTRODUCED, "Docker"), events)
            self.assertIn("React", {item.name for item in report.snapshots[-1].detections})


if __name__ == "__main__":
    unittest.main()
