from __future__ import annotations

import unittest

from codestrata.detectors import DetectionContext, DetectionEngine, default_detectors


class FakeRepository:
    def __init__(self, files: dict[str, str]):
        self.files = files

    def read_file(self, ref: str, path: str, *, max_bytes: int = 512_000) -> str | None:
        return self.files.get(path)


def detect(files: dict[str, str]):
    context = DetectionContext(FakeRepository(files), "HEAD", list(files))  # type: ignore[arg-type]
    return {item.name: item for item in DetectionEngine(default_detectors()).run(context)}


class DetectorTests(unittest.TestCase):
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

    def test_source_signature_is_lower_confidence_than_manifest(self):
        detections = detect({"legacy.js": '$("#dialog").show();'})
        self.assertEqual(detections["jQuery"].confidence, 20)


if __name__ == "__main__":
    unittest.main()
