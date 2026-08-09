# Remote Log Analyzer

[![Tests](https://github.com/annamaulii/remote-log-analyzer/actions/workflows/tests.yml/badge.svg)](https://github.com/annamaulii/remote-log-analyzer/actions/workflows/tests.yml)

A Python command-line tool for filtering and summarizing application logs without loading an entire file into memory.

## Features

- Reads log files incrementally
- Filters entries by severity and relative time
- Continues after malformed lines and reports their line numbers
- Produces JSON and Markdown summaries
- Counts severities and repeated error messages
- Loads optional TOML configuration
- Runs as the installable `remote-log` command
- Tests Python 3.11 and 3.14 in GitHub Actions

## Log format

Each line must contain a timestamp, severity, and message:

```text
2026-08-09 10:01:00 ERROR Database failed
```

The expected timestamp format is `YYYY-MM-DD HH:MM:SS`. The message may contain spaces.

## Installation

```bash
git clone https://github.com/annamaulii/remote-log-analyzer.git
cd remote-log-analyzer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Python 3.11 or newer is required.

## Usage

Show all valid entries:

```bash
remote-log analyze examples/sample.log.example
```

Filter by severity:

```bash
remote-log analyze examples/sample.log.example --level error
```

Filter to the last 24 hours:

```bash
remote-log analyze app.log --since 24h
```

Use a configuration file:

```bash
remote-log analyze app.log --config remote-log.example.toml
```

Command-line options override configuration values.

Create a JSON summary:

```bash
remote-log summary examples/sample.log.example --format json
```

Create a Markdown summary:

```bash
remote-log summary examples/sample.log.example --format markdown
```

Save a report with standard shell redirection:

```bash
remote-log summary app.log --format json > report.json
```

Malformed-line warnings use standard error, so redirected report output remains valid.

## Configuration

```toml
[analyze]
level = "error"
since = "24h"
```

Supported settings:

| Setting | Meaning |
| --- | --- |
| `level` | Case-insensitive severity filter |
| `since` | Positive whole-hour duration such as `24h` |

Unknown sections, unknown options, and incorrectly typed values produce clear errors.

## Example summary

```json
{
  "severity_counts": {
    "ERROR": 2,
    "INFO": 1
  },
  "error_types": {
    "Database failed": 2
  }
}
```

Error types are grouped by exact message text.

## Architecture

```text
remote_log_analyzer/
├── cli.py       # command parsing, terminal output, and exit codes
├── config.py    # TOML loading and validation
└── core.py      # parsing, filtering, counting, and report formatting
```

The CLI translates user input into calls to the core. The core reads entries lazily with a generator, allowing processing cost to scale with the number of lines while avoiding a full-file list in memory.

## Testing

Run the complete suite:

```bash
pytest -v
```

The repository contains 31 test cases covering parsers, filters, malformed input, configuration, CLI behavior, reports, and edge cases.

## Security and privacy

Log files can contain credentials, personal data, or internal system details. Real `*.log` files, environment files, and private-key formats are ignored by Git. Only sanitized examples should be committed.

## Known limitations

- Only the documented whitespace-separated log format is supported.
- Timestamps do not include time-zone information.
- Relative durations support positive whole hours only.
- Error types use exact message matching.
- Configuration currently applies to the `analyze` command only.
- Summary memory use grows with the number of unique error messages.

## Roadmap

- Add more relative-duration units
- Support configurable log formats
- Add output-file options without shell redirection
- Add performance benchmarks for very large files

