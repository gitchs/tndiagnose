import click

from internal.s3.analyze import analyze
from internal.s3.ls import ls


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """S3 utilities."""


cli.add_command(ls)
cli.add_command(analyze)
