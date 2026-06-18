import click

from internal.kafka import cli as kafka_cli
from internal.s3 import cli as s3_cli


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    """Tencent Cloud diagnostics toolkit."""


main.add_command(kafka_cli, name="kafka")
main.add_command(s3_cli, name="s3")


if __name__ == "__main__":
    main()
