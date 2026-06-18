import click
from internal.kafka.list_partitions import list_partitions
from internal.kafka.list_topics import list_topics


@click.group()
def cli():
    """Kafka cluster diagnostics."""


cli.add_command(list_topics)
cli.add_command(list_partitions)
