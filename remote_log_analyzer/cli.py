import argparse
import sys
from datetime import datetime
from pathlib import Path

from remote_log_analyzer.config import AnalyzeConfig, load_config
from remote_log_analyzer.core import (
    format_summary,
    iter_log_entries,
    parse_duration,
    summarize_log,
)


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    """Run the remote-log command-line interface."""
    parser = argparse.ArgumentParser(prog="remote-log")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="Filter log entries")
    analyze_parser.add_argument("path", type=Path)
    analyze_parser.add_argument("--level")
    analyze_parser.add_argument("--since", type=parse_duration)
    analyze_parser.add_argument("--config", type=Path)
    summary_parser = subparsers.add_parser("summary", help="Summarize log entries")
    summary_parser.add_argument("path", type=Path)
    summary_parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "analyze":
            config = load_config(args.config) if args.config else AnalyzeConfig()
            duration = args.since or config.since
            since = (now or datetime.now()) - duration if duration else None
            level = args.level or config.level
            for entry in iter_log_entries(args.path, severity=level, since=since):
                print(
                    f"{entry.timestamp:%Y-%m-%d %H:%M:%S} "
                    f"{entry.severity} {entry.message}"
                )
        else:
            summary = summarize_log(iter_log_entries(args.path))
            print(format_summary(summary, args.format))
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0
