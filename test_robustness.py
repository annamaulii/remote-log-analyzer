import json
from datetime import datetime
from pathlib import Path

import pytest

from remote_log_analyzer.cli import main
from remote_log_analyzer.core import iter_log_entries


def test_filters_combine(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 13:59:59 ERROR Too old\n"
        "2026-08-01 14:00:00 INFO Wrong level\n"
        "2026-08-01 14:00:00 ERROR Match\n",
        encoding="utf-8",
    )

    entries = list(
        iter_log_entries(
            log_path,
            severity="error",
            since=datetime(2026, 8, 1, 14, 0, 0),
        )
    )

    assert [entry.message for entry in entries] == ["Match"]


def test_empty_log_has_empty_json_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "empty.log"
    log_path.write_text("", encoding="utf-8")

    exit_code = main(["summary", str(log_path), "--format", "json"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert json.loads(captured.out) == {"severity_counts": {}, "error_types": {}}


def test_analyze_succeeds_with_no_matches(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("2026-08-01 14:00:00 INFO Started\n", encoding="utf-8")

    exit_code = main(["analyze", str(log_path), "--level", "error"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""


def test_multiple_malformed_lines_each_warn(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "bad first line\n"
        "2026-08-01 14:00:00 INFO Valid\n"
        "2026-99-01 14:00:00 ERROR Bad timestamp\n",
        encoding="utf-8",
    )

    entries = list(iter_log_entries(log_path))
    captured = capsys.readouterr()

    assert [entry.message for entry in entries] == ["Valid"]
    assert "Warning on line 1:" in captured.err
    assert "Warning on line 3:" in captured.err


def test_invalid_toml_returns_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("", encoding="utf-8")
    config_path = tmp_path / "invalid.toml"
    config_path.write_text("[analyze]\nlevel =", encoding="utf-8")

    exit_code = main(["analyze", str(log_path), "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.startswith("Error: ")


def test_missing_config_file_returns_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("", encoding="utf-8")
    config_path = tmp_path / "missing.toml"

    exit_code = main(["analyze", str(log_path), "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert str(config_path) in captured.err


def test_unknown_config_section_returns_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("", encoding="utf-8")
    config_path = tmp_path / "remote-log.toml"
    config_path.write_text("[summary]\n", encoding="utf-8")

    exit_code = main(["analyze", str(log_path), "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err == "Error: Unknown config section: summary\n"


def test_summary_normalizes_severity_case(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "2026-08-01 14:00:00 error Failed\n"
        "2026-08-01 14:01:00 ERROR Failed\n",
        encoding="utf-8",
    )

    exit_code = main(["summary", str(log_path), "--format", "json"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert json.loads(captured.out) == {
        "severity_counts": {"ERROR": 2},
        "error_types": {"Failed": 2},
    }
