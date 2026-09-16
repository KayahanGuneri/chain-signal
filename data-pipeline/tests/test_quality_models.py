from collections.abc import MutableMapping
from dataclasses import replace
from typing import cast

import pytest

from chainsignal_pipeline.quality.models import (
    DataQualitySummary,
    QuarantinedRecord,
    QuarantineReason,
)


@pytest.fixture
def summary() -> DataQualitySummary:
    return DataQualitySummary(
        3,
        1,
        1,
        1,
        2,
        {
            QuarantineReason.INVALID_COORDINATES: 1,
            QuarantineReason.INVALID_SEVERITY: 1,
            QuarantineReason.DUPLICATE_CANONICAL_IDENTITY: 1,
        },
    )


def test_summary_allows_multiple_reasons_per_record(summary: DataQualitySummary) -> None:
    assert summary.input_count == summary.valid_count + summary.quarantine_count
    assert summary.quarantine_count == summary.invalid_count + summary.duplicate_count
    assert sum(summary.reason_counts.values()) > summary.quarantine_count
    assert summary.reason_counts_by_code == {
        "INVALID_COORDINATES": 1,
        "INVALID_SEVERITY": 1,
        "DUPLICATE_CANONICAL_IDENTITY": 1,
    }
    assert all(type(code) is str for code in summary.reason_counts_by_code)


@pytest.mark.parametrize(
    "field",
    [
        "input_count",
        "valid_count",
        "invalid_count",
        "duplicate_count",
        "quarantine_count",
    ],
)
def test_negative_summary_counts_rejected(summary: DataQualitySummary, field: str) -> None:
    with pytest.raises(ValueError, match=f"{field} must not be negative"):
        replace(
            summary,
            input_count=-1 if field == "input_count" else summary.input_count,
            valid_count=-1 if field == "valid_count" else summary.valid_count,
            invalid_count=-1 if field == "invalid_count" else summary.invalid_count,
            duplicate_count=-1 if field == "duplicate_count" else summary.duplicate_count,
            quarantine_count=-1 if field == "quarantine_count" else summary.quarantine_count,
        )


@pytest.mark.parametrize(
    "field,message",
    [
        ("input_count", "input_count must equal"),
        ("invalid_count", "quarantine_count must equal"),
    ],
)
def test_summary_invariants_rejected(summary: DataQualitySummary, field: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        replace(
            summary,
            input_count=99 if field == "input_count" else summary.input_count,
            invalid_count=99 if field == "invalid_count" else summary.invalid_count,
        )


def test_reason_counts_are_normalized_and_defensively_immutable() -> None:
    counts = {QuarantineReason.INVALID_COORDINATES: 1, QuarantineReason.INVALID_SEVERITY: 0}
    summary = DataQualitySummary(1, 0, 1, 0, 1, counts)
    counts[QuarantineReason.INVALID_COORDINATES] = 99
    assert summary.reason_counts_by_code == {"INVALID_COORDINATES": 1}
    with pytest.raises(TypeError):
        cast(MutableMapping[QuarantineReason, int], summary.reason_counts)[
            QuarantineReason.INVALID_COORDINATES
        ] = 2
    exported = summary.reason_counts_by_code
    exported.clear()
    assert summary.reason_counts_by_code == {"INVALID_COORDINATES": 1}


def test_negative_reason_count_rejected(summary: DataQualitySummary) -> None:
    with pytest.raises(ValueError, match="reason counts must not be negative"):
        replace(summary, reason_counts={QuarantineReason.INVALID_SEVERITY: -1})


@pytest.mark.parametrize(
    "index,reasons,message",
    [
        (-1, (QuarantineReason.INVALID_COORDINATES,), "record_index"),
        (0, (), "at least one reason"),
        (
            0,
            (QuarantineReason.INVALID_COORDINATES, QuarantineReason.INVALID_COORDINATES),
            "duplicates",
        ),
    ],
)
def test_quarantine_invariants(
    index: int,
    reasons: tuple[QuarantineReason, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        QuarantinedRecord(index, {}, reasons)
