from __future__ import annotations

import json
from collections import Counter
from pathlib import PurePosixPath

from ..models import Evidence, EvidenceKind
from .base import DetectionContext


EXTENSIONS = {
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
}


class LanguageDetector:
    name = "languages-and-runtimes"

    def detect(self, context: DetectionContext) -> list[Evidence]:
        evidence: list[Evidence] = []
        counts: Counter[str] = Counter()
        first_path: dict[str, str] = {}
        for path in context.files:
            lowered = f"/{path.lower()}"
            if any(part in lowered for part in ("/vendor/", "/node_modules/", "/dist/", "/build/")):
                continue
            technology = EXTENSIONS.get(PurePosixPath(path).suffix.lower())
            if technology:
                counts[technology] += 1
                first_path.setdefault(technology, path)

        for technology, count in counts.items():
            weight = 40 if count == 1 else 55 if count < 10 else 70
            evidence.append(
                Evidence(
                    technology,
                    EvidenceKind.FILE,
                    first_path[technology],
                    f"{count} {technology} source file{'s' if count != 1 else ''}",
                    weight,
                )
            )

        if context.has("composer.json"):
            content = context.read("composer.json")
            if content:
                try:
                    manifest = json.loads(content)
                except json.JSONDecodeError:
                    manifest = {}
                php_version = manifest.get("require", {}).get("php") if isinstance(manifest.get("require"), dict) else None
                if php_version:
                    evidence.append(Evidence("PHP", EvidenceKind.MANIFEST, "composer.json", "PHP runtime constraint", 70, str(php_version)))

        if context.has("package.json"):
            content = context.read("package.json")
            if content:
                try:
                    manifest = json.loads(content)
                except json.JSONDecodeError:
                    manifest = {}
                engines = manifest.get("engines", {})
                if isinstance(engines, dict) and engines.get("node"):
                    evidence.append(Evidence("Node.js", EvidenceKind.MANIFEST, "package.json", "Node.js engine constraint", 75, str(engines["node"])))

        if context.has(".python-version"):
            version = (context.read(".python-version", max_bytes=4096) or "").strip()
            evidence.append(Evidence("Python", EvidenceKind.CONFIG, ".python-version", "Python version pin", 70, version or None))

        return evidence
