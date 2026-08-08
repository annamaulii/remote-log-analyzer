import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class LogEntry:
    timestamp: datetime
    severity: str
    message: str


def parse_log_line(line: str) -> LogEntry:
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


def iter_log_entries(path: Path) -> Iterator[LogEntry]:
    with path.open(encoding="utf-8") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            try:
                yield parse_log_line(line)
            except ValueError as error:
                malformed_line = line.rstrip("\r\n")
                print(
                    f"Warning on line {line_number}: {error}; "
                    f"received: {malformed_line!r}",
                    file=sys.stderr,
                )
