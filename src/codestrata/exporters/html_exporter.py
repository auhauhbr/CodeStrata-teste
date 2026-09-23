from __future__ import annotations

from html import escape
from pathlib import Path

from ..models import ArchaeologyReport, EventKind


def _event_label(kind: EventKind) -> str:
    return {
        EventKind.INTRODUCED: "first observed",
        EventKind.REMOVED: "last observed",
        EventKind.VERSION_CHANGED: "version change",
    }[kind]


def _event_class(kind: EventKind) -> str:
    return {
        EventKind.INTRODUCED: "introduced",
        EventKind.REMOVED: "removed",
        EventKind.VERSION_CHANGED: "changed",
    }[kind]


def render_html(report: ArchaeologyReport) -> str:
    technologies = sorted({d.name for snapshot in report.snapshots for d in snapshot.detections})
    is_wayback = report.metadata.get("mode") == "wayback"
    source_description = "archived web history" if is_wayback else "Git history"
    if is_wayback:
        history_meta = f"{report.metadata.get('capture_count', 0)} archive captures"
    else:
        history_meta = f"{report.metadata.get('commit_count', 0)} commits"

    technology_links = " · ".join(
        f"<a href='#evidence'>{escape(name)}</a>" for name in technologies
    ) or "No technologies detected"

    event_rows: list[str] = []
    for event in report.events:
        if event.kind is EventKind.VERSION_CHANGED:
            version = f"{escape(event.from_version or '?')} → {escape(event.to_version or '?')}"
        else:
            version = escape(event.to_version or "—")
        event_rows.append(
            "<tr>"
            f"<td>{event.at.date().isoformat()}</td>"
            f"<td><a href='#evidence'>{escape(event.technology)}</a></td>"
            f"<td><span class='status {_event_class(event.kind)}'>{escape(_event_label(event.kind))}</span></td>"
            f"<td>{version}</td>"
            "</tr>"
        )

    snapshot_sections: list[str] = []
    for snapshot in report.snapshots:
        rows: list[str] = []
        for detection in snapshot.detections:
            evidence_items = "".join(
                "<li>"
                f"<code>{escape(item.path)}</code>"
                f"<span>{escape(item.detail)}</span>"
                f"<small>+{item.weight}</small>"
                "</li>"
                for item in detection.evidence[:5]
            )
            version = escape(detection.version or "—")
            rows.append(
                "<details class='detection'>"
                "<summary>"
                f"<span class='tech-name'>{escape(detection.name)}</span>"
                f"<span>{version}</span>"
                f"<span>{escape(detection.category.replace('_', ' '))}</span>"
                f"<span>{detection.confidence}%</span>"
                "</summary>"
                f"<ul>{evidence_items or '<li><span>No stored evidence excerpt.</span></li>'}</ul>"
                "</details>"
            )
        snapshot_sections.append(
            "<section class='snapshot'>"
            "<div class='snapshot-title'>"
            f"<strong>{snapshot.committed_at.date().isoformat()}</strong>"
            f"<span>{len(snapshot.detections)} {'technology' if len(snapshot.detections) == 1 else 'technologies'}</span>"
            f"<details class='technical-ref'><summary>technical reference</summary><code>{escape(snapshot.sha[:10])}</code></details>"
            "</div>"
            "<div class='detection-head'>"
            "<span>Technology</span><span>Version</span><span>Category</span><span>Confidence</span>"
            "</div>"
            + "".join(rows)
            + "</section>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="software archaeology report">
<title>{escape(report.repository)} · technology history</title>
<style>
:root{{--page:#efeee8;--surface:#fffefa;--text:#2b2b2b;--muted:#66645f;--link:#003399;--visited:#663399;--line:#c7c5bc;--soft-line:#dfddd4;--bar:#e6e9ee;--bar-2:#f0f0ec;--green:#3f6844;--red:#855050;--amber:#75612f}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--page);color:var(--text);font:12px/1.4 Verdana,Arial,Helvetica,sans-serif}}
a{{color:var(--link);text-decoration:underline}}
a:hover{{color:#000066}}
a:visited{{color:var(--visited)}}
.utility{{border-bottom:1px solid #b9b7ae;background:#deddd7}}
.utility-inner{{width:min(1000px,98vw);margin:0 auto;padding:4px 4px;color:#5f5d58;font-size:11px;display:flex;justify-content:space-between;gap:16px}}
.utility nav{{display:flex;gap:13px;flex-wrap:wrap}}
.page{{width:min(1000px,98vw);margin:0 auto;background:var(--surface);border-left:1px solid #cbc9c0;border-right:1px solid #cbc9c0;min-height:100vh}}
.searchbar{{display:flex;gap:6px;align-items:center;padding:7px 10px;border-bottom:1px solid var(--line);background:#f7f6f1}}
.searchbar label{{font-weight:bold;color:#444}}
.searchbar input{{flex:1;min-width:0;height:24px;border:1px solid #999;background:#fff;padding:2px 5px;font:12px Verdana,Arial,Helvetica,sans-serif;color:#333}}
.searchbar button{{height:24px;border:1px solid #888;background:#e7e7e3;padding:0 11px;color:#222;font:11px Verdana,Arial,Helvetica,sans-serif;font-weight:bold}}
.navline{{padding:5px 10px;border-bottom:1px solid var(--line);font-size:11px;background:#eeeef0}}
.navline a{{margin-right:13px}}
.content{{padding:11px 12px 30px}}
.breadcrumb{{color:var(--muted);font-size:12px;margin-bottom:7px}}
h1{{font:normal 20px/1.2 Georgia,"Times New Roman",serif;margin:0 0 4px;color:#262626}}
.subtitle{{color:#55534e;margin:0 0 9px}}
.summaryline{{padding:6px 0 9px;border-bottom:1px solid var(--line);color:#666;font-size:12px}}
.summaryline span{{margin-right:18px}}
.columns{{display:grid;grid-template-columns:minmax(0,1fr) 220px;gap:16px;margin-top:11px}}
.section{{margin:0 0 15px}}
.section-title{{font-size:11px;font-weight:bold;background:var(--bar);border-top:1px solid #aeb7c1;border-bottom:1px solid #c4c8cc;padding:3px 5px;color:#263d59}}
.section-body{{padding:5px 1px}}
.index{{line-height:1.75;padding:0 5px}}
.help{{color:#666;margin:0}}
.sidebar .section-title{{background:#f1f1ee;border-top-color:#c7c7c0;color:#4c4c4c}}
.sidebar .section-body{{padding:7px}}
.sidebar ul{{margin:0;padding-left:17px}}
.sidebar li{{margin:3px 0}}
table{{width:100%;border-collapse:collapse;font-size:11px}}
th{{text-align:left;background:var(--bar-2);border:1px solid #c8c7c0;padding:4px 5px;color:#444;font-weight:bold}}
td{{border:1px solid var(--soft-line);padding:4px 5px;vertical-align:top}}
tr:hover td{{background:#fafbfd}}
.status{{white-space:nowrap}}
.status.introduced{{color:var(--green)}}
.status.removed{{color:var(--red)}}
.status.changed{{color:var(--amber)}}
code{{font:12px Consolas,"Courier New",monospace;color:#444;background:transparent}}
.snapshot{{margin-bottom:14px;border-bottom:1px solid var(--line)}}
.snapshot-title{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;background:var(--bar);border-top:1px solid #aeb7c1;border-bottom:1px solid #c4c8cc;padding:3px 5px;color:#555}}
.snapshot-title strong{{color:#35485d}}
.technical-ref{{margin-left:auto;display:flex;align-items:center;gap:6px}}
.technical-ref>summary{{display:inline;padding:0;color:var(--link);text-decoration:underline;font-size:10px;cursor:pointer}}
.technical-ref>summary:before{{content:none}}
.technical-ref[open]>summary:before{{content:none}}
.technical-ref>code{{margin-left:5px}}
.detection-head,summary{{display:grid;grid-template-columns:minmax(180px,1.5fr) minmax(100px,.8fr) minmax(100px,.8fr) 85px;gap:8px}}
.detection-head{{padding:4px 5px 3px;background:#f8f8f4;color:#686761;font-size:10px;border-bottom:1px solid var(--soft-line)}}
.detection{{border-bottom:1px solid var(--soft-line)}}
.detection:last-child{{border-bottom:0}}
summary{{padding:5px;cursor:pointer;list-style:none;align-items:center}}
summary::-webkit-details-marker{{display:none}}
summary:before{{content:"+";position:absolute;margin-left:-11px;color:#777}}
.detection[open] summary:before{{content:"−"}}
.tech-name{{color:var(--link);font-weight:bold}}
.detection ul{{margin:0;padding:3px 5px 7px 18px;background:#fbfbf8;list-style:none}}
.detection li{{display:grid;grid-template-columns:minmax(150px,220px) minmax(0,1fr) 40px;gap:10px;padding:3px 0;color:#5a5a5a}}
.detection li small{{text-align:right;color:#777}}
.note{{border-top:1px solid var(--line);padding-top:6px;color:#66645f;font-size:11px}}
footer{{border-top:1px solid var(--line);padding:8px 12px 20px;color:#75736d;font-size:10px;background:#f6f5f0}}
@media(max-width:760px){{
  .page{{width:100%;border-left:0;border-right:0}}
  .utility-inner{{width:100%;padding:4px 8px;display:block}}
  .utility nav{{margin-top:3px;gap:10px}}
  .content{{padding:9px 8px 24px}}
  .columns{{grid-template-columns:1fr;gap:8px}}
  .sidebar{{order:2}}
  .searchbar{{padding:6px 8px}}
  .searchbar label{{display:none}}
  .navline{{padding:5px 8px;white-space:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch}}
  .navline a{{display:inline-block;margin-right:12px}}
  .summaryline{{line-height:1.7}}
  .summaryline span{{display:inline-block;margin-right:10px}}
  .section{{margin-bottom:12px}}
  .table-scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch;border-right:1px solid var(--soft-line)}}
  .table-scroll table{{min-width:560px}}
  .detection-head{{display:none}}
  summary{{grid-template-columns:minmax(0,1fr) auto;gap:8px}}
  summary span:nth-child(2),summary span:nth-child(3){{display:none}}
  .detection li{{grid-template-columns:1fr;gap:2px;padding:5px 0}}
  .detection li small{{text-align:left}}
  .snapshot-title{{gap:8px}}
}}
@media(max-width:420px){{
  body{{font-size:11px}}
  h1{{font-size:18px}}
  .utility nav a:nth-child(4){{display:none}}
  .searchbar button{{padding:0 8px}}
  .section-title{{font-size:10px}}
  .snapshot-title{{display:grid;grid-template-columns:1fr auto}}
  .technical-ref{{grid-column:1/-1}}
}}
</style>
</head>
<body>
<div class="utility">
  <div class="utility-inner">
    <span>Software history report</span>
    <nav><a href="#summary">Summary</a><a href="#timeline">Timeline</a><a href="#evidence">Evidence</a><a href="#about">About this report</a></nav>
  </div>
</div>
<div class="page">
  <form class="searchbar" onsubmit="return false">
    <label for="target">Target</label>
    <input id="target" value="{escape(report.repository)}" readonly>
    <button type="button">History</button>
  </form>
  <div class="navline">
    <a href="#summary">Overview</a>
    <a href="#timeline">Technology changes</a>
    <a href="#evidence">Snapshots</a>
    <a href="#evidence">Detection evidence</a>
  </div>
  <main class="content">
    <div class="breadcrumb">Analysis &gt; {escape(report.repository)}</div>
    <h1>Technology history: {escape(report.repository)}</h1>
    <p class="subtitle">Technologies reconstructed from {source_description}. Detections are based on inspectable evidence rather than execution of the target.</p>
    <div class="summaryline" id="summary">
      <span>{history_meta}</span>
      <span>{len(report.snapshots)} snapshots</span>
      <span>{len(report.events)} changes</span>
      <span>Generated {report.generated_at.date().isoformat()}</span>
    </div>

    <div class="columns">
      <div>
        <section class="section">
          <div class="section-title">Technology index</div>
          <div class="section-body index">{technology_links}</div>
        </section>

        <section class="section" id="timeline">
          <div class="section-title">Historical timeline</div>
          <div class="section-body">
            <div class="table-scroll">
              <table>
                <thead><tr><th>Date</th><th>Technology</th><th>Observation</th><th>Version</th></tr></thead>
                <tbody>{''.join(event_rows) or '<tr><td colspan="4">No technology changes detected.</td></tr>'}</tbody>
              </table>
            </div>
          </div>
        </section>

        <section class="section" id="evidence">
          <div class="section-title">Snapshot evidence</div>
          <div class="section-body">
            {''.join(snapshot_sections) or '<p>No snapshots available.</p>'}
          </div>
        </section>
      </div>

      <aside class="sidebar">
        <section class="section">
          <div class="section-title">Report information</div>
          <div class="section-body">
            <ul>
              <li>Source: {escape(source_description)}</li>
              <li>Target: {escape(report.repository)}</li>
              <li>Snapshots: {len(report.snapshots)}</li>
              <li>Changes: {len(report.events)}</li>
            </ul>
          </div>
        </section>
        <section class="section">
          <div class="section-title">How to read</div>
          <div class="section-body">
            <p class="help">Open any technology row to inspect the files, manifests, configuration entries, or archived assets that support the detection.</p>
          </div>
        </section>
        <section class="section" id="about">
          <div class="section-title">Method</div>
          <div class="section-body">
            <p class="help">Confidence is derived from weighted evidence. Hidden server-side technologies are not inferred from archived pages when no public evidence exists.</p>
          </div>
        </section>
      </aside>
    </div>
    <p class="note">This report is a historical reconstruction. Absence of evidence in a sampled snapshot does not necessarily prove that a technology was absent from the project.</p>
  </main>
  <footer>Generated by CodeStrata · software archaeology</footer>
</div>
</body>
</html>"""


def write_html(report: ArchaeologyReport, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(report), encoding="utf-8")
    return path
