import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin._config import ConfigResource
from confluent_kafka.admin._resource import ResourceType


def load_properties(path):
    props = {}

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            k, v = line.split("=", 1)
            props[k.strip()] = v.strip()

    jaas = props.pop("sasl.jaas.config", None)
    if jaas:
        username = re.search(r'username="([^"]+)"', jaas)
        password = re.search(r'password="([^"]+)"', jaas)

        if username:
            props["sasl.username"] = username.group(1)
        if password:
            props["sasl.password"] = password.group(1)

    if "sasl.mechanisms" in props and "sasl.mechanism" not in props:
        props["sasl.mechanism"] = props.pop("sasl.mechanisms")

    return props


def fetch_topic_configs(admin_client, timeout=10):
    """Fetch all topic configurations from a Kafka cluster.

    Returns a list of dicts, each containing a "topic" key followed by all
    configuration keys for that topic.  Suitable for direct use with
    ``pandas.DataFrame(rows)``.
    """

    metadata = admin_client.list_topics(timeout=timeout)
    topics = sorted(t for t in metadata.topics if not t.startswith("__"))

    resources = [ConfigResource(ResourceType.TOPIC, t) for t in topics]
    futures = admin_client.describe_configs(resources)

    all_keys: set[str] = set()
    topic_configs: dict[str, dict[str, str]] = {}

    for resource, future in futures.items():
        topic = resource.name
        topic_configs[topic] = {}

        try:
            configs = future.result()
            for key, entry in configs.items():
                value = entry.value if entry.value is not None else ""
                topic_configs[topic][key] = value
                all_keys.add(key)
        except Exception as e:
            topic_configs[topic]["__error__"] = str(e)
            all_keys.add("__error__")

    sorted_keys = sorted(all_keys)

    rows: list[dict[str, str]] = []
    for topic in topics:
        row: dict[str, str] = {"topic": topic}
        configs = topic_configs.get(topic, {})
        for key in sorted_keys:
            row[key] = configs.get(key, "")
        rows.append(row)

    return rows


def _fetch_partition_batch(consumer_conf, topic, partition_ids, timeout):
    """Fetch offset info for a batch of partitions using a dedicated consumer."""
    conf = {
        **consumer_conf,
        "group.id": f"tndiagnose-batch-{topic}",
        "enable.auto.commit": "false",
    }
    c = Consumer(conf)
    try:
        results: list[dict] = []
        for p in partition_ids:
            tp = TopicPartition(topic, p)
            lo, hi = c.get_watermark_offsets(tp, timeout=timeout)

            timestamp = ""
            if hi > lo:
                c.assign([TopicPartition(topic, p, hi - 1)])
                msg = c.poll(timeout)
                if msg and not msg.error():
                    ts_type, ts_ms = msg.timestamp()
                    if ts_type != 0:
                        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                        timestamp = dt.isoformat()

            results.append(
                {
                    "partition": p,
                    "earliest_offset": lo,
                    "latest_offset": hi,
                    "messages": max(0, hi - lo),
                    "message_time": timestamp,
                }
            )
        return results
    finally:
        c.close()


def fetch_partition_info(consumer_conf, topic, timeout=10, concurrency=8):
    """Fetch per-partition offset / message-time info for a topic.

    Partition queries are distributed across ``concurrency`` worker threads
    (each with its own Kafka consumer).  The actual concurrency is capped at
    ``min(concurrency, len(partitions))``.

    Returns a list of dicts with keys: partition, earliest_offset,
    latest_offset, message_time (ISO-8601 string or empty), messages.
    """

    # Discover partitions with a short-lived consumer
    meta_conf = {**consumer_conf, "group.id": f"tndiagnose-meta-{topic}"}
    mc = Consumer(meta_conf)
    try:
        meta = mc.list_topics(topic, timeout=timeout)
        if topic not in meta.topics:
            return []
        partitions = sorted(meta.topics[topic].partitions.keys())
    finally:
        mc.close()

    if not partitions:
        return []

    workers = min(concurrency, len(partitions))

    # Distribute partitions across workers (round-robin)
    batches: list[list[int]] = [[] for _ in range(workers)]
    for i, p in enumerate(partitions):
        batches[i % workers].append(p)

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _fetch_partition_batch, consumer_conf, topic, batch, timeout
            ): batch
            for batch in batches
        }
        for future in as_completed(futures):
            results.extend(future.result())

    results.sort(key=lambda r: r["partition"])
    return results
