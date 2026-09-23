from __future__ import annotations

import json
from pathlib import PurePosixPath

from ..models import Evidence, EvidenceKind
from .base import DetectionContext


COMPOSER_TECHNOLOGIES = {
    "laravel/framework": "Laravel",
    "laravel/lumen-framework": "Laravel",
    "symfony/framework-bundle": "Symfony",
    "symfony/symfony": "Symfony",
}


class PhpDetector:
    name = "php-ecosystem"

    def detect(self, context: DetectionContext) -> list[Evidence]:
        evidence: list[Evidence] = []
        composer_paths = [path for path in context.files if PurePosixPath(path).name == "composer.json"]
        for path in composer_paths[:20]:
            content = context.read(path)
            if not content:
                continue
            try:
                manifest = json.loads(content)
            except json.JSONDecodeError:
                continue
            requirements: dict[str, str] = {}
            for section in ("require", "require-dev"):
                values = manifest.get(section, {})
                if isinstance(values, dict):
                    requirements.update({str(key): str(value) for key, value in values.items()})

            evidence.append(Evidence("Composer", EvidenceKind.MANIFEST, path, "composer.json manifest", 85))
            for package, technology in COMPOSER_TECHNOLOGIES.items():
                if package in requirements:
                    evidence.append(
                        Evidence(
                            technology,
                            EvidenceKind.MANIFEST,
                            path,
                            f"Composer dependency: {package}",
                            85,
                            requirements[package],
                        )
                    )

        lowered = {path.lower(): path for path in context.files}
        if "artisan" in lowered:
            evidence.append(Evidence("Laravel", EvidenceKind.FILE, lowered["artisan"], "Laravel artisan entrypoint", 45))
        for path in context.files:
            normalized = path.lower()
            if normalized.endswith("config/bundles.php"):
                evidence.append(Evidence("Symfony", EvidenceKind.CONFIG, path, "Symfony bundles configuration", 50))
                break

        return evidence
