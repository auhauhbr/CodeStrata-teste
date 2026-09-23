from __future__ import annotations

import re
from pathlib import PurePosixPath

from ..models import Evidence, EvidenceKind
from .base import DetectionContext


class RubyDetector:
    name = "ruby-ecosystem"

    def detect(self, context: DetectionContext) -> list[Evidence]:
        evidence: list[Evidence] = []
        gemfiles = [path for path in context.files if PurePosixPath(path).name.lower() == "gemfile"]
        rails_pattern = re.compile(r"gem\s+[\"']rails[\"'](?:\s*,\s*[\"']([^\"']+)[\"'])?")
        for path in gemfiles[:20]:
            content = context.read(path)
            if not content:
                continue
            match = rails_pattern.search(content)
            if match:
                evidence.append(
                    Evidence(
                        "Ruby on Rails",
                        EvidenceKind.MANIFEST,
                        path,
                        "Rails gem dependency",
                        85,
                        match.group(1),
                    )
                )

        for path in context.files:
            if path.lower().endswith("config/application.rb"):
                evidence.append(Evidence("Ruby on Rails", EvidenceKind.CONFIG, path, "Rails application config", 50))
                break
        return evidence
