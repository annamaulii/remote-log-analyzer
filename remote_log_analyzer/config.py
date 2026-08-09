import tomllib
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from remote_log_analyzer.core import parse_duration


@dataclass(frozen=True)
class AnalyzeConfig:
    level: str | None = None
    since: timedelta | None = None


def load_config(path: Path) -> AnalyzeConfig:
    """Load and validate analyze settings from a TOML file."""
    with path.open("rb") as config_file:
        data = tomllib.load(config_file)

    unknown_sections = set(data) - {"analyze"}
    if unknown_sections:
        raise ValueError(f"Unknown config section: {sorted(unknown_sections)[0]}")

    analyze = data.get("analyze", {})
    if not isinstance(analyze, dict):
        raise ValueError("Config section 'analyze' must be a table")

    unknown_options = set(analyze) - {"level", "since"}
    if unknown_options:
        raise ValueError(f"Unknown analyze option: {sorted(unknown_options)[0]}")

    level = analyze.get("level")
    since = analyze.get("since")
    if level is not None and not isinstance(level, str):
        raise ValueError("Config option 'analyze.level' must be text")
    if since is not None and not isinstance(since, str):
        raise ValueError("Config option 'analyze.since' must be text")

    return AnalyzeConfig(
        level=level,
        since=parse_duration(since) if since is not None else None,
    )
