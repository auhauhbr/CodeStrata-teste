from __future__ import annotations

import re
from collections import defaultdict

from .models import Evidence, EvidenceKind, TechnologyDetection


WEB_CATEGORIES = {
    "jQuery": "frontend-library",
    "React": "frontend-library",
    "Vue": "frontend-framework",
    "Angular": "frontend-framework",
    "AngularJS": "frontend-framework",
    "Bootstrap": "css-framework",
    "Tailwind CSS": "css-framework",
    "Next.js": "web-framework",
    "WordPress": "cms",
    "Adobe Flash": "browser-platform",
    "MooTools": "frontend-library",
    "Prototype.js": "frontend-library",
    "Modernizr": "frontend-library",
    "RequireJS": "module-loader",
    "Alpine.js": "frontend-library",
    "Svelte": "frontend-framework",
}


class WebsiteDetector:
    def detect(self, html: str, source_url: str) -> list[TechnologyDetection]:
        evidence: list[Evidence] = []
        lower = html.lower()

        def add(technology: str, detail: str, weight: int, version: str | None = None) -> None:
            evidence.append(
                Evidence(
                    technology=technology,
                    kind=EvidenceKind.SOURCE,
                    path=source_url,
                    detail=detail,
                    weight=weight,
                    version=version,
                )
            )

        jquery = re.search(r"jquery(?:[-./]|%2f)(\d+\.\d+(?:\.\d+)?)", lower)
        if "jquery" in lower:
            add("jQuery", "jQuery asset/signature in archived HTML", 75, jquery.group(1) if jquery else None)

        bootstrap = re.search(r"bootstrap(?:[-./]|@)(\d+\.\d+(?:\.\d+)?)", lower)
        if "bootstrap" in lower and (".css" in lower or ".js" in lower):
            add("Bootstrap", "Bootstrap asset in archived HTML", 80, bootstrap.group(1) if bootstrap else None)

        react = re.search(r"react(?:-dom)?(?:[-./@]|%2f)(\d+\.\d+(?:\.\d+)?)", lower)
        if any(marker in lower for marker in ("react.js", "react.min.js", "react-dom", "data-reactroot", "react@")):
            add("React", "React asset/DOM marker in archived HTML", 80, react.group(1) if react else None)

        vue = re.search(r"vue(?:[-./@]|%2f)(\d+\.\d+(?:\.\d+)?)", lower)
        if any(marker in lower for marker in ("vue.js", "vue.min.js", "vue@", "data-v-")):
            add("Vue", "Vue asset/DOM marker in archived HTML", 80, vue.group(1) if vue else None)

        ng_version = re.search(r"ng-version=[\"']([^\"']+)", html, flags=re.IGNORECASE)
        if ng_version:
            add("Angular", "Angular ng-version marker", 95, ng_version.group(1))
        elif "angular.js" in lower or "angular.min.js" in lower or "ng-app=" in lower:
            angular = re.search(r"angular(?:[-./]|%2f)(\d+\.\d+(?:\.\d+)?)", lower)
            add("AngularJS", "AngularJS asset/directive marker", 80, angular.group(1) if angular else None)

        if "/_next/" in lower or "__next_data__" in lower:
            add("Next.js", "Next.js _next/ or __NEXT_DATA__ marker", 95)

        if "cdn.tailwindcss.com" in lower or "tailwind.min.css" in lower:
            add("Tailwind CSS", "Tailwind asset marker", 80)

        wp = re.search(r"wordpress\s*([0-9]+(?:\.[0-9]+){1,2})?", html, flags=re.IGNORECASE)
        if "wp-content/" in lower or "wp-includes/" in lower or wp:
            add("WordPress", "WordPress asset/generator marker", 90, wp.group(1) if wp and wp.group(1) else None)

        if ".swf" in lower or "application/x-shockwave-flash" in lower or "shockwaveflash" in lower:
            add("Adobe Flash", "Flash object/SWF asset in archived HTML", 90)

        if "mootools" in lower:
            version = self._asset_version(lower, "mootools")
            add("MooTools", "MooTools asset marker", 85, version)
        if "prototype.js" in lower or "prototype.min.js" in lower:
            version = self._asset_version(lower, "prototype")
            add("Prototype.js", "Prototype.js asset marker", 85, version)
        if "modernizr" in lower:
            version = self._asset_version(lower, "modernizr")
            add("Modernizr", "Modernizr asset marker", 80, version)
        if "require.js" in lower or "require.min.js" in lower or "requirejs" in lower:
            version = self._asset_version(lower, "require")
            add("RequireJS", "RequireJS asset marker", 80, version)
        if "alpinejs" in lower or "alpine.js" in lower:
            add("Alpine.js", "Alpine.js asset marker", 80, self._asset_version(lower, "alpine"))
        if "__svelte" in lower or "/_app/immutable/" in lower:
            add("Svelte", "Svelte runtime/build marker", 75)

        grouped: dict[str, list[Evidence]] = defaultdict(list)
        for item in evidence:
            grouped[item.technology].append(item)

        detections: list[TechnologyDetection] = []
        for technology, items in grouped.items():
            versions = [item.version for item in items if item.version]
            detections.append(
                TechnologyDetection(
                    name=technology,
                    category=WEB_CATEGORIES.get(technology, "other"),
                    confidence=min(100, sum(item.weight for item in items)),
                    version=versions[0] if versions else None,
                    evidence=items,
                )
            )
        return sorted(detections, key=lambda item: (-item.confidence, item.name.lower()))

    @staticmethod
    def _asset_version(html: str, name: str) -> str | None:
        match = re.search(rf"{re.escape(name)}(?:[-./@]|%2f)(\d+\.\d+(?:\.\d+)?)", html)
        return match.group(1) if match else None
