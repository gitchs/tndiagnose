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


@click.command("analyze")
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
def analyze(input_path, level, topk):
    """Analyze directory sizes from an S3 object listing."""

    db = duckdb.connect()
    db.execute(
        """
        CREATE OR REPLACE VIEW objects AS
        SELECT key, size FROM read_json_auto(?, format='newline_delimited')
        """,
        [input_path],
    )

    rows = db.execute(
        f"""
        SELECT
          COALESCE(
            array_to_string(list_slice(string_split(key, '/'), 1, {level}), '/'),
            key
          ) AS prefix,
          SUM(size)::BIGINT AS total
        FROM objects
        GROUP BY prefix
        ORDER BY total DESC
        """
    ).fetchall()

    db.close()

    if not rows:
        click.echo("No objects found.")
        return

    grand_total = sum(r[1] for r in rows)

    console = Console()
    table = Table(title=f"Top directories (level {level})")
    table.add_column("directory", style="cyan")
    table.add_column("size", justify="right")
    table.add_column("ratio", justify="right")

    top = rows[:topk]
    others_size = sum(r[1] for r in rows[topk:])
    others_ratio = others_size / grand_total * 100 if grand_total else 0

    for prefix, total in top:
        ratio = total / grand_total * 100 if grand_total else 0
        table.add_row(prefix, _pretty_size(total), f"{ratio:.1f}%")

    if others_size > 0:
        table.add_row(
            "[dim]others[/dim]",
            _pretty_size(others_size),
            f"{others_ratio:.1f}%",
        )

    console.print(table)
    console.print(f"\nTotal: {_pretty_size(grand_total)} across {len(rows)} prefixes")
