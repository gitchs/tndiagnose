import csv

import click
from confluent_kafka.admin import AdminClient
from internal.kafka.kafkautils import fetch_topic_configs, load_properties


@click.command("list-topics")
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
    default="topic_configs.csv",
    show_default=True,
    help="Path to the output CSV file.",
)
def list_topics(config_path, output_path):
    """Export all topic configurations from a Kafka cluster to CSV."""

    conf = load_properties(config_path)
    admin = AdminClient(conf)
    rows = fetch_topic_configs(admin)

    if not rows:
        click.echo("No topics found.")
        return

    fieldnames = list(rows[0].keys())

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    click.echo(f"Exported {len(rows)} topics to: {output_path}")


if __name__ == "__main__":
    list_topics()
