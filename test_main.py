from datetime import datetime
from pathlib import Path

import pytest

from main import LogEntry, iter_log_entries, parse_log_line


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


def test_iter_log_entries_yields_valid_entries(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 14:35:22 INFO Application started\n"
        "2026-08-01 14:36:10 ERROR Database failed\n",
        encoding="utf-8",
    )

    entries = list(iter_log_entries(log_path))

    assert entries == [
        LogEntry(
            timestamp=datetime(2026, 8, 1, 14, 35, 22),
            severity="INFO",
            message="Application started",
        ),
        LogEntry(
            timestamp=datetime(2026, 8, 1, 14, 36, 10),
            severity="ERROR",
            message="Database failed",
        ),
    ]


def test_iter_log_entries_warns_and_continues(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 14:35:22 INFO Application started\n"
        "Database suddenly disappeared\n"
        "2026-08-01 14:36:10 ERROR Database failed\n",
        encoding="utf-8",
    )

    entries = list(iter_log_entries(log_path))
    captured = capsys.readouterr()

    assert [entry.severity for entry in entries] == ["INFO", "ERROR"]
    assert captured.out == ""
    assert captured.err == (
        "Warning on line 2: "
        "Expected date, time, severity, and message\n"
    )
