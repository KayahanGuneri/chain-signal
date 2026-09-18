from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chainsignal_pipeline.bronze.models import BronzeRequest
from chainsignal_pipeline.bronze.reader import BronzeReader
from chainsignal_pipeline.bronze.writer import BronzeWriter
from chainsignal_pipeline.config import DatabaseSettings, Settings
from chainsignal_pipeline.database.event_writer import EventPersistenceWriter
from chainsignal_pipeline.logging_config import configure_logging
from chainsignal_pipeline.normalization.gdacs import (
    normalize_gdacs_records,
)
from chainsignal_pipeline.normalization.writer import (
    NormalizationWriter,
)
from chainsignal_pipeline.sources.base import SourceWindow
from chainsignal_pipeline.sources.gdacs import (
    GDACS_SOURCE_NAME,
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
        help=("Window start as timezone-aware ISO 8601 datetime"),
    )

    parser.add_argument(
        "--end",
        required=True,
        type=parse_datetime,
        help=("Window end as timezone-aware ISO 8601 datetime"),
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
        help=("Fetch raw GDACS events for an explicit time window"),
    )
    add_window_arguments(fetch_gdacs_parser)

    ingest_gdacs_parser = subparsers.add_parser(
        "ingest-gdacs",
        help=("Fetch GDACS events and persist an immutable Bronze batch"),
    )
    add_window_arguments(ingest_gdacs_parser)

    normalize_gdacs_parser = subparsers.add_parser(
        "normalize-gdacs",
        help=("Normalize one verified GDACS Bronze batch and persist canonical events"),
    )

    normalize_gdacs_parser.add_argument(
        "--bronze-file",
        required=True,
        type=Path,
        help=("Path to one Bronze Parquet batch file"),
    )

    return parser


def fetch_gdacs_records(
    *,
    settings: Settings,
    window: SourceWindow,
) -> tuple[
    str,
    list[dict[str, Any]],
]:
    with create_gdacs_client(
        timeout_seconds=(settings.http_timeout_seconds),
    ) as client:
        adapter = GdacsAdapter(client)
        records = adapter.fetch(window)

        return (
            adapter.source_name,
            records,
        )


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
            "source": GDACS_SOURCE_NAME,
            "window_start": (window.start.isoformat()),
            "window_end": (window.end.isoformat()),
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
            "window_start": (window.start.isoformat()),
            "window_end": (window.end.isoformat()),
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
            "event": ("gdacs_ingestion_started"),
            "source": GDACS_SOURCE_NAME,
            "window_start": (window.start.isoformat()),
            "window_end": (window.end.isoformat()),
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
            "event": ("gdacs_ingestion_completed"),
            "source": source,
            "window_start": (window.start.isoformat()),
            "window_end": (window.end.isoformat()),
            "request_identity": (result.metadata.request_identity),
            "raw_content_hash": (result.metadata.raw_content_hash),
            "batch_id": (result.metadata.batch_id),
            "record_count": (result.metadata.record_count),
            "bronze_path": str(result.path),
            "batch_created": (result.created),
        },
    )


def run_gdacs_normalization(
    *,
    settings: Settings,
    event_writer: EventPersistenceWriter,
    bronze_file: Path,
) -> None:
    logger.info(
        "Starting GDACS canonical normalization",
        extra={
            "event": ("gdacs_normalization_started"),
            "bronze_path": str(bronze_file),
        },
    )

    reader = BronzeReader()

    batch = reader.read(bronze_file)

    if batch.metadata.source != GDACS_SOURCE_NAME:
        raise ValueError(
            f"GDACS normalization requires a GDACS Bronze batch, got source={batch.metadata.source}"
        )

    result = normalize_gdacs_records(
        batch.raw_records,
    )

    writer = NormalizationWriter(
        root_path=(settings.normalized_path),
    )

    write_result = writer.write(
        source=batch.metadata.source,
        batch_id=batch.metadata.batch_id,
        events=result.events,
        quarantined_records=(result.quarantined_records),
        summary=result.summary,
    )
    persistence_result = event_writer.write(
        result.events,
    )

    logger.info(
        "Completed GDACS canonical normalization",
        extra={
            "event": ("gdacs_normalization_completed"),
            "source": (batch.metadata.source),
            "batch_id": (batch.metadata.batch_id),
            "bronze_path": str(batch.path),
            "input_count": (result.summary.input_count),
            "valid_count": (result.summary.valid_count),
            "invalid_count": (result.summary.invalid_count),
            "duplicate_count": (result.summary.duplicate_count),
            "quarantine_count": (result.summary.quarantine_count),
            "reason_counts": (result.summary.reason_counts_by_code),
            "output_directory": str(write_result.output_directory),
            "events_path": str(write_result.events_path),
            "quarantine_path": str(write_result.quarantine_path),
            "quality_path": str(write_result.quality_path),
            "output_created": (write_result.created),
            "database_input_count": persistence_result.input_count,
            "database_changed_count": persistence_result.changed_count,
            "database_unchanged_count": persistence_result.unchanged_count,
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

    if args.command == "normalize-gdacs":
        database_settings = DatabaseSettings()

        event_writer = EventPersistenceWriter(
            settings=database_settings,
        )

        run_gdacs_normalization(
            settings=settings,
            event_writer=event_writer,
            bronze_file=args.bronze_file,
        )
        return

    logger.info(
        "ChainSignal data pipeline ready",
        extra={
            "event": "pipeline_bootstrap",
            "version": VERSION,
            "environment": (settings.environment),
        },
    )


if __name__ == "__main__":
    main()
