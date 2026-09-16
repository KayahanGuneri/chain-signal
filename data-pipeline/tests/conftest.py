from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from chainsignal_pipeline.bronze.models import BronzeRequest
from chainsignal_pipeline.bronze.writer import BronzeWriter, BronzeWriteResult


@pytest.fixture
def ingested_at() -> datetime:
    return datetime(2026, 9, 16, 12, tzinfo=UTC)


@pytest.fixture
def bronze_request() -> BronzeRequest:
    return BronzeRequest(
        source="GDACS",
        window_start=datetime(2026, 9, 14, tzinfo=UTC),
        window_end=datetime(2026, 9, 16, tzinfo=UTC),
    )


@pytest.fixture
def gdacs_record() -> dict[str, Any]:
    return {
        "type": "Feature",
        "id": "provider-feature-123",
        "geometry": {"type": "Point", "coordinates": [30.5, 40.25]},
        "properties": {
            "eventtype": "EQ",
            "eventid": 123,
            "fromdate": "2026-09-14T01:00:00",
            "alertlevel": "Orange",
            "country": "Türkiye",
            "episodeid": 2,
            "source": "provider",
            "alertscore": 1.5,
            "episodealertlevel": "Green",
            "episodealertscore": 0.5,
            "severitydata": {"magnitude": 5.5},
            "iso3": "TUR",
            "affectedcountries": ["Türkiye"],
            "iscurrent": True,
            "istemporary": False,
            "todate": "2026-09-15T01:00:00",
            "datemodified": "2026-09-16T02:00:00",
            "unselected": {"complete": [1, 2, 3]},
        },
        "provider_extension": {"nested": ["preserve", "all"]},
    }


@pytest.fixture
def bronze_output(
    tmp_path: Path,
    bronze_request: BronzeRequest,
    gdacs_record: dict[str, Any],
    ingested_at: datetime,
) -> BronzeWriteResult:
    return BronzeWriter(tmp_path / "bronze").write(
        request=bronze_request,
        raw_records=[gdacs_record],
        ingested_at=ingested_at,
    )
