from dataclasses import dataclass
from datetime import datetime


@dataclass
class LogEntry:
    timestamp: datetime
    severity: str
    message: str


def parse_log_line(line: str) -> LogEntry:
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
