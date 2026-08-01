from datetime import datetime

import pytest

from main import LogEntry, parse_log_line


def test_parse_valid_log_line() -> None:
    line = "2026-08-01 14:35:22 WARNING Disk space is low"

    result = parse_log_line(line)

    expected = LogEntry(
        timestamp=datetime(2026, 8, 1, 14, 35, 22),
        severity="WARNING",
        message="Disk space is low",
    )

    assert result == expected


def test_parse_log_line_with_missing_fields() -> None:
    line = "Database suddenly disappeared"

    with pytest.raises(
        ValueError,
        match="Expected date, time, severity, and message",
    ):
        parse_log_line(line)


def test_parse_log_line_with_invalid_timestamp() -> None:
    line = "2026-99-01 14:35:22 ERROR Bad date"

    with pytest.raises(
        ValueError,
        match=r"^Invalid timestamp: 2026-99-01 14:35:22$",
    ):
        parse_log_line(line)
