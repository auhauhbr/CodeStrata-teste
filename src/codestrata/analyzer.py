from __future__ import annotations

from datetime import UTC, datetime

from .detectors import DetectionContext, DetectionEngine, default_detectors
from .git import GitRepository
from .models import ArchaeologyReport, Snapshot, TechnologyDetection
from .sampling import Granularity, sample_commits
from .timeline import build_timeline


class Archaeologist:
    def __init__(self, *, min_confidence: int = 40):
        if not 0 <= min_confidence <= 100:
            raise ValueError("min_confidence must be between 0 and 100")
        self.min_confidence = min_confidence
        self.engine = DetectionEngine(default_detectors())

    def inspect(self, repository: GitRepository, ref: str) -> Snapshot:
        commit = repository.commit(ref)
        files = repository.list_files(commit.sha)
        context = DetectionContext(repository=repository, ref=commit.sha, files=files)
        detections = [
            item for item in self.engine.run(context)
            if item.confidence >= self.min_confidence
        ]
        return Snapshot(
            ref=ref,
            sha=commit.sha,
            committed_at=commit.committed_at,
            detections=detections,
        )

    def analyze(
        self,
        repository: GitRepository,
        *,
        granularity: Granularity = "year",
        max_snapshots: int = 24,
    ) -> ArchaeologyReport:
        commits = repository.commits()
        selected = sample_commits(
            commits,
            granularity=granularity,
            max_snapshots=max_snapshots,
        )
        snapshots = [self.inspect(repository, commit.sha) for commit in selected]
        return ArchaeologyReport(
            repository=repository.display_name,
            generated_at=datetime.now(UTC),
            snapshots=snapshots,
            events=build_timeline(snapshots),
            metadata={
                "commit_count": len(commits),
                "snapshot_count": len(snapshots),
                "granularity": granularity,
                "min_confidence": self.min_confidence,
            },
        )


def technology_index(snapshot: Snapshot) -> dict[str, TechnologyDetection]:
    return {item.name: item for item in snapshot.detections}
