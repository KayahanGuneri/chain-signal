from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

REQUEST_CONTRACT_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class BronzeRequest:
    """Identity-bearing description of one external source request."""

    source: str
    window_start: datetime
    window_end: datetime
    request_contract_version: str = REQUEST_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("Bronze request source must not be blank")

        if self.window_start.tzinfo is None or self.window_start.utcoffset() is None:
            raise ValueError("Bronze request window_start must be timezone-aware")

        if self.window_end.tzinfo is None or self.window_end.utcoffset() is None:
            raise ValueError("Bronze request window_end must be timezone-aware")

        if self.window_start > self.window_end:
            raise ValueError("Bronze request window_start must not be after window_end")

        if not self.request_contract_version.strip():
            raise ValueError("Bronze request_contract_version must not be blank")

    @property
    def request_identity(self) -> str:
        """Return the deterministic identity of the logical source request."""

        payload = {
            "source": self.source,
            "window_start": self._normalize_datetime(self.window_start),
            "window_end": self._normalize_datetime(self.window_end),
            "request_contract_version": self.request_contract_version,
        }

        return _sha256_json(payload)

    @staticmethod
    def _normalize_datetime(value: datetime) -> str:
        return value.astimezone(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class BronzeBatchMetadata:
    """Metadata describing one immutable Bronze ingestion batch."""

    source: str
    request_identity: str
    raw_content_hash: str
    batch_id: str
    ingested_at: datetime
    record_count: int

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("Bronze batch source must not be blank")

        if not self.request_identity.strip():
            raise ValueError("Bronze batch request_identity must not be blank")

        if not self.raw_content_hash.strip():
            raise ValueError("Bronze batch raw_content_hash must not be blank")

        if not self.batch_id.strip():
            raise ValueError("Bronze batch_id must not be blank")

        if self.ingested_at.tzinfo is None or self.ingested_at.utcoffset() is None:
            raise ValueError("Bronze batch ingested_at must be timezone-aware")

        if self.record_count < 0:
            raise ValueError("Bronze batch record_count must not be negative")

    @property
    def partition_date(self) -> date:
        """Return the UTC ingestion date used for Bronze partitioning."""

        return self.ingested_at.astimezone(UTC).date()

    @classmethod
    def create(
        cls,
        *,
        request: BronzeRequest,
        raw_records: list[dict[str, Any]],
        ingested_at: datetime,
    ) -> BronzeBatchMetadata:
        raw_content_hash = calculate_raw_content_hash(raw_records)

        batch_id = calculate_batch_id(
            request_identity=request.request_identity,
            raw_content_hash=raw_content_hash,
        )

        return cls(
            source=request.source,
            request_identity=request.request_identity,
            raw_content_hash=raw_content_hash,
            batch_id=batch_id,
            ingested_at=ingested_at,
            record_count=len(raw_records),
        )


def calculate_raw_content_hash(
    raw_records: list[dict[str, Any]],
) -> str:
    """Hash raw records deterministically without interpreting their fields."""

    return _sha256_json(raw_records)


def calculate_batch_id(
    *,
    request_identity: str,
    raw_content_hash: str,
) -> str:
    """Combine logical request identity and raw content identity."""

    return _sha256_json(
        {
            "request_identity": request_identity,
            "raw_content_hash": raw_content_hash,
        }
    )


def _sha256_json(value: object) -> str:
    serialized = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
