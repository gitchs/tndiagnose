import csv

import click
from rich.console import Console
from rich.table import Table

from internal.kafkautils import fetch_partition_info, load_properties


@click.command()
@click.option("--topic", required=True, help="Kafka topic name.")
@click.option(
    "--config",
    "config_path",
    default="consumer.properties",
    show_default=True,
    help="Path to the Kafka consumer properties file.",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    help="Write CSV to this path instead of printing a table.",
)
@click.option(
    "--concurrent",
    "concurrency",
    type=int,
    default=8,
    show_default=True,
    help="Max parallel consumers. Actual = min(concurrent, partitions).",
)
def main(topic, config_path, output_path, concurrency):
    """List per-partition offsets, message count, and latest message time."""

    conf = load_properties(config_path)
    rows = fetch_partition_info(conf, topic, concurrency=concurrency)

    if not rows:
        click.echo(f"No partition info found for topic: {topic}")
        return

    fieldnames = list(rows[0].keys())

    if output_path:
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        click.echo(f"Exported {len(rows)} partitions to: {output_path}")
    else:
        console = Console()
        table = Table(title=f"Topic: {topic}")
        for key in fieldnames:
            table.add_column(key, style="cyan" if key == "partition" else None)
        for row in rows:
            table.add_row(*[str(row[k]) for k in fieldnames])
        console.print(table)


if __name__ == "__main__":
    main()
