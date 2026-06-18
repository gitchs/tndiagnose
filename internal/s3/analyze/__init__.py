import click
import duckdb
from rich.console import Console
from rich.table import Table


def _pretty_size(n):
    """Human-readable size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"


def _load_objects(db, input_path):
    db.execute(
        f"""
        CREATE OR REPLACE VIEW objects AS
        SELECT key, size, last_modified
        FROM read_json_auto('{input_path}', format='newline_delimited')
        """
    )


@click.command("by-level")
@click.option("--input", "input_path", required=True, help="JSON Lines file (.zst ok).")
@click.option(
    "--level",
    type=int,
    default=1,
    show_default=True,
    help="Aggregate at this directory depth.",
)
@click.option(
    "--topk",
    type=int,
    default=10,
    show_default=True,
    help="Number of top directories to show; rest grouped as others.",
)
def by_level(input_path, level, topk):
    """Analyze directory sizes by prefix depth."""

    db = duckdb.connect()
    _load_objects(db, input_path)

    rows = db.execute(
        f"""
        WITH per_prefix AS (
            SELECT
                COALESCE(
                    array_to_string(list_slice(string_split(key, '/'), 1, {level}), '/'),
                    key
                ) AS prefix,
                SUM(size)::BIGINT AS total
            FROM objects
            GROUP BY prefix
        ),
        tagged AS (
            SELECT
                CASE
                    WHEN ROW_NUMBER() OVER (ORDER BY total DESC) <= {topk} THEN prefix
                    ELSE '__others__'
                END AS display_prefix,
                total
            FROM per_prefix
        )
        SELECT
            display_prefix AS prefix,
            SUM(total)::BIGINT AS total,
            SUM(total) * 100.0 / SUM(SUM(total)) OVER () AS ratio
        FROM tagged
        GROUP BY display_prefix
        ORDER BY total DESC
        """
    ).fetchall()

    db.close()

    if not rows:
        click.echo("No objects found.")
        return

    grand_total = sum(r[1] for r in rows)
    others_row = next((r for r in rows if r[0] == "__others__"), None)

    console = Console()
    table = Table(title=f"Top directories (level {level})")
    table.add_column("directory", style="cyan")
    table.add_column("size", justify="right")
    table.add_column("ratio", justify="right")

    for prefix, total, ratio in rows:
        if prefix == "__others__":
            continue
        table.add_row(prefix, _pretty_size(total), f"{ratio:.1f}%")

    if others_row:
        table.add_row(
            "[dim]others[/dim]",
            _pretty_size(others_row[1]),
            f"{others_row[2]:.1f}%",
        )

    console.print(table)
    console.print(
        f"\nTotal: {_pretty_size(grand_total)} across "
        f"{len(rows) - (1 if others_row else 0)} prefixes"
    )


@click.command("by-time")
@click.option("--input", "input_path", required=True, help="JSON Lines file (.zst ok).")
@click.option("--prefix", default="", help="Filter objects by key prefix.")
def by_time(input_path, prefix):
    """Analyze storage size distribution over time (by day)."""

    db = duckdb.connect()
    _load_objects(db, input_path)

    where = f"WHERE key LIKE '{prefix}%'" if prefix else ""

    rows = db.execute(
        f"""
        SELECT
            last_modified::DATE AS day,
            SUM(size)::BIGINT AS total
        FROM objects
        {where}
        GROUP BY day
        ORDER BY day
        """
    ).fetchall()

    db.close()

    if not rows:
        click.echo("No objects found.")
        return

    grand_total = sum(r[1] for r in rows)

    console = Console()
    table = Table(title=f"Size by day{' (prefix={prefix})' if prefix else ''}")
    table.add_column("day", style="cyan")
    table.add_column("size", justify="right")
    table.add_column("ratio", justify="right")

    for day, total in rows:
        ratio = total / grand_total * 100 if grand_total else 0
        table.add_row(str(day), _pretty_size(total), f"{ratio:.1f}%")

    console.print(table)
    console.print(f"\nTotal: {_pretty_size(grand_total)} across {len(rows)} days")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """Analyze S3 object listings."""


cli.add_command(by_level)
cli.add_command(by_time)
