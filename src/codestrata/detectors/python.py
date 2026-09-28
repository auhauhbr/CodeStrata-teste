from __future__ import annotations

import re
import tomllib
from pathlib import PurePosixPath
from typing import Any

from ..models import Evidence, EvidenceKind
from .base import DetectionContext


PYTHON_TECHNOLOGIES = {
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
}

REQ_PATTERN = re.compile(
    r"^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?:\[[A-Za-z0-9._,-]+\])?\s*"
    r"((?:(?:===|~=|==|!=|<=|>=|<|>)\s*[^,;\s]+"
    r"(?:\s*,\s*(?:===|~=|==|!=|<=|>=|<|>)\s*[^,;\s]+)*))?"
    r"\s*(?:;\s*.+)?$"
)


def _normalize_package(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_dependency(requirement: str) -> tuple[str, str | None] | None:
    line = re.sub(r"\s+#.*$", "", requirement).strip()
    if not line or line.startswith("#"):
        return None
    match = REQ_PATTERN.fullmatch(line)
    if not match:
        return None
    return _normalize_package(match.group(1)), (match.group(2) or "").replace(" ", "") or None


def _toml_document(content: str) -> dict[str, Any] | None:
    try:
        return tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return None


def _version_value(value: object) -> str | None:
    if isinstance(value, str):
        return value if value != "*" else None
    if isinstance(value, dict):
        version = value.get("version")
        return version if isinstance(version, str) and version != "*" else None
    return None


def _add_table_dependencies(
    dependencies: dict[str, str | None],
    table: object,
) -> None:
    if not isinstance(table, dict):
        return
    for name, value in table.items():
        normalized = _normalize_package(str(name))
        if normalized in PYTHON_TECHNOLOGIES:
            dependencies.setdefault(normalized, _version_value(value))


def _pyproject_dependencies(content: str) -> dict[str, str | None]:
    document = _toml_document(content)
    if document is None:
        return {}

    dependencies: dict[str, str | None] = {}
    project = document.get("project")
    if isinstance(project, dict):
        requirement_groups = [project.get("dependencies")]
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            requirement_groups.extend(optional.values())
        for group in requirement_groups:
            if not isinstance(group, list):
                continue
            for requirement in group:
                if not isinstance(requirement, str):
                    continue
                dependency = _requirement_dependency(requirement)
                if dependency and dependency[0] in PYTHON_TECHNOLOGIES:
                    dependencies.setdefault(*dependency)

    tool = document.get("tool")
    poetry = tool.get("poetry") if isinstance(tool, dict) else None
    if isinstance(poetry, dict):
        _add_table_dependencies(dependencies, poetry.get("dependencies"))
        groups = poetry.get("group")
        if isinstance(groups, dict):
            for group in groups.values():
                if isinstance(group, dict):
                    _add_table_dependencies(dependencies, group.get("dependencies"))
    return dependencies


def _pipfile_dependencies(content: str) -> dict[str, str | None]:
    document = _toml_document(content)
    if document is None:
        return {}
    dependencies: dict[str, str | None] = {}
    _add_table_dependencies(dependencies, document.get("packages"))
    _add_table_dependencies(dependencies, document.get("dev-packages"))
    return dependencies


def _requirements_dependencies(content: str) -> dict[str, str | None]:
    dependencies: dict[str, str | None] = {}
    for line in content.splitlines():
        dependency = _requirement_dependency(line)
        if dependency and dependency[0] in PYTHON_TECHNOLOGIES:
            dependencies.setdefault(*dependency)
    return dependencies


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
            filename = PurePosixPath(path).name.lower()
            if filename == "requirements.txt":
                dependencies = _requirements_dependencies(content)
            elif filename == "pyproject.toml":
                dependencies = _pyproject_dependencies(content)
            else:
                dependencies = _pipfile_dependencies(content)
            for package, version in dependencies.items():
                evidence.append(
                    Evidence(
                        PYTHON_TECHNOLOGIES[package],
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
