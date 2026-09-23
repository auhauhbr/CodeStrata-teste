from __future__ import annotations

from collections import OrderedDict

from .sampling import Granularity
from .wayback import WaybackSnapshot


def _bucket(snapshot: WaybackSnapshot, granularity: Granularity) -> str:
    date = snapshot.captured_at
    if granularity == "year":
        return str(date.year)
    if granularity == "quarter":
        return f"{date.year}-Q{((date.month - 1) // 3) + 1}"
    if granularity == "month":
        return f"{date.year}-{date.month:02d}"
    raise ValueError(f"Unsupported granularity: {granularity}")


def sample_wayback_snapshots(
    snapshots: list[WaybackSnapshot],
    *,
    granularity: Granularity = "year",
    max_snapshots: int = 24,
) -> list[WaybackSnapshot]:
    if not snapshots:
        return []

    ordered = sorted(snapshots, key=lambda item: item.timestamp)
    buckets: OrderedDict[str, WaybackSnapshot] = OrderedDict()
    for snapshot in ordered:
        buckets.setdefault(_bucket(snapshot, granularity), snapshot)

    sampled = list(buckets.values())
    latest = ordered[-1]
    if sampled[-1].timestamp != latest.timestamp:
        sampled.append(latest)

    if max_snapshots > 0 and len(sampled) > max_snapshots:
        if max_snapshots == 1:
            return [latest]
        span = len(sampled) - 1
        indexes = {round(index * span / (max_snapshots - 1)) for index in range(max_snapshots)}
        sampled = [item for index, item in enumerate(sampled) if index in indexes]
        if sampled[-1].timestamp != latest.timestamp:
            sampled[-1] = latest

    return sampled
