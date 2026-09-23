from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from codestrata.exporters import render_html, write_json
from codestrata.git import Commit
from codestrata.models import ArchaeologyReport, EventKind, TimelineEvent
from codestrata.sampling import sample_commits


class SamplingTests(unittest.TestCase):
    def test_keeps_first_commit_per_year_and_latest(self):
        commits = [
            Commit("a" * 40, datetime(2020, 1, 1, tzinfo=UTC), "first"),
            Commit("b" * 40, datetime(2020, 8, 1, tzinfo=UTC), "same year"),
            Commit("c" * 40, datetime(2021, 2, 1, tzinfo=UTC), "next year"),
            Commit("d" * 40, datetime(2021, 9, 1, tzinfo=UTC), "latest"),
        ]
        sampled = sample_commits(commits, granularity="year", max_snapshots=10)
        self.assertEqual([item.sha[0] for item in sampled], ["a", "c", "d"])

    def test_caps_snapshots_but_keeps_endpoints(self):
        commits = [
            Commit(str(year) * 10, datetime(year, 1, 1, tzinfo=UTC), str(year))
            for year in range(2010, 2020)
        ]
        sampled = sample_commits(commits, max_snapshots=4)
        self.assertEqual(len(sampled), 4)
        self.assertEqual(sampled[0].committed_at.year, 2010)
        self.assertEqual(sampled[-1].committed_at.year, 2019)


class ExportTests(unittest.TestCase):
    def test_json_and_html_exports(self):
        event = TimelineEvent(
            kind=EventKind.INTRODUCED,
            technology="React",
            at=datetime(2024, 1, 1, tzinfo=UTC),
            sha="f" * 40,
            to_version="^18",
        )
        report = ArchaeologyReport(
            repository="example/repo",
            generated_at=datetime(2024, 1, 2, tzinfo=UTC),
            snapshots=[],
            events=[event],
            metadata={"commit_count": 42},
        )
        with tempfile.TemporaryDirectory() as temp:
            target = write_json(report, Path(temp) / "report.json")
            data = json.loads(target.read_text())
            self.assertEqual(data["events"][0]["technology"], "React")
        html = render_html(report)
        self.assertIn("example/repo", html)
        self.assertIn("React", html)
        self.assertIn("software archaeology report", html)
        self.assertIn('name="viewport"', html)
        self.assertIn("@media(max-width:760px)", html)
        self.assertIn('class="table-scroll"', html)
        self.assertNotIn("<th>Commit</th>", html)


if __name__ == "__main__":
    unittest.main()
