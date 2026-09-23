from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class WaybackError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class WaybackSnapshot:
    timestamp: str
    original_url: str
    digest: str

    @property
    def captured_at(self) -> datetime:
        return datetime.strptime(self.timestamp, "%Y%m%d%H%M%S").replace(tzinfo=UTC)

    @property
    def archive_url(self) -> str:
        return f"https://web.archive.org/web/{self.timestamp}id_/{self.original_url}"


class WaybackClient:
    CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
    USER_AGENT = "CodeStrata/0.1 (+https://github.com/JeffersonSantosKn/CodeStrata)"

    def __init__(self, *, timeout: float = 20.0):
        self.timeout = timeout

    def _read(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": self.USER_AGENT})
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - explicit user target
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise WaybackError(f"Wayback request failed: {exc}") from exc

    def list_snapshots(
        self,
        url: str,
        *,
        from_year: int | None = None,
        to_year: int | None = None,
        limit: int = 5000,
    ) -> list[WaybackSnapshot]:
        params: list[tuple[str, str]] = [
            ("url", url),
            ("output", "json"),
            ("fl", "timestamp,original,digest,statuscode,mimetype"),
            ("filter", "statuscode:200"),
            ("filter", "mimetype:text/html"),
            ("collapse", "digest"),
            ("limit", str(limit)),
        ]
        if from_year is not None:
            params.append(("from", str(from_year)))
        if to_year is not None:
            params.append(("to", str(to_year)))

        endpoint = f"{self.CDX_ENDPOINT}?{urlencode(params)}"
        raw = self._read(endpoint)
        try:
            rows = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WaybackError("Wayback CDX returned an invalid response") from exc
        if not isinstance(rows, list) or len(rows) < 2:
            return []

        snapshots: list[WaybackSnapshot] = []
        for row in rows[1:]:
            if not isinstance(row, list) or len(row) < 3:
                continue
            timestamp, original, digest = row[:3]
            if not str(timestamp).isdigit() or len(str(timestamp)) != 14:
                continue
            snapshots.append(WaybackSnapshot(str(timestamp), str(original), str(digest)))
        return snapshots

    def fetch_html(self, snapshot: WaybackSnapshot, *, max_bytes: int = 2_000_000) -> str:
        raw = self._read(snapshot.archive_url)
        if len(raw) > max_bytes:
            raw = raw[:max_bytes]
        return raw.decode("utf-8", errors="replace")
