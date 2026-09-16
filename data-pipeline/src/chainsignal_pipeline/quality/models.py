from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class QuarantineReason(StrEnum):
    """Stable reason codes for records rejected by canonical normalization."""

    MALFORMED_RECORD = "MALFORMED_RECORD"
    MISSING_SOURCE_EVENT_ID = "MISSING_SOURCE_EVENT_ID"
    UNSUPPORTED_EVENT_TYPE = "UNSUPPORTED_EVENT_TYPE"
    INVALID_OCCURRENCE_TIME = "INVALID_OCCURRENCE_TIME"
    INVALID_COORDINATES = "INVALID_COORDINATES"
    INVALID_SEVERITY = "INVALID_SEVERITY"
    DUPLICATE_CANONICAL_IDENTITY = "DUPLICATE_CANONICAL_IDENTITY"


@dataclass(frozen=True, slots=True)
class QuarantinedRecord:
    """Raw provider record rejected from canonical output."""

    record_index: int
    raw_record: dict[str, Any]
    reasons: tuple[QuarantineReason, ...]

    def __post_init__(self) -> None:
        if self.record_index < 0:
            raise ValueError("Quarantined record_index must not be negative")

        if not self.reasons:
            raise ValueError("Quarantined record must contain at least one reason")

        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError("Quarantined record reasons must not contain duplicates")


@dataclass(frozen=True, slots=True)
class DataQualitySummary:
    """Batch-level data-quality metrics for one normalization run."""

    input_count: int
    valid_count: int
    invalid_count: int
    duplicate_count: int
    quarantine_count: int
    reason_counts: Mapping[QuarantineReason, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        counts = {
            "input_count": self.input_count,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "duplicate_count": self.duplicate_count,
            "quarantine_count": self.quarantine_count,
        }

        for name, value in counts.items():
            if value < 0:
                raise ValueError(f"Data-quality {name} must not be negative")

        if self.input_count != (self.valid_count + self.quarantine_count):
            raise ValueError("Data-quality input_count must equal valid_count + quarantine_count")

        if self.quarantine_count != (self.invalid_count + self.duplicate_count):
            raise ValueError(
                "Data-quality quarantine_count must equal invalid_count + duplicate_count"
            )

        normalized_reason_counts: dict[
            QuarantineReason,
            int,
        ] = {}

        for reason, count in self.reason_counts.items():
            if count < 0:
                raise ValueError("Data-quality reason counts must not be negative")

            if count > 0:
                normalized_reason_counts[reason] = count

        object.__setattr__(
            self,
            "reason_counts",
            MappingProxyType(normalized_reason_counts),
        )

    @property
    def reason_counts_by_code(self) -> dict[str, int]:
        """Return reason counts with stable string reason codes."""

        return {reason.value: count for reason, count in self.reason_counts.items()}
