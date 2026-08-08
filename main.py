import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class LogEntry:
    timestamp: datetime
    severity: str
    message: str


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
