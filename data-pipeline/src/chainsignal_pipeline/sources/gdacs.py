from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from chainsignal_pipeline.sources.base import SourceAdapter, SourceWindow

logger = logging.getLogger(__name__)

GDACS_SEARCH_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
GDACS_SOURCE_NAME = "GDACS"

EVENT_TYPES = "EQ;FL"
ALERT_LEVELS = "Green;Orange;Red"

DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 100
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 0.5


def create_gdacs_client(
    *,
    timeout_seconds: float,
) -> httpx.Client:
    """Create the configured HTTP client used by the GDACS adapter."""

    if timeout_seconds <= 0:
        raise ValueError("GDACS timeout_seconds must be greater than zero")

    return httpx.Client(
        timeout=timeout_seconds,
    )


class GdacsAdapter(SourceAdapter):
    """Fetch raw disaster events from the GDACS SEARCH API."""

    def __init__(
        self,
        client: httpx.Client,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    ) -> None:
        if not 1 <= page_size <= 100:
            raise ValueError("GDACS page_size must be between 1 and 100")

        if max_pages < 1:
            raise ValueError("GDACS max_pages must be at least 1")

        if max_attempts < 1:
            raise ValueError("GDACS max_attempts must be at least 1")

        if retry_backoff_seconds < 0:
            raise ValueError("GDACS retry_backoff_seconds must not be negative")

        self._client = client
        self._page_size = page_size
        self._max_pages = max_pages
        self._max_attempts = max_attempts
        self._retry_backoff_seconds = retry_backoff_seconds

    @property
    def source_name(self) -> str:
        return GDACS_SOURCE_NAME

    def fetch(
        self,
        window: SourceWindow,
    ) -> list[dict[str, Any]]:
        """Fetch all GDACS records for the requested source window."""

        records: list[dict[str, Any]] = []
        seen_page_signatures: set[str] = set()

        for page_number in range(1, self._max_pages + 1):
            page = self._fetch_page(
                window=window,
                page_number=page_number,
            )

            if not page:
                return records

            page_signature = self._page_signature(page)

            if page_signature in seen_page_signatures:
                raise RuntimeError("GDACS returned a previously seen page during pagination")

            seen_page_signatures.add(page_signature)
            records.extend(page)

            if len(page) < self._page_size:
                return records

        raise RuntimeError(f"GDACS pagination exceeded max_pages={self._max_pages}")

    def _fetch_page(
        self,
        *,
        window: SourceWindow,
        page_number: int,
    ) -> list[dict[str, Any]]:
        params = self._build_params(
            window=window,
            page_number=page_number,
        )

        response = self._get_with_retry(
            params=params,
        )

        payload: object = response.json()

        if not isinstance(payload, dict):
            raise ValueError("GDACS response must be a JSON object")

        if payload.get("type") != "FeatureCollection":
            raise ValueError("GDACS response must be a GeoJSON FeatureCollection")

        features = payload.get("features")

        if not isinstance(features, list):
            raise ValueError("GDACS response must contain a features list")

        validated_features: list[dict[str, Any]] = []

        for feature in features:
            if not isinstance(feature, dict):
                raise ValueError("GDACS features must contain JSON objects")

            validated_features.append(feature)

        return validated_features

    def _get_with_retry(
        self,
        *,
        params: dict[str, str | int],
    ) -> httpx.Response:
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._client.get(
                    GDACS_SEARCH_URL,
                    params=params,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == self._max_attempts:
                    raise

                self._retry(
                    attempt=attempt,
                    reason=type(exc).__name__,
                )
                continue

            if self._is_retryable_status(response.status_code):
                if attempt == self._max_attempts:
                    response.raise_for_status()

                self._retry(
                    attempt=attempt,
                    reason="retryable_http_status",
                    status_code=response.status_code,
                )
                continue

            response.raise_for_status()
            return response

        raise RuntimeError("GDACS retry loop terminated unexpectedly")

    def _retry(
        self,
        *,
        attempt: int,
        reason: str,
        status_code: int | None = None,
    ) -> None:
        delay = self._retry_delay(attempt)

        logger.warning(
            "Retrying GDACS request after transient failure",
            extra={
                "event": "gdacs_request_retry",
                "source": GDACS_SOURCE_NAME,
                "attempt": attempt,
                "max_attempts": self._max_attempts,
                "reason": reason,
                "status_code": status_code,
                "retry_delay_seconds": delay,
            },
        )

        if delay > 0:
            time.sleep(delay)

    def _retry_delay(
        self,
        attempt: int,
    ) -> float:
        return self._retry_backoff_seconds * (2.0 ** (attempt - 1))

    @staticmethod
    def _is_retryable_status(
        status_code: int,
    ) -> bool:
        return status_code == 429 or 500 <= status_code <= 599

    def _build_params(
        self,
        *,
        window: SourceWindow,
        page_number: int,
    ) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "eventlist": EVENT_TYPES,
            "fromdate": self._format_date(window.start),
            "todate": self._format_date(window.end),
            "alertlevel": ALERT_LEVELS,
            "pagesize": self._page_size,
        }

        if page_number > 1:
            params["pagenumber"] = page_number

        return params

    @staticmethod
    def _format_date(
        value: datetime,
    ) -> str:
        return value.astimezone(UTC).date().isoformat()

    @staticmethod
    def _page_signature(
        page: list[dict[str, Any]],
    ) -> str:
        serialized = json.dumps(
            page,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
