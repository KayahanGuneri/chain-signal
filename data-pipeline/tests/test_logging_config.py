import json
import logging

from chainsignal_pipeline.logging_config import JsonFormatter


def test_json_formatter_includes_structured_fields() -> None:
    record = logging.LogRecord(
        name="chainsignal.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="GDACS fetch completed",
        args=(),
        exc_info=None,
    )

    record.event = "gdacs_fetch_completed"
    record.source = "gdacs"
    record.record_count = 53

    formatter = JsonFormatter()

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "chainsignal.test"
    assert payload["message"] == "GDACS fetch completed"
    assert payload["event"] == "gdacs_fetch_completed"
    assert payload["source"] == "gdacs"
    assert payload["record_count"] == 53
