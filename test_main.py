import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from remote_log_analyzer.cli import main
from remote_log_analyzer.config import load_config
from remote_log_analyzer.core import (
    LogEntry,
    iter_log_entries,
    parse_duration,
    parse_log_line,
)


def test_parse_duration_in_hours() -> None:
    assert parse_duration("24h") == timedelta(hours=24)


def test_example_config_is_valid() -> None:
    config = load_config(Path(__file__).with_name("remote-log.example.toml"))

    assert config.level == "error"
    assert config.since == timedelta(hours=24)


@pytest.mark.parametrize("value", ["24", "hours", "-1h", "0h", "h"])
def test_parse_duration_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="Duration must be positive hours, such as 24h"):
        parse_duration(value)


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
        "Expected date, time, severity, and message; "
        "received: 'Database suddenly disappeared'\n"
    )


def test_iter_log_entries_filters_by_severity(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 14:35:22 INFO Application started\n"
        "2026-08-01 14:36:10 ERROR Database failed\n"
        "2026-08-01 14:37:05 WARNING Disk space is low\n"
        "2026-08-01 14:38:30 ERROR Request timed out\n",
        encoding="utf-8",
    )

    entries = list(iter_log_entries(log_path, severity="error"))

    assert [entry.severity for entry in entries] == ["ERROR", "ERROR"]


def test_iter_log_entries_filters_since_inclusively(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 13:59:59 INFO Before boundary\n"
        "2026-08-01 14:00:00 ERROR At boundary\n"
        "2026-08-01 14:00:01 WARNING After boundary\n",
        encoding="utf-8",
    )

    entries = list(
        iter_log_entries(log_path, since=datetime(2026, 8, 1, 14, 0, 0))
    )

    assert [entry.message for entry in entries] == ["At boundary", "After boundary"]


def test_main_analyzes_with_level_and_since(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 13:59:59 ERROR Too old\n"
        "2026-08-01 14:00:00 INFO Wrong level\n"
        "2026-08-01 14:00:00 ERROR At boundary\n",
        encoding="utf-8",
    )

    exit_code = main(
        ["analyze", str(log_path), "--level", "error", "--since", "24h"],
        now=datetime(2026, 8, 2, 14, 0, 0),
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "2026-08-01 14:00:00 ERROR At boundary\n"
    assert captured.err == ""


def test_main_reports_missing_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_path = tmp_path / "missing.log"

    exit_code = main(["analyze", str(missing_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.startswith("Error: ")
    assert str(missing_path) in captured.err


def test_main_summarizes_as_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 14:00:00 INFO Started\n"
        "2026-08-01 14:01:00 ERROR Database failed\n"
        "2026-08-01 14:02:00 ERROR Database failed\n",
        encoding="utf-8",
    )

    exit_code = main(["summary", str(log_path), "--format", "json"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert json.loads(captured.out) == {
        "severity_counts": {"ERROR": 2, "INFO": 1},
        "error_types": {"Database failed": 2},
    }


def test_main_summarizes_as_markdown(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 14:00:00 ERROR Disk | full\n",
        encoding="utf-8",
    )

    exit_code = main(["summary", str(log_path), "--format", "markdown"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# Log Summary" in captured.out
    assert "| ERROR | 1 |" in captured.out
    assert r"| Disk \| full | 1 |" in captured.out


def test_main_uses_analyze_config(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 13:59:59 ERROR Too old\n"
        "2026-08-01 14:00:00 INFO Wrong level\n"
        "2026-08-01 14:00:00 ERROR At boundary\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "remote-log.toml"
    config_path.write_text(
        '[analyze]\nlevel = "error"\nsince = "24h"\n',
        encoding="utf-8",
    )

    exit_code = main(
        ["analyze", str(log_path), "--config", str(config_path)],
        now=datetime(2026, 8, 2, 14, 0, 0),
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "2026-08-01 14:00:00 ERROR At boundary\n"


def test_cli_option_overrides_analyze_config(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 14:00:00 INFO Started\n"
        "2026-08-01 14:01:00 ERROR Failed\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "remote-log.toml"
    config_path.write_text('[analyze]\nlevel = "info"\n', encoding="utf-8")

    exit_code = main(
        [
            "analyze",
            str(log_path),
            "--config",
            str(config_path),
            "--level",
            "error",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "2026-08-01 14:01:00 ERROR Failed\n"


def test_main_rejects_unknown_config_option(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("", encoding="utf-8")
    config_path = tmp_path / "remote-log.toml"
    config_path.write_text('[analyze]\nlevle = "error"\n', encoding="utf-8")

    exit_code = main(["analyze", str(log_path), "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "Error: Unknown analyze option: levle\n"


@pytest.mark.parametrize(
    ("setting", "error_message"),
    [
        ("level = 10", "Config option 'analyze.level' must be text"),
        ("since = 24", "Config option 'analyze.since' must be text"),
    ],
)
def test_main_rejects_wrong_config_value_type(
    setting: str,
    error_message: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("", encoding="utf-8")
    config_path = tmp_path / "remote-log.toml"
    config_path.write_text(f"[analyze]\n{setting}\n", encoding="utf-8")

    exit_code = main(["analyze", str(log_path), "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err == f"Error: {error_message}\n"
