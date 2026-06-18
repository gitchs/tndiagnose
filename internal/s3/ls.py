import json
import sys
from urllib.parse import urlparse

import boto3
import click
import zstandard


def _parse_s3_uri(uri):
    """Parse s3://bucket/prefix into (bucket, prefix)."""
    parsed = urlparse(uri)
    if parsed.scheme != "s3":
        raise click.BadParameter(f"Expected s3:// URI, got: {uri}")
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/")
    return bucket, prefix


def _list_objects(bucket, prefix):
    """Yield JSON-serializable dicts for every object under the prefix."""
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            yield {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
                "etag": obj["ETag"].strip('"'),
                "storage_class": obj.get("StorageClass", "STANDARD"),
            }


def _write_output(rows, output_path):
    """Stream JSON Lines to file (optionally .zst compressed) or stdout."""

    # --- file output: stream directly ---
    if output_path:
        if output_path.endswith(".zst"):
            cctx = zstandard.ZstdCompressor()
            with open(output_path, "wb") as f:
                compressor = cctx.stream_writer(f)
                for row in rows:
                    compressor.write(json.dumps(row).encode() + b"\n")
                compressor.flush(zstandard.FLUSH_FRAME)
        else:
            with open(output_path, "w") as f:
                for row in rows:
                    f.write(json.dumps(row) + "\n")
        return

    # --- pipe stdout: stream everything ---
    if not sys.stdout.isatty():
        for row in rows:
            sys.stdout.write(json.dumps(row) + "\n")
        return

    # --- TTY stdout: stream first 100, then count silently ---
    count = 0
    for row in rows:
        if count < 100:
            sys.stdout.write(json.dumps(row) + "\n")
        count += 1

    if count > 100:
        click.echo(
            f"\n... truncated ({count - 100} more objects). "
            "Use --output to export all results.",
            err=True,
        )


@click.command("ls")
@click.argument("uri", required=False)
@click.option("--bucket", default=None, help="S3 bucket name.")
@click.option("--prefix", default="", help="S3 key prefix.")
@click.option(
    "--output", "output_path", default=None, help="Output file (.zst for compression)."
)
def ls(uri, bucket, prefix, output_path):
    """List S3 objects under a prefix (JSON Lines)."""

    if uri:
        if bucket or prefix:
            raise click.UsageError("Use either URI or --bucket/--prefix, not both.")
        bucket, prefix = _parse_s3_uri(uri)
    elif not bucket:
        raise click.UsageError("Either --bucket or an s3:// URI is required.")

    rows = _list_objects(bucket, prefix)
    _write_output(rows, output_path)
