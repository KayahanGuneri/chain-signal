import logging

from chainsignal_pipeline import __version__
from chainsignal_pipeline.config import Settings
from chainsignal_pipeline.logging_config import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()

    configure_logging(settings.log_level)

    logger.info(
        "ChainSignal data pipeline ready",
        extra={
            "event": "pipeline_bootstrap",
            "version": __version__,
            "environment": settings.environment,
        },
    )


if __name__ == "__main__":
    main()
