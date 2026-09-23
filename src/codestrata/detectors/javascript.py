from __future__ import annotations

import json
import re
from pathlib import PurePosixPath

from ..models import Evidence, EvidenceKind
from .base import DetectionContext


PACKAGE_TECHNOLOGIES = {
    "jquery": "jQuery",
    "react": "React",
    "react-dom": "React",
    "vue": "Vue",
    "@angular/core": "Angular",
    "bootstrap": "Bootstrap",
    "tailwindcss": "Tailwind CSS",
    "next": "Next.js",
    "express": "Express",
    "typescript": "TypeScript",
    "webpack": "Webpack",
    "vite": "Vite",
    "grunt": "Grunt",
    "gulp": "Gulp",
}

CONFIG_TECHNOLOGIES = {
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "next.config.ts": "Next.js",
    "vite.config.js": "Vite",
    "vite.config.mjs": "Vite",
    "vite.config.ts": "Vite",
    "webpack.config.js": "Webpack",
    "webpack.config.ts": "Webpack",
    "gruntfile.js": "Grunt",
    "gulpfile.js": "Gulp",
    "tailwind.config.js": "Tailwind CSS",
    "tailwind.config.ts": "Tailwind CSS",
    "tsconfig.json": "TypeScript",
}

SIGNATURES: list[tuple[str, re.Pattern[str], str]] = [
    ("jQuery", re.compile(r"(?:jQuery\s*\(|\$\s*\([\"'])"), "jQuery call signature"),
    ("React", re.compile(r"(?:from\s+[\"']react[\"']|ReactDOM\.|createRoot\s*\()"), "React import/API signature"),
    ("Vue", re.compile(r"(?:from\s+[\"']vue[\"']|createApp\s*\()"), "Vue import/API signature"),
    ("Angular", re.compile(r"@angular/(?:core|common|router)"), "Angular import signature"),
    ("Bootstrap", re.compile(r"(?:bootstrap(?:\.min)?\.css|class=[\"'][^\"']*\b(?:btn|container|row)\b)"), "Bootstrap asset/class signature"),
    ("Tailwind CSS", re.compile(r"@tailwind\s+(?:base|components|utilities)"), "Tailwind directive"),
    ("Express", re.compile(r"(?:require\([\"']express[\"']\)|from\s+[\"']express[\"'])"), "Express import signature"),
]


class JavaScriptDetector:
    name = "javascript-ecosystem"

    def detect(self, context: DetectionContext) -> list[Evidence]:
        evidence: list[Evidence] = []
        package_paths = [path for path in context.files if PurePosixPath(path).name == "package.json"]
        for path in package_paths[:20]:
            content = context.read(path)
            if not content:
                continue
            try:
                package = json.loads(content)
            except json.JSONDecodeError:
                continue
            dependencies: dict[str, str] = {}
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                values = package.get(section, {})
                if isinstance(values, dict):
                    dependencies.update({str(key): str(value) for key, value in values.items()})
            for dependency, technology in PACKAGE_TECHNOLOGIES.items():
                if dependency in dependencies:
                    evidence.append(
                        Evidence(
                            technology=technology,
                            kind=EvidenceKind.MANIFEST,
                            path=path,
                            detail=f"package dependency: {dependency}",
                            weight=80,
                            version=dependencies[dependency],
                        )
                    )

        for path in context.files:
            filename = PurePosixPath(path).name.lower()
            if filename in CONFIG_TECHNOLOGIES:
                technology = CONFIG_TECHNOLOGIES[filename]
                evidence.append(
                    Evidence(
                        technology=technology,
                        kind=EvidenceKind.CONFIG,
                        path=path,
                        detail=f"configuration file: {filename}",
                        weight=70,
                    )
                )
            if filename == "package-lock.json":
                evidence.append(Evidence("npm", EvidenceKind.LOCKFILE, path, "npm lockfile", 90))
            elif filename == "yarn.lock":
                evidence.append(Evidence("Yarn", EvidenceKind.LOCKFILE, path, "Yarn lockfile", 90))
            elif filename == "pnpm-lock.yaml":
                evidence.append(Evidence("pnpm", EvidenceKind.LOCKFILE, path, "pnpm lockfile", 90))

        source_paths = [
            path
            for path in context.files
            if path.lower().endswith((".js", ".jsx", ".ts", ".tsx", ".html", ".htm", ".vue", ".css"))
            and "/vendor/" not in f"/{path.lower()}"
            and "/node_modules/" not in f"/{path.lower()}"
        ][:100]
        found_signatures: set[tuple[str, str]] = set()
        for path in source_paths:
            content = context.read(path, max_bytes=160_000)
            if not content:
                continue
            for technology, pattern, detail in SIGNATURES:
                key = (technology, path)
                if key in found_signatures or not pattern.search(content):
                    continue
                found_signatures.add(key)
                evidence.append(
                    Evidence(
                        technology=technology,
                        kind=EvidenceKind.SOURCE,
                        path=path,
                        detail=detail,
                        weight=20,
                    )
                )

        return evidence
