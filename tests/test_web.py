from __future__ import annotations

import unittest
from unittest.mock import patch

from codestrata.models import EventKind
from codestrata.wayback import WaybackClient, WaybackSnapshot
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


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content
        self.read_sizes: list[int | None] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, size: int | None = None) -> bytes:
        self.read_sizes.append(size)
        if size is None:
            return self.content
        return self.content[:size]


class WaybackClientTests(unittest.TestCase):
    snapshot = WaybackSnapshot("20240102030405", "https://example.test/", "digest")

    def fetch(self, content: bytes, *, max_bytes: int) -> tuple[str, FakeResponse]:
        response = FakeResponse(content)
        with patch("codestrata.wayback.urlopen", return_value=response):
            html = WaybackClient().fetch_html(self.snapshot, max_bytes=max_bytes)
        return html, response

    def test_fetch_html_returns_content_below_limit(self):
        html, response = self.fetch(b"abcdef", max_bytes=10)
        self.assertEqual(html, "abcdef")
        self.assertEqual(response.read_sizes, [11])

    def test_fetch_html_limits_response_read(self):
        html, response = self.fetch(b"abcdefghij", max_bytes=5)
        self.assertEqual(html, "abcde")
        self.assertEqual(response.read_sizes, [6])

    def test_fetch_html_replaces_invalid_utf8(self):
        html, _ = self.fetch(b"abc\xffdef", max_bytes=10)
        self.assertEqual(html, "abc\ufffddef")

    def test_fetch_html_preserves_content_at_exact_limit(self):
        html, response = self.fetch(b"abcdef", max_bytes=6)
        self.assertEqual(html, "abcdef")
        self.assertEqual(response.read_sizes, [7])

    def test_fetch_html_accepts_zero_limit(self):
        with patch("codestrata.wayback.urlopen") as mocked_urlopen:
            html = WaybackClient().fetch_html(self.snapshot, max_bytes=0)
        self.assertEqual(html, "")
        mocked_urlopen.assert_not_called()

    def test_fetch_html_rejects_negative_limit_without_request(self):
        with patch("codestrata.wayback.urlopen") as mocked_urlopen:
            with self.assertRaisesRegex(ValueError, "max_bytes must be non-negative"):
                WaybackClient().fetch_html(self.snapshot, max_bytes=-1)
        mocked_urlopen.assert_not_called()

    def test_fetch_html_rejects_non_integer_limit_without_request(self):
        with patch("codestrata.wayback.urlopen") as mocked_urlopen:
            with self.assertRaisesRegex(TypeError, "max_bytes must be an integer"):
                WaybackClient().fetch_html(self.snapshot, max_bytes=1.5)  # type: ignore[arg-type]
        mocked_urlopen.assert_not_called()

    def test_fetch_html_rejects_boolean_limit_without_request(self):
        with patch("codestrata.wayback.urlopen") as mocked_urlopen:
            for max_bytes in (True, False):
                with self.subTest(max_bytes=max_bytes):
                    with self.assertRaisesRegex(TypeError, "max_bytes must be an integer"):
                        WaybackClient().fetch_html(self.snapshot, max_bytes=max_bytes)
        mocked_urlopen.assert_not_called()


class WebsiteDetectorTests(unittest.TestCase):
    def test_does_not_detect_technology_names_in_visible_text(self):
        html = """
        <html><body>
        <p>We migrated from jQuery to React and replaced Bootstrap in our WordPress site.</p>
        </body></html>
        """
        detections = {item.name for item in WebsiteDetector().detect(html, "https://example.test")}
        self.assertTrue({"jQuery", "React", "Bootstrap", "WordPress"}.isdisjoint(detections))

    def test_does_not_detect_technology_names_in_irrelevant_attributes(self):
        html = '<p title="jQuery React Bootstrap WordPress">Migration article</p>'
        detections = {item.name for item in WebsiteDetector().detect(html, "https://example.test")}
        self.assertTrue({"jQuery", "React", "Bootstrap", "WordPress"}.isdisjoint(detections))

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

    def test_detects_wordpress_generator_and_version(self):
        html = '<meta name="generator" content="WordPress 6.4.2">'
        detections = {item.name: item for item in WebsiteDetector().detect(html, "https://example.test")}
        self.assertEqual(detections["WordPress"].version, "6.4.2")

    def test_detects_modern_framework_markers(self):
        html = '<script id="__NEXT_DATA__">{}</script><script src="/_next/static/react-dom.js"></script>'
        detections = {item.name for item in WebsiteDetector().detect(html, "https://example.test")}
        self.assertIn("Next.js", detections)
        self.assertIn("React", detections)

    def test_detects_angular_and_vue_structural_markers(self):
        cases = (
            ('<main ng-version="17.0.0"></main>', "Angular", "17.0.0"),
            ('<main ng-app="legacy"></main>', "AngularJS", None),
            ('<main data-v-a1b2c3></main>', "Vue", None),
        )
        for html, technology, version in cases:
            with self.subTest(technology=technology):
                detections = {
                    item.name: item
                    for item in WebsiteDetector().detect(html, "https://example.test")
                }
                self.assertIn(technology, detections)
                self.assertEqual(detections[technology].version, version)


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
