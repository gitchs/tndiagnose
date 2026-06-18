# Changelog

# 0.1.0
## 2026-06-18

### Added

- **`tndiagnose`** entry point: `uv run tndiagnose` (delegates to `kafka` CLI).
- **`kafka`** CLI group with subcommands:
  - `kafka list-topics` — export all topic configurations to CSV (`--config`, `--output`).
  - `kafka list-partitions` — per-partition offsets, message count, and latest
    message timestamp (`--topic`, `--config`, `--output`, `--concurrent`).
  - Pretty-printed table via `rich` when `--output` is omitted.
  - `-h` short flag equivalent to `--help`.
- **`internal/kafka/`** package:
  - `kafkautils.py` — `load_properties()`, `fetch_topic_configs()`,
    `fetch_partition_info()` with concurrent `ThreadPoolExecutor` support.
- Dependencies: `click`, `confluent-kafka`, `rich`.
