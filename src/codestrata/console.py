from __future__ import annotations

from .models import ArchaeologyReport, EventKind, Snapshot


SYMBOLS = {
    EventKind.INTRODUCED: "+",
    EventKind.REMOVED: "-",
    EventKind.VERSION_CHANGED: "~",
}


def render_snapshot(snapshot: Snapshot) -> str:
    lines = [f"Snapshot {snapshot.committed_at.date().isoformat()}  {snapshot.sha[:10]}"]
    if not snapshot.detections:
        lines.append("  No technologies detected above the confidence threshold.")
        return "\n".join(lines)

    width = max(len(item.name) for item in snapshot.detections)
    for item in snapshot.detections:
        version = f"  {item.version}" if item.version else ""
        lines.append(f"  {item.name:<{width}}  {item.confidence:>3}%{version}")
    return "\n".join(lines)


def render_report(report: ArchaeologyReport) -> str:
    if report.metadata.get("mode") == "wayback":
        history = (
            f"Archive: {report.metadata.get('capture_count', 0)} captures found · "
            f"{len(report.snapshots)} snapshots analyzed · {len(report.events)} events"
        )
    else:
        history = (
            f"History: {report.metadata.get('commit_count', 0)} commits · "
            f"{len(report.snapshots)} snapshots · {len(report.events)} events"
        )
    lines = [
        "CodeStrata — software archaeology",
        f"Target: {report.repository}",
        history,
        "",
        "Timeline",
        "--------",
    ]
    if not report.events:
        lines.append("No technology changes detected.")
    for event in report.events:
        suffix = ""
        if event.kind is EventKind.VERSION_CHANGED:
            suffix = f" {event.from_version or '?'} -> {event.to_version or '?'}"
        elif event.to_version:
            suffix = f" {event.to_version}"
        lines.append(
            f"{event.at.date().isoformat()}  {SYMBOLS[event.kind]} "
            f"{event.technology}{suffix}  [{event.sha[:8]}]"
        )

    if report.snapshots:
        lines.extend(["", "Latest stratum", "--------------", render_snapshot(report.snapshots[-1])])
    return "\n".join(lines)
