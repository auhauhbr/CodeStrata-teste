from __future__ import annotations

from .models import EventKind, Snapshot, TimelineEvent


def build_timeline(snapshots: list[Snapshot]) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    previous: dict[str, object] = {}

    for snapshot in snapshots:
        current = {item.name: item for item in snapshot.detections}
        previous_names = set(previous)
        current_names = set(current)

        for technology in sorted(current_names - previous_names):
            detection = current[technology]
            events.append(
                TimelineEvent(
                    kind=EventKind.INTRODUCED,
                    technology=technology,
                    at=snapshot.committed_at,
                    sha=snapshot.sha,
                    to_version=detection.version,
                )
            )

        for technology in sorted(previous_names - current_names):
            old = previous[technology]
            events.append(
                TimelineEvent(
                    kind=EventKind.REMOVED,
                    technology=technology,
                    at=snapshot.committed_at,
                    sha=snapshot.sha,
                    from_version=getattr(old, "version", None),
                )
            )

        for technology in sorted(previous_names & current_names):
            old_version = getattr(previous[technology], "version", None)
            new_version = current[technology].version
            if old_version and new_version and old_version != new_version:
                events.append(
                    TimelineEvent(
                        kind=EventKind.VERSION_CHANGED,
                        technology=technology,
                        at=snapshot.committed_at,
                        sha=snapshot.sha,
                        from_version=old_version,
                        to_version=new_version,
                    )
                )

        previous = current

    return events
