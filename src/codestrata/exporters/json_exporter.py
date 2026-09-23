from __future__ import annotations

import json
from pathlib import Path

from ..models import ArchaeologyReport


def write_json(report: ArchaeologyReport, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
