from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyzer import Archaeologist
from .console import render_report, render_snapshot
from .detectors import default_detectors
from .exporters import write_html, write_json
from .git import GitError, open_repository
from .wayback import WaybackError
from .website_analyzer import WebsiteArchaeologist


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codestrata",
        description="Reconstruct technology timelines from Git history and archived websites.",
    )
    parser.add_argument("--version", action="version", version=f"CodeStrata {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze an entire repository history")
    analyze.add_argument("source", nargs="?", default=".", help="Local path or Git URL")
    analyze.add_argument("--granularity", choices=("year", "quarter", "month"), default="year")
    analyze.add_argument("--max-snapshots", type=int, default=24)
    analyze.add_argument("--min-confidence", type=int, default=40)
    analyze.add_argument("--json", dest="json_path", metavar="PATH", help="Write a JSON report")
    analyze.add_argument("--html", dest="html_path", metavar="PATH", help="Write a standalone HTML report")

    snapshot = sub.add_parser("snapshot", help="Inspect one commit/ref")
    snapshot.add_argument("source", nargs="?", default=".", help="Local path or Git URL")
    snapshot.add_argument("--ref", default="HEAD", help="Commit, tag, or branch to inspect")
    snapshot.add_argument("--min-confidence", type=int, default=40)

    web = sub.add_parser("web", help="Analyze archived versions of a public website")
    web.add_argument("url", help="Public website URL recorded by the Wayback Machine")
    web.add_argument("--from", dest="from_year", type=int, metavar="YEAR")
    web.add_argument("--to", dest="to_year", type=int, metavar="YEAR")
    web.add_argument("--granularity", choices=("year", "quarter", "month"), default="year")
    web.add_argument("--max-snapshots", type=int, default=24)
    web.add_argument("--min-confidence", type=int, default=40)
    web.add_argument("--json", dest="json_path", metavar="PATH", help="Write a JSON report")
    web.add_argument("--html", dest="html_path", metavar="PATH", help="Write a standalone HTML report")

    sub.add_parser("detectors", help="List enabled Git repository detector modules")
    return parser


def _validate_confidence(value: int) -> None:
    if not 0 <= value <= 100:
        raise ValueError("--min-confidence must be between 0 and 100")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "detectors":
            print("\n".join(detector.name for detector in default_detectors()))
            return 0

        _validate_confidence(args.min_confidence)

        if args.command == "web":
            if args.from_year and args.to_year and args.from_year > args.to_year:
                raise ValueError("--from cannot be later than --to")
            report = WebsiteArchaeologist(min_confidence=args.min_confidence).analyze(
                args.url,
                granularity=args.granularity,
                max_snapshots=args.max_snapshots,
                from_year=args.from_year,
                to_year=args.to_year,
            )
            print(render_report(report))
            if args.json_path:
                path = write_json(report, args.json_path)
                print(f"\nJSON report: {path}")
            if args.html_path:
                path = write_html(report, args.html_path)
                print(f"HTML report: {path}")
            return 0

        archaeologist = Archaeologist(min_confidence=args.min_confidence)
        with open_repository(args.source) as repository:
            if args.command == "snapshot":
                print(render_snapshot(archaeologist.inspect(repository, args.ref)))
                return 0

            report = archaeologist.analyze(
                repository,
                granularity=args.granularity,
                max_snapshots=args.max_snapshots,
            )
            print(render_report(report))
            if args.json_path:
                path = write_json(report, args.json_path)
                print(f"\nJSON report: {path}")
            if args.html_path:
                path = write_html(report, args.html_path)
                print(f"HTML report: {path}")
            return 0
    except (GitError, WaybackError, ValueError) as exc:
        print(f"codestrata: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("codestrata: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
