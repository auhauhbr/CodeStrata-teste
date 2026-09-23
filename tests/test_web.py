from __future__ import annotations

import unittest

from codestrata.models import EventKind
from codestrata.wayback import WaybackSnapshot
from codestrata.web_detector import WebsiteDetector
from codestrata.website_analyzer import WebsiteArchaeologist


class FakeWaybackClient:
    def __init__(self):
        self.snapshots = [
            WaybackSnapshot("20080101000000", "http://example.test/", "a"),
            WaybackSnapshot("20150601000000", "http://example.test/", "b"),
            WaybackSnapshot("20220301000000", "https://example.test/", "c"),
        ]
        self.pages = {
            "20080101000000": '<script src="/jquery-1.2.6.min.js"></script><object data="intro.swf"></object>',
            "20150601000000": '<link href="/bootstrap-3.3.7.min.css"><script src="/jquery-1.11.3.min.js"></script>',
            "20220301000000": '<div id="__next"><script src="/_next/static/chunks/react-dom.js"></script><script id="__NEXT_DATA__">{}</script></div>',
        }

    def list_snapshots(self, url: str, *, from_year=None, to_year=None, limit=5000):
        return [
            item for item in self.snapshots
            if (from_year is None or item.captured_at.year >= from_year)
            and (to_year is None or item.captured_at.year <= to_year)
        ]

    def fetch_html(self, snapshot: WaybackSnapshot, *, max_bytes: int = 2_000_000) -> str:
        return self.pages[snapshot.timestamp]


class WebsiteDetectorTests(unittest.TestCase):
    def test_detects_legacy_frontend_and_flash(self):
        html = '''
        <script src="https://cdn.test/jquery-1.12.4.min.js"></script>
        <link href="/bootstrap-3.3.7.min.css" rel="stylesheet">
        <object type="application/x-shockwave-flash" data="hero.swf"></object>
        '''
        detections = {item.name: item for item in WebsiteDetector().detect(html, "http://example.test")}
        self.assertEqual(detections["jQuery"].version, "1.12.4")
        self.assertEqual(detections["Bootstrap"].version, "3.3.7")
        self.assertIn("Adobe Flash", detections)

    def test_detects_modern_framework_markers(self):
        html = '<script id="__NEXT_DATA__">{}</script><script src="/_next/static/react-dom.js"></script>'
        detections = {item.name for item in WebsiteDetector().detect(html, "https://example.test")}
        self.assertIn("Next.js", detections)
        self.assertIn("React", detections)


class WebsiteArchaeologistTests(unittest.TestCase):
    def test_reconstructs_archived_website_transition(self):
        report = WebsiteArchaeologist(client=FakeWaybackClient()).analyze(  # type: ignore[arg-type]
            "example.test", granularity="year", max_snapshots=10
        )
        self.assertEqual(len(report.snapshots), 3)
        self.assertEqual(report.metadata["mode"], "wayback")
        events = {(event.kind, event.technology) for event in report.events}
        self.assertIn((EventKind.INTRODUCED, "jQuery"), events)
        self.assertIn((EventKind.INTRODUCED, "Adobe Flash"), events)
        self.assertIn((EventKind.REMOVED, "Adobe Flash"), events)
        self.assertIn((EventKind.INTRODUCED, "Next.js"), events)
        self.assertIn((EventKind.INTRODUCED, "React"), events)


if __name__ == "__main__":
    unittest.main()
