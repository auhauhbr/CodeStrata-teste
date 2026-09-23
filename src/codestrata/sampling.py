from __future__ import annotations

from collections import OrderedDict
from typing import Literal

from .git import Commit

Granularity = Literal["year", "quarter", "month"]


def _bucket(commit: Commit, granularity: Granularity) -> str:
    date = commit.committed_at
    if granularity == "year":
        return f"{date.year}"
    if granularity == "quarter":
        quarter = ((date.month - 1) // 3) + 1
        return f"{date.year}-Q{quarter}"
    if granularity == "month":
        return f"{date.year}-{date.month:02d}"
    raise ValueError(f"Unsupported granularity: {granularity}")


def sample_commits(
    commits: list[Commit],
    *,
    granularity: Granularity = "year",
    max_snapshots: int | None = 24,
) -> list[Commit]:
    """Pick representative commits while always preserving the latest state.

    The first commit in each time bucket is selected because it makes technology
    introductions easier to bound. The repository's latest commit is appended
    when it is not already represented.
    """

    if not commits:
        return []

    buckets: OrderedDict[str, Commit] = OrderedDict()
    for commit in commits:
        buckets.setdefault(_bucket(commit, granularity), commit)

    sampled = list(buckets.values())
    latest = commits[-1]
    if sampled[-1].sha != latest.sha:
        sampled.append(latest)

    if max_snapshots is not None and max_snapshots > 0 and len(sampled) > max_snapshots:
        if max_snapshots == 1:
            return [latest]
        # Keep the endpoints and spread the remaining picks across the range.
        span = len(sampled) - 1
        indexes = {round(i * span / (max_snapshots - 1)) for i in range(max_snapshots)}
        sampled = [commit for idx, commit in enumerate(sampled) if idx in indexes]
        if sampled[-1].sha != latest.sha:
            sampled[-1] = latest

    return sampled
