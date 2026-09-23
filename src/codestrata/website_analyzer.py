from __future__ import annotations

from datetime import UTC, datetime

from .models import ArchaeologyReport, Snapshot
from .sampling import Granularity
from .timeline import build_timeline
from .wayback import WaybackClient, WaybackError
from .web_detector import WebsiteDetector
from .web_sampling import sample_wayback_snapshots


class WebsiteArchaeologist:
    def __init__(
        self,
        *,
        client: WaybackClient | None = None,
        min_confidence: int = 40,
    ):
        if not 0 <= min_confidence <= 100:
            raise ValueError("min_confidence must be between 0 and 100")
        self.client = client or WaybackClient()
        self.detector = WebsiteDetector()
        self.min_confidence = min_confidence

    def analyze(
        self,
        url: str,
        *,
        granularity: Granularity = "year",
        max_snapshots: int = 24,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> ArchaeologyReport:
        available = self.client.list_snapshots(url, from_year=from_year, to_year=to_year)
        selected = sample_wayback_snapshots(
            available,
            granularity=granularity,
            max_snapshots=max_snapshots,
        )

        snapshots: list[Snapshot] = []
        failed = 0
        for archived in selected:
            try:
                html = self.client.fetch_html(archived)
            except WaybackError:
                failed += 1
                continue
            detections = [
                item for item in self.detector.detect(html, archived.original_url)
                if item.confidence >= self.min_confidence
            ]
            snapshots.append(
                Snapshot(
                    ref=archived.archive_url,
                    sha=archived.timestamp,
                    committed_at=archived.captured_at,
                    detections=detections,
                )
            )

        return ArchaeologyReport(
            repository=url,
            generated_at=datetime.now(UTC),
            snapshots=snapshots,
            events=build_timeline(snapshots),
            metadata={
                "mode": "wayback",
                "capture_count": len(available),
                "selected_capture_count": len(selected),
                "snapshot_count": len(snapshots),
                "failed_snapshot_count": failed,
                "granularity": granularity,
                "min_confidence": self.min_confidence,
                "from_year": from_year,
                "to_year": to_year,
            },
        )
