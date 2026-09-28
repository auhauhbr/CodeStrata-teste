from __future__ import annotations

import re
from collections import defaultdict
from html.parser import HTMLParser

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


class _HTMLSignals(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scripts: list[str] = []
        self.links: list[str] = []
        self.urls: list[str] = []
        self.meta_generators: list[str] = []
        self.attribute_names: set[str] = set()
        self.attribute_values: dict[str, list[str]] = defaultdict(list)
        self.marker_values: list[str] = []
        self.embedded_values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): (value or "") for name, value in attrs}
        self.attribute_names.update(attributes)
        for name, value in attributes.items():
            self.attribute_values[name].append(value)
        self.urls.extend(
            attributes[name]
            for name in ("src", "href")
            if attributes.get(name)
        )

        if tag == "script" and attributes.get("src"):
            self.scripts.append(attributes["src"])
        elif tag == "link" and attributes.get("href"):
            self.links.append(attributes["href"])
        elif tag == "meta" and attributes.get("name", "").lower() == "generator":
            self.meta_generators.append(attributes.get("content", ""))

        for name in ("id", "class"):
            if attributes.get(name):
                self.marker_values.append(attributes[name])

        if tag in {"object", "embed"}:
            self.embedded_values.extend(
                attributes[name]
                for name in ("data", "src", "type", "classid")
                if attributes.get(name)
            )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


class WebsiteDetector:
    def detect(self, html: str, source_url: str) -> list[TechnologyDetection]:
        evidence: list[Evidence] = []
        signals = _HTMLSignals()
        signals.feed(html)
        scripts = " ".join(signals.scripts).lower()
        links = " ".join(signals.links).lower()
        assets = f"{scripts} {links}"
        urls = " ".join(signals.urls).lower()
        markers = " ".join(signals.marker_values).lower()
        embedded = " ".join(signals.embedded_values).lower()

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

        jquery = re.search(r"jquery(?:[-./]|%2f)(\d+\.\d+(?:\.\d+)?)", scripts)
        if "jquery" in scripts:
            add("jQuery", "jQuery asset/signature in archived HTML", 75, jquery.group(1) if jquery else None)

        bootstrap = re.search(r"bootstrap(?:[-./]|@)(\d+\.\d+(?:\.\d+)?)", assets)
        if "bootstrap" in assets and (".css" in assets or ".js" in assets):
            add("Bootstrap", "Bootstrap asset in archived HTML", 80, bootstrap.group(1) if bootstrap else None)

        react = re.search(r"react(?:-dom)?(?:[-./@]|%2f)(\d+\.\d+(?:\.\d+)?)", scripts)
        if any(marker in scripts for marker in ("react.js", "react.min.js", "react-dom", "react@")) or "data-reactroot" in signals.attribute_names:
            add("React", "React asset/DOM marker in archived HTML", 80, react.group(1) if react else None)

        vue = re.search(r"vue(?:[-./@]|%2f)(\d+\.\d+(?:\.\d+)?)", scripts)
        vue_marker = any(name.startswith("data-v-") for name in signals.attribute_names)
        if any(marker in scripts for marker in ("vue.js", "vue.min.js", "vue@")) or vue_marker:
            add("Vue", "Vue asset/DOM marker in archived HTML", 80, vue.group(1) if vue else None)

        ng_versions = signals.attribute_values.get("ng-version", [])
        ng_version = ng_versions[0] if ng_versions else None
        if ng_version is not None:
            add("Angular", "Angular ng-version marker", 95, ng_version or None)
        elif "angular.js" in scripts or "angular.min.js" in scripts or "ng-app" in signals.attribute_names:
            angular = re.search(r"angular(?:[-./]|%2f)(\d+\.\d+(?:\.\d+)?)", scripts)
            add("AngularJS", "AngularJS asset/directive marker", 80, angular.group(1) if angular else None)

        if "/_next/" in assets or "__next_data__" in markers:
            add("Next.js", "Next.js _next/ or __NEXT_DATA__ marker", 95)

        if "cdn.tailwindcss.com" in assets or "tailwind.min.css" in links:
            add("Tailwind CSS", "Tailwind asset marker", 80)

        generators = " ".join(signals.meta_generators)
        wp = re.search(r"wordpress\s*([0-9]+(?:\.[0-9]+){1,2})?", generators, flags=re.IGNORECASE)
        if "wp-content/" in urls or "wp-includes/" in urls or wp:
            add("WordPress", "WordPress asset/generator marker", 90, wp.group(1) if wp and wp.group(1) else None)

        if ".swf" in embedded or "application/x-shockwave-flash" in embedded or "shockwaveflash" in embedded:
            add("Adobe Flash", "Flash object/SWF asset in archived HTML", 90)

        if "mootools" in scripts:
            version = self._asset_version(scripts, "mootools")
            add("MooTools", "MooTools asset marker", 85, version)
        if "prototype.js" in scripts or "prototype.min.js" in scripts:
            version = self._asset_version(scripts, "prototype")
            add("Prototype.js", "Prototype.js asset marker", 85, version)
        if "modernizr" in scripts:
            version = self._asset_version(scripts, "modernizr")
            add("Modernizr", "Modernizr asset marker", 80, version)
        if "require.js" in scripts or "require.min.js" in scripts or "requirejs" in scripts:
            version = self._asset_version(scripts, "require")
            add("RequireJS", "RequireJS asset marker", 80, version)
        if "alpinejs" in scripts or "alpine.js" in scripts:
            add("Alpine.js", "Alpine.js asset marker", 80, self._asset_version(scripts, "alpine"))
        if "__svelte" in markers or "/_app/immutable/" in assets:
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
