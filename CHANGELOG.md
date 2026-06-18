# Changelog

## [0.1.0] — Unreleased

### Added

- **`list-topics`** CLI command: export all Kafka topic configurations to CSV.
  - `--config` flag for consumer properties file.
  - `--output` flag for CSV destination.
- **`list-partitions`** CLI command: list per-partition offsets, message count,
  and latest message timestamp for a given topic.
  - `--topic` (required), `--config`, `--output`, `--concurrent` (default 8).
  - Pretty-printed table via `rich` when `--output` is omitted.
- **`internal/kafkautils.py`**: shared Kafka utilities.
  - `load_properties(path)` — parse Java-style `.properties` file.
  - `fetch_topic_configs(admin_client)` — collect all topic configs.
  - `fetch_partition_info(conf, topic, concurrency)` — concurrent per-partition
    offset & timestamp queries.
- Dependencies: `click`, `confluent-kafka`, `rich`.
