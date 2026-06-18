# Changelog

### Changed

- **`s3 analyze`**: split into `by-level` and `by-time` subcommands.
  - `by-time` groups object sizes by day, with optional `--prefix` filter.

### Added
- **`s3 analyze`** command: analyze directory sizes by depth level from an S3
  object listing (`--input`). Uses DuckDB, prints TOP 10 + others via Rich.
- **`s3 ls`** command: recursively list S3 objects as JSON Lines.
  - Accepts `--bucket`/`--prefix` or `s3://bucket/prefix` URI.
  - `--output` with `.zst` extension compresses via zstandard.
  - Stdout truncated at 100 lines unless piped.
- **`tndiagnose`** top-level group: includes `kafka` and `s3` subcommands.
- Dependencies: `boto3`, `duckdb`, `zstandard`.

# 0.1.0
## 2026-06-18

### Added

- **`tndiagnose`** entry point: `uv run tndiagnose` (delegates to `kafka` CLI).
- **`kafka`** CLI group with subcommands:
  - `kafka list-topics` — export all topic configurations to CSV (`--config`, `--output`).
  - `kafka list-partitions` — per-partition offsets, delta, and message
    timestamps (`--topic`, `--config`, `--output`, `--concurrent`).
  - `list-partitions` `ratio` column — per-partition message share (`delta / sum(delta)`).
  - Pretty-printed table via `rich` when `--output` is omitted.
  - `-h` short flag equivalent to `--help`.
- **`internal/kafka/`** package:
  - `kafkautils.py` — `load_properties()`, `fetch_topic_configs()`,
    `fetch_partition_info()` with concurrent `ThreadPoolExecutor` support.
  - Muted librdkafka stderr logs by default (`debug=""`, `log_level=0`);
    overridable via consumer properties.
- Dependencies: `click`, `confluent-kafka`, `rich`.
