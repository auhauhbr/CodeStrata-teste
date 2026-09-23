from __future__ import annotations

from collections import defaultdict

from ..models import Evidence, TechnologyDetection
from .base import DetectionContext, Detector


CATEGORY_BY_TECHNOLOGY = {
    "jQuery": "frontend-library",
    "React": "frontend-library",
    "Vue": "frontend-framework",
    "Angular": "frontend-framework",
    "Bootstrap": "css-framework",
    "Tailwind CSS": "css-framework",
    "Next.js": "web-framework",
    "Express": "web-framework",
    "Laravel": "web-framework",
    "Symfony": "web-framework",
    "Django": "web-framework",
    "Flask": "web-framework",
    "FastAPI": "web-framework",
    "Ruby on Rails": "web-framework",
    "TypeScript": "language",
    "JavaScript": "language",
    "PHP": "language",
    "Python": "language",
    "Ruby": "language",
    "Java": "language",
    "Go": "language",
    "Rust": "language",
    "Node.js": "runtime",
    "Webpack": "build-tool",
    "Vite": "build-tool",
    "Grunt": "build-tool",
    "Gulp": "build-tool",
    "Docker": "infrastructure",
    "Composer": "package-manager",
    "npm": "package-manager",
    "Yarn": "package-manager",
    "pnpm": "package-manager",
}


class DetectionEngine:
    def __init__(self, detectors: list[Detector]):
        self.detectors = detectors

    def run(self, context: DetectionContext) -> list[TechnologyDetection]:
        grouped: dict[str, list[Evidence]] = defaultdict(list)
        for detector in self.detectors:
            for evidence in detector.detect(context):
                grouped[evidence.technology].append(evidence)

        detections: list[TechnologyDetection] = []
        for technology, evidence in grouped.items():
            confidence = min(100, sum(item.weight for item in evidence))
            versions = [item.version for item in evidence if item.version]
            version = versions[0] if versions else None
            detections.append(
                TechnologyDetection(
                    name=technology,
                    category=CATEGORY_BY_TECHNOLOGY.get(technology, "other"),
                    confidence=confidence,
                    version=version,
                    evidence=sorted(evidence, key=lambda item: item.weight, reverse=True),
                )
            )

        return sorted(detections, key=lambda item: (-item.confidence, item.name.lower()))
