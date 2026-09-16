from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SourceWindow:
    """Inclusive time window requested from an external source."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.start.utcoffset() is None:
            raise ValueError("Source window start must be timezone-aware")

        if self.end.tzinfo is None or self.end.utcoffset() is None:
            raise ValueError("Source window end must be timezone-aware")

        if self.start > self.end:
            raise ValueError("Source window start must not be after end")


class SourceAdapter(ABC):
    """Contract implemented by external source adapters."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the stable ChainSignal source name."""

    @abstractmethod
    def fetch(
        self,
        window: SourceWindow,
    ) -> list[dict[str, Any]]:
        """Fetch raw source records for the requested window."""
