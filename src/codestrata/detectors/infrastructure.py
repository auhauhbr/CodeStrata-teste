from __future__ import annotations

from pathlib import PurePosixPath

from ..models import Evidence, EvidenceKind
from .base import DetectionContext


class InfrastructureDetector:
    name = "infrastructure"

    def detect(self, context: DetectionContext) -> list[Evidence]:
        evidence: list[Evidence] = []
        for path in context.files:
            name = PurePosixPath(path).name.lower()
            if name == "dockerfile" or name.startswith("dockerfile."):
                evidence.append(Evidence("Docker", EvidenceKind.FILE, path, "Dockerfile", 90))
            elif name in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}:
                evidence.append(Evidence("Docker", EvidenceKind.CONFIG, path, "Docker Compose configuration", 75))
        return evidence
