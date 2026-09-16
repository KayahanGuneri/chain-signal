from datetime import UTC, datetime

import pytest

from chainsignal_pipeline.sources.base import SourceWindow


def test_source_window_accepts_valid_range() -> None:
    start = datetime(
        2026,
        9,
        8,
        tzinfo=UTC,
    )

    end = datetime(
        2026,
        9,
        15,
        tzinfo=UTC,
    )

    window = SourceWindow(
        start=start,
        end=end,
    )

    assert window.start == start
    assert window.end == end


def test_source_window_rejects_naive_start() -> None:
    start = datetime(
        2026,
        9,
        8,
    )

    end = datetime(
        2026,
        9,
        15,
        tzinfo=UTC,
    )

    with pytest.raises(
        ValueError,
        match="Source window start must be timezone-aware",
    ):
        SourceWindow(
            start=start,
            end=end,
        )


def test_source_window_rejects_naive_end() -> None:
    start = datetime(
        2026,
        9,
        8,
        tzinfo=UTC,
    )

    end = datetime(
        2026,
        9,
        15,
    )

    with pytest.raises(
        ValueError,
        match="Source window end must be timezone-aware",
    ):
        SourceWindow(
            start=start,
            end=end,
        )


def test_source_window_rejects_reversed_range() -> None:
    start = datetime(
        2026,
        9,
        15,
        tzinfo=UTC,
    )

    end = datetime(
        2026,
        9,
        8,
        tzinfo=UTC,
    )

    with pytest.raises(
        ValueError,
        match="Source window start must not be after end",
    ):
        SourceWindow(
            start=start,
            end=end,
        )
