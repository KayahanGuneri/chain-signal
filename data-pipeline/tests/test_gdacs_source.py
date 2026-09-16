from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from chainsignal_pipeline.sources.base import SourceWindow
from chainsignal_pipeline.sources.gdacs import (
    GdacsAdapter,
    create_gdacs_client,
)


def make_window() -> SourceWindow:
    return SourceWindow(
        start=datetime(2026, 9, 8, tzinfo=UTC),
        end=datetime(2026, 9, 15, tzinfo=UTC),
    )


def make_feature(event_id: int) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {
            "eventtype": "EQ",
            "eventid": event_id,
        },
        "geometry": {
            "type": "Point",
            "coordinates": [30.0, 40.0],
        },
    }


def test_gdacs_adapter_exposes_stable_source_name() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [],
            },
        )
    )

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(client)

        assert adapter.source_name == "GDACS"


def test_gdacs_adapter_builds_expected_search_request() -> None:
    observed_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed_requests.append(request)

        return httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [make_feature(1)],
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(client)

        records = adapter.fetch(make_window())

    assert len(records) == 1
    assert len(observed_requests) == 1

    params = observed_requests[0].url.params

    assert params["eventlist"] == "EQ;FL"
    assert params["fromdate"] == "2026-09-08"
    assert params["todate"] == "2026-09-15"
    assert params["alertlevel"] == "Green;Orange;Red"
    assert params["pagesize"] == "100"
    assert "pagenumber" not in params


def test_gdacs_adapter_paginates_until_partial_page() -> None:
    requested_pages: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page_number = request.url.params.get("pagenumber")
        requested_pages.append(page_number)

        if page_number is None:
            features = [
                make_feature(1),
                make_feature(2),
            ]
        elif page_number == "2":
            features = [
                make_feature(3),
            ]
        else:
            raise AssertionError(f"Unexpected GDACS page request: {page_number}")

        return httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": features,
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(
            client,
            page_size=2,
        )

        records = adapter.fetch(make_window())

    assert requested_pages == [None, "2"]
    assert len(records) == 3


def test_gdacs_adapter_rejects_non_feature_collection() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "type": "Unexpected",
                "features": [],
            },
        )
    )

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(client)

        with pytest.raises(
            ValueError,
            match="GeoJSON FeatureCollection",
        ):
            adapter.fetch(make_window())


def test_gdacs_adapter_rejects_repeated_page() -> None:
    feature = make_feature(1)

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [feature],
            },
        )
    )

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(
            client,
            page_size=1,
            max_pages=3,
        )

        with pytest.raises(
            RuntimeError,
            match="previously seen page",
        ):
            adapter.fetch(make_window())


def test_gdacs_adapter_retries_timeout_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise httpx.ReadTimeout(
                "Simulated timeout",
                request=request,
            )

        return httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [make_feature(1)],
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(
            client,
            retry_backoff_seconds=0,
        )

        records = adapter.fetch(make_window())

    assert attempts == 2
    assert len(records) == 1


def test_gdacs_adapter_retries_429_and_5xx_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            return httpx.Response(
                429,
                request=request,
            )

        if attempts == 2:
            return httpx.Response(
                503,
                request=request,
            )

        return httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [make_feature(1)],
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(
            client,
            retry_backoff_seconds=0,
        )

        records = adapter.fetch(make_window())

    assert attempts == 3
    assert len(records) == 1


def test_gdacs_adapter_does_not_retry_non_retryable_4xx() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1

        return httpx.Response(
            400,
            request=request,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(
            client,
            retry_backoff_seconds=0,
        )

        with pytest.raises(httpx.HTTPStatusError):
            adapter.fetch(make_window())

    assert attempts == 1


def test_gdacs_adapter_does_not_retry_malformed_success_response() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1

        return httpx.Response(
            200,
            json={
                "type": "Unexpected",
                "features": [],
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(
            client,
            retry_backoff_seconds=0,
        )

        with pytest.raises(
            ValueError,
            match="GeoJSON FeatureCollection",
        ):
            adapter.fetch(make_window())

    assert attempts == 1


def test_gdacs_adapter_stops_after_max_attempts() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1

        raise httpx.ReadTimeout(
            "Simulated persistent timeout",
            request=request,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(
            client,
            max_attempts=3,
            retry_backoff_seconds=0,
        )

        with pytest.raises(httpx.ReadTimeout):
            adapter.fetch(make_window())

    assert attempts == 3


def test_create_gdacs_client_uses_configured_timeout() -> None:
    with create_gdacs_client(
        timeout_seconds=17.5,
    ) as client:
        assert client.timeout.connect == 17.5
        assert client.timeout.read == 17.5
        assert client.timeout.write == 17.5
        assert client.timeout.pool == 17.5


def test_create_gdacs_client_rejects_non_positive_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="timeout_seconds must be greater than zero",
    ):
        create_gdacs_client(
            timeout_seconds=0,
        )


def test_gdacs_adapter_logs_retry_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            return httpx.Response(
                503,
                request=request,
            )

        return httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [make_feature(1)],
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = GdacsAdapter(
            client,
            retry_backoff_seconds=0,
        )

        with caplog.at_level(
            "WARNING",
            logger="chainsignal_pipeline.sources.gdacs",
        ):
            adapter.fetch(make_window())

    retry_records = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "gdacs_request_retry"
    ]

    assert len(retry_records) == 1

    record = retry_records[0]

    assert getattr(record, "source", None) == "GDACS"

    assert getattr(record, "attempt", None) == 1
    assert getattr(record, "max_attempts", None) == 3
    assert getattr(record, "reason", None) == "retryable_http_status"
    assert getattr(record, "status_code", None) == 503
    assert getattr(record, "retry_delay_seconds", None) == 0
