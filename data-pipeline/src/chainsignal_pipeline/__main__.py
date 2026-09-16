from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from chainsignal_pipeline.bronze.models import BronzeRequest
from chainsignal_pipeline.bronze.writer import BronzeWriter
from chainsignal_pipeline.config import Settings
from chainsignal_pipeline.logging_config import configure_logging
from chainsignal_pipeline.sources.base import SourceWindow
from chainsignal_pipeline.sources.gdacs import (
    GdacsAdapter,
    create_gdacs_client,
)

logger = logging.getLogger(__name__)

VERSION = "0.1.0"


def parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 datetime supplied through the CLI."""

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid ISO 8601 datetime: {value}") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("Datetime must include a timezone offset")

    return parsed


def add_window_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--start",
        required=True,
        type=parse_datetime,
        help="Window start as timezone-aware ISO 8601 datetime",
    )

    parser.add_argument(
        "--end",
        required=True,
        type=parse_datetime,
        help="Window end as timezone-aware ISO 8601 datetime",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chainsignal_pipeline",
        description="ChainSignal data pipeline",
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )

    fetch_gdacs_parser = subparsers.add_parser(
        "fetch-gdacs",
        help="Fetch raw GDACS events for an explicit time window",
    )
    add_window_arguments(fetch_gdacs_parser)

    ingest_gdacs_parser = subparsers.add_parser(
        "ingest-gdacs",
        help="Fetch GDACS events and persist an immutable Bronze batch",
    )
    add_window_arguments(ingest_gdacs_parser)

    return parser


def fetch_gdacs_records(
    *,
    settings: Settings,
    window: SourceWindow,
) -> tuple[str, list[dict[str, object]]]:
    with create_gdacs_client(
        timeout_seconds=settings.http_timeout_seconds,
    ) as client:
        adapter = GdacsAdapter(client)
        records = adapter.fetch(window)

        return adapter.source_name, records


def run_gdacs_fetch(
    *,
    settings: Settings,
    start: datetime,
    end: datetime,
) -> None:
    window = SourceWindow(
        start=start,
        end=end,
    )

    logger.info(
        "Starting GDACS fetch",
        extra={
            "event": "gdacs_fetch_started",
            "source": "GDACS",
            "window_start": window.start.isoformat(),
            "window_end": window.end.isoformat(),
        },
    )

    source, records = fetch_gdacs_records(
        settings=settings,
        window=window,
    )

    logger.info(
        "Completed GDACS fetch",
        extra={
            "event": "gdacs_fetch_completed",
            "source": source,
            "window_start": window.start.isoformat(),
            "window_end": window.end.isoformat(),
            "record_count": len(records),
        },
    )


def run_gdacs_ingestion(
    *,
    settings: Settings,
    start: datetime,
    end: datetime,
) -> None:
    window = SourceWindow(
        start=start,
        end=end,
    )

    logger.info(
        "Starting GDACS Bronze ingestion",
        extra={
            "event": "gdacs_ingestion_started",
            "source": "GDACS",
            "window_start": window.start.isoformat(),
            "window_end": window.end.isoformat(),
        },
    )

    source, records = fetch_gdacs_records(
        settings=settings,
        window=window,
    )

    request = BronzeRequest(
        source=source,
        window_start=window.start,
        window_end=window.end,
    )

    writer = BronzeWriter(
        root_path=settings.bronze_path,
    )

    result = writer.write(
        request=request,
        raw_records=records,
        ingested_at=datetime.now(UTC),
    )

    logger.info(
        "Completed GDACS Bronze ingestion",
        extra={
            "event": "gdacs_ingestion_completed",
            "source": source,
            "window_start": window.start.isoformat(),
            "window_end": window.end.isoformat(),
            "request_identity": result.metadata.request_identity,
            "raw_content_hash": result.metadata.raw_content_hash,
            "batch_id": result.metadata.batch_id,
            "record_count": result.metadata.record_count,
            "bronze_path": str(result.path),
            "batch_created": result.created,
        },
    )


def main(
    argv: Sequence[str] | None = None,
) -> None:
    settings = Settings()
    configure_logging(settings.log_level)

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "fetch-gdacs":
        run_gdacs_fetch(
            settings=settings,
            start=args.start,
            end=args.end,
        )
        return

    if args.command == "ingest-gdacs":
        run_gdacs_ingestion(
            settings=settings,
            start=args.start,
            end=args.end,
        )
        return

    logger.info(
        "ChainSignal data pipeline ready",
        extra={
            "event": "pipeline_bootstrap",
            "version": VERSION,
            "environment": settings.environment,
        },
    )


if __name__ == "__main__":
    main()
