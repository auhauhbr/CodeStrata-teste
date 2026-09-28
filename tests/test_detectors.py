from __future__ import annotations

import unittest

from codestrata.detectors import DetectionContext, DetectionEngine, default_detectors
from codestrata.models import Evidence, EvidenceKind


class FakeRepository:
    def __init__(self, files: dict[str, str]):
        self.files = files

    def read_file(self, ref: str, path: str, *, max_bytes: int = 512_000) -> str | None:
        return self.files.get(path)


def detect(files: dict[str, str]):
    context = DetectionContext(FakeRepository(files), "HEAD", list(files))  # type: ignore[arg-type]
    return {item.name: item for item in DetectionEngine(default_detectors()).run(context)}


class StaticDetector:
    name = "static"

    def __init__(self, evidence: list[Evidence]):
        self.evidence = evidence

    def detect(self, context: DetectionContext) -> list[Evidence]:
        return self.evidence


def aggregate(evidence: list[Evidence]):
    context = DetectionContext(FakeRepository({}), "HEAD", [])  # type: ignore[arg-type]
    return DetectionEngine([StaticDetector(evidence)]).run(context)[0]


class DetectorTests(unittest.TestCase):
    def test_stronger_evidence_version_wins(self):
        detection = aggregate(
            [
                Evidence("React", EvidenceKind.SOURCE, "src/app.js", "source", 20, "^17"),
                Evidence("React", EvidenceKind.MANIFEST, "package.json", "manifest", 80, "^18"),
            ]
        )
        self.assertEqual(detection.version, "^18")

    def test_version_selection_does_not_depend_on_input_order(self):
        evidence = [
            Evidence("React", EvidenceKind.MANIFEST, "z/package.json", "manifest", 80, "^17"),
            Evidence("React", EvidenceKind.MANIFEST, "a/package.json", "manifest", 80, "^18"),
        ]
        self.assertEqual(aggregate(evidence).version, "^18")
        self.assertEqual(aggregate(list(reversed(evidence))).version, "^18")

    def test_version_tie_uses_evidence_kind_priority(self):
        priority = [
            EvidenceKind.LOCKFILE,
            EvidenceKind.MANIFEST,
            EvidenceKind.CONFIG,
            EvidenceKind.FILE,
            EvidenceKind.SOURCE,
        ]
        for preferred, other in zip(priority, priority[1:]):
            with self.subTest(preferred=preferred, other=other):
                detection = aggregate(
                    [
                        Evidence("React", other, "a", "other", 50, "other"),
                        Evidence("React", preferred, "z", "preferred", 50, "preferred"),
                    ]
                )
                self.assertEqual(detection.version, "preferred")

    def test_complete_version_tie_is_deterministic(self):
        evidence = [
            Evidence("React", EvidenceKind.MANIFEST, "package.json", "manifest", 80, "^18"),
            Evidence("React", EvidenceKind.MANIFEST, "package.json", "manifest", 80, "^17"),
        ]
        versions = {
            aggregate(evidence).version,
            aggregate(list(reversed(evidence))).version,
        }
        self.assertEqual(versions, {"^17"})

    def test_evidence_without_version_still_contributes_to_confidence(self):
        detection = aggregate(
            [
                Evidence("React", EvidenceKind.MANIFEST, "package.json", "manifest", 60, "^18"),
                Evidence("React", EvidenceKind.SOURCE, "app.js", "source", 30),
            ]
        )
        self.assertEqual(detection.version, "^18")
        self.assertEqual(detection.confidence, 90)

    def test_no_version_remains_none_and_confidence_is_capped(self):
        detection = aggregate(
            [
                Evidence("React", EvidenceKind.MANIFEST, "package.json", "manifest", 80),
                Evidence("React", EvidenceKind.SOURCE, "app.js", "source", 40),
            ]
        )
        self.assertIsNone(detection.version)
        self.assertEqual(detection.confidence, 100)

    def test_detects_react_typescript_vite_and_npm(self):
        detections = detect(
            {
                "package.json": '{"dependencies":{"react":"^18.3.1"},"devDependencies":{"typescript":"^5.6","vite":"^5.4"}}',
                "package-lock.json": "{}",
                "vite.config.ts": "export default {}",
                "src/main.tsx": 'import React from "react"; React.createElement("div")',
                "tsconfig.json": "{}",
            }
        )
        self.assertGreaterEqual(detections["React"].confidence, 80)
        self.assertEqual(detections["React"].version, "^18.3.1")
        self.assertIn("TypeScript", detections)
        self.assertIn("Vite", detections)
        self.assertEqual(detections["npm"].confidence, 90)

    def test_detects_laravel_and_composer(self):
        detections = detect(
            {
                "composer.json": '{"require":{"php":"^8.3","laravel/framework":"^11.0"}}',
                "artisan": "#!/usr/bin/env php",
            }
        )
        self.assertEqual(detections["Laravel"].confidence, 100)
        self.assertEqual(detections["Laravel"].version, "^11.0")
        self.assertIn("Composer", detections)

    def test_detects_python_framework_from_manifest_and_source(self):
        detections = detect(
            {
                "requirements.txt": "fastapi==0.115.0\nuvicorn==0.30.0\n",
                "app.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            }
        )
        self.assertEqual(detections["FastAPI"].confidence, 100)
        self.assertEqual(detections["FastAPI"].version, "==0.115.0")

    def test_ignores_python_framework_names_in_pyproject_description(self):
        detections = detect(
            {
                "pyproject.toml": '''
[project]
name = "demo"
description = "Migrating away from Django and Flask"
dependencies = []
''',
            }
        )
        self.assertNotIn("Django", detections)
        self.assertNotIn("Flask", detections)

    def test_detects_pep621_dependencies_with_constraints(self):
        detections = detect(
            {
                "pyproject.toml": '''
[project]
dependencies = [
  "Django>=5.1",
  "fastapi==0.115.0",
]
''',
            }
        )
        self.assertEqual(detections["Django"].version, ">=5.1")
        self.assertEqual(detections["FastAPI"].version, "==0.115.0")

    def test_detects_pep621_optional_dependencies(self):
        detections = detect(
            {
                "pyproject.toml": '''
[project.optional-dependencies]
test = ["Flask>=3"]
''',
            }
        )
        self.assertEqual(detections["Flask"].version, ">=3")

    def test_detects_poetry_dependencies_and_groups(self):
        detections = detect(
            {
                "pyproject.toml": '''
[tool.poetry.dependencies]
python = "^3.11"
django = "^5.1"

[tool.poetry.group.dev.dependencies]
flask = "^3.0"
''',
            }
        )
        self.assertEqual(detections["Django"].version, "^5.1")
        self.assertEqual(detections["Flask"].version, "^3.0")

    def test_detects_pipfile_packages(self):
        detections = detect(
            {
                "Pipfile": '''
[packages]
flask = "==3.0.0"
''',
            }
        )
        self.assertEqual(detections["Flask"].version, "==3.0.0")

    def test_ignores_requirements_comments(self):
        detections = detect(
            {
                "requirements.txt": "# project migrated from Django\nfastapi==0.115.0\n",
            }
        )
        self.assertNotIn("Django", detections)
        self.assertEqual(detections["FastAPI"].version, "==0.115.0")

    def test_ignores_invalid_python_toml_manifests(self):
        detections = detect(
            {
                "pyproject.toml": '[project\ndescription = "Django"',
                "Pipfile": '[packages\nflask = "==3.0"',
            }
        )
        self.assertNotIn("Django", detections)
        self.assertNotIn("Flask", detections)

    def test_source_signature_is_lower_confidence_than_manifest(self):
        detections = detect({"legacy.js": '$("#dialog").show();'})
        self.assertEqual(detections["jQuery"].confidence, 20)


if __name__ == "__main__":
    unittest.main()
