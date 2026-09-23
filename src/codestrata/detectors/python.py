from __future__ import annotations

import re
from pathlib import PurePosixPath

from ..models import Evidence, EvidenceKind
from .base import DetectionContext


PYTHON_TECHNOLOGIES = {
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
}

REQ_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*([<>=!~].*)?$", re.MULTILINE)


class PythonDetector:
    name = "python-ecosystem"

    def detect(self, context: DetectionContext) -> list[Evidence]:
        evidence: list[Evidence] = []
        manifest_paths = [
            path for path in context.files
            if PurePosixPath(path).name.lower() in {"requirements.txt", "pyproject.toml", "pipfile"}
        ][:30]

        for path in manifest_paths:
            content = context.read(path)
            if not content:
                continue
            lowered = content.lower()
            for package, technology in PYTHON_TECHNOLOGIES.items():
                version = None
                if PurePosixPath(path).name.lower() == "requirements.txt":
                    for match in REQ_PATTERN.finditer(content):
                        if match.group(1).lower().replace("_", "-") == package:
                            version = (match.group(2) or "").strip() or None
                            break
                pattern = re.compile(rf"(?<![a-z0-9_-]){re.escape(package)}(?![a-z0-9_-])", re.IGNORECASE)
                if pattern.search(lowered):
                    evidence.append(
                        Evidence(
                            technology,
                            EvidenceKind.MANIFEST,
                            path,
                            f"Python dependency: {package}",
                            80,
                            version,
                        )
                    )

        filenames = {PurePosixPath(path).name.lower(): path for path in context.files}
        if "manage.py" in filenames:
            evidence.append(Evidence("Django", EvidenceKind.FILE, filenames["manage.py"], "Django management entrypoint", 45))

        source_paths = [path for path in context.files if path.lower().endswith(".py")][:100]
        signatures = {
            "Django": re.compile(r"(?:from|import)\s+django"),
            "Flask": re.compile(r"from\s+flask\s+import|import\s+flask"),
            "FastAPI": re.compile(r"from\s+fastapi\s+import|import\s+fastapi"),
        }
        seen: set[tuple[str, str]] = set()
        for path in source_paths:
            content = context.read(path, max_bytes=160_000)
            if not content:
                continue
            for technology, pattern in signatures.items():
                if pattern.search(content) and (technology, path) not in seen:
                    seen.add((technology, path))
                    evidence.append(Evidence(technology, EvidenceKind.SOURCE, path, f"{technology} import", 20))

        return evidence
