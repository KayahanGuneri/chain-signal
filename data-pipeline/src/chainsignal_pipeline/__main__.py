from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from datetime import datetime

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

    fetch_gdacs_parser.add_argument(
        "--start",
        required=True,
        type=parse_datetime,
        help="Window start as timezone-aware ISO 8601 datetime",
    )

    fetch_gdacs_parser.add_argument(
        "--end",
        required=True,
        type=parse_datetime,
        help="Window end as timezone-aware ISO 8601 datetime",
    )

    return parser


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

    with create_gdacs_client(
        timeout_seconds=settings.http_timeout_seconds,
    ) as client:
        adapter = GdacsAdapter(client)
        records = adapter.fetch(window)

    logger.info(
        "Completed GDACS fetch",
        extra={
            "event": "gdacs_fetch_completed",
            "source": adapter.source_name,
            "window_start": window.start.isoformat(),
            "window_end": window.end.isoformat(),
            "record_count": len(records),
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
