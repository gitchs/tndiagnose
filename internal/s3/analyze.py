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
        ranked AS (
            SELECT
                prefix,
                total,
                ROW_NUMBER() OVER (ORDER BY total DESC) AS rn,
                SUM(total) OVER () AS grand_total
            FROM per_prefix
        )
        SELECT
            CASE WHEN rn <= {topk} THEN prefix ELSE '__others__' END AS prefix,
            SUM(total)::BIGINT AS total,
            SUM(total) * 100.0 / MAX(grand_total) AS ratio
        FROM ranked
        GROUP BY prefix
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
        f"\nTotal: {_pretty_size(grand_total)} across {len(rows) - (1 if others_row else 0)} prefixes"
    )
