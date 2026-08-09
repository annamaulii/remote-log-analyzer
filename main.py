import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class LogEntry:
    timestamp: datetime
    severity: str
    message: str


@dataclass
class LogSummary:
    severity_counts: Counter[str]
    error_types: Counter[str]


def parse_duration(value: str) -> timedelta:
    """Convert text such as 24h into a positive duration."""
    match = re.fullmatch(r"(\d+)h", value)
    if not match:
        raise ValueError("Duration must be positive hours, such as 24h")

    hours = int(match.group(1))
    if hours <= 0:
        raise ValueError("Duration must be positive hours, such as 24h")

    return timedelta(hours=hours)


def parse_log_line(line: str) -> LogEntry:
    """Convert one log line into a structured log entry."""
    line = line.rstrip("\r\n")
    parts = line.split(maxsplit=3)
    if len(parts) != 4:
        raise ValueError("Expected date, time, severity, and message")

    timestamp_text = f"{parts[0]} {parts[1]}"
    try:
        timestamp = datetime.strptime(timestamp_text, "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise ValueError(f"Invalid timestamp: {timestamp_text}") from error

    return LogEntry(
        timestamp=timestamp,
        severity=parts[2],
        message=parts[3],
    )


def iter_log_entries(
    path: Path,
    severity: str | None = None,
    since: datetime | None = None,
) -> Iterator[LogEntry]:
    """Yield valid log entries that match the optional filters."""
    with path.open(encoding="utf-8") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            try:
                entry = parse_log_line(line)
                matches_severity = (
                    severity is None or entry.severity.casefold() == severity.casefold()
                )
                if matches_severity and (since is None or entry.timestamp >= since):
                    yield entry
            except ValueError as error:
                malformed_line = line.rstrip("\r\n")
                print(
                    f"Warning on line {line_number}: {error}; "
                    f"received: {malformed_line!r}",
                    file=sys.stderr,
                )


def summarize_log(entries: Iterable[LogEntry]) -> LogSummary:
    """Count entries by severity and repeated error message."""
    severity_counts: Counter[str] = Counter()
    error_types: Counter[str] = Counter()
    for entry in entries:
        severity = entry.severity.upper()
        severity_counts[severity] += 1
        if severity == "ERROR":
            error_types[entry.message] += 1
    return LogSummary(severity_counts=severity_counts, error_types=error_types)


def format_summary(summary: LogSummary, output_format: str) -> str:
    """Format a log summary as Markdown or JSON."""
    data = {
        "severity_counts": dict(sorted(summary.severity_counts.items())),
        "error_types": dict(sorted(summary.error_types.items())),
    }
    if output_format == "json":
        return json.dumps(data, indent=2)

    lines = [
        "# Log Summary",
        "",
        "## Severity Counts",
        "",
        "| Severity | Count |",
        "| --- | ---: |",
    ]
    lines.extend(
        "| {} | {} |".format(name.replace("|", r"\|"), count)
        for name, count in data["severity_counts"].items()
    )
    lines.extend(
        [
            "",
            "## Error Types",
            "",
            "| Message | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(
        "| {} | {} |".format(name.replace("|", r"\|"), count)
        for name, count in data["error_types"].items()
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    """Run the remote-log command-line interface."""
    parser = argparse.ArgumentParser(prog="remote-log")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="Filter log entries")
    analyze_parser.add_argument("path", type=Path)
    analyze_parser.add_argument("--level")
    analyze_parser.add_argument("--since", type=parse_duration)
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
            since = (now or datetime.now()) - args.since if args.since else None
            for entry in iter_log_entries(args.path, severity=args.level, since=since):
                print(
                    f"{entry.timestamp:%Y-%m-%d %H:%M:%S} "
                    f"{entry.severity} {entry.message}"
                )
        else:
            summary = summarize_log(iter_log_entries(args.path))
            print(format_summary(summary, args.format))
    except OSError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
