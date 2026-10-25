"""P1-1 JSON logging tests (CLAUDE.md §16, N3 groundwork)."""

import asyncio
import io
import json
import logging

import pytest

from app.core.logging import REDACTED, log_context, request_id_var, setup_logging


@pytest.fixture
def stream() -> io.StringIO:
    buf = io.StringIO()
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    setup_logging(stream=buf)
    yield buf
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


def lines(buf: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in buf.getvalue().splitlines() if line]


def test_emits_one_json_object_per_line(stream: io.StringIO) -> None:
    logging.getLogger("clouddesk.test").info("hello %s", "world")
    [record] = lines(stream)
    assert record["message"] == "hello world"
    assert record["level"] == "INFO"
    assert record["logger"] == "clouddesk.test"
    assert record["timestamp"].endswith("+00:00")
    assert record["request_id"] is None
    assert record["workflow_id"] is None


def test_context_ids_on_every_line(stream: io.StringIO) -> None:
    log = logging.getLogger("clouddesk.test")
    with log_context(request_id="req-1", workflow_id="wf-1"):
        log.info("inside")
        with log_context(workflow_id="wf-2"):
            log.info("nested")
    log.info("outside")
    inside, nested, outside = lines(stream)
    assert (inside["request_id"], inside["workflow_id"]) == ("req-1", "wf-1")
    assert (nested["request_id"], nested["workflow_id"]) == ("req-1", "wf-2")
    assert (outside["request_id"], outside["workflow_id"]) == (None, None)


def test_context_reaches_async_tasks(stream: io.StringIO) -> None:
    async def work() -> None:
        logging.getLogger("clouddesk.test").info("from task")

    async def main() -> None:
        request_id_var.set("req-async")
        await asyncio.create_task(work())

    asyncio.run(main())
    assert lines(stream)[0]["request_id"] == "req-async"


def test_extra_fields_included_and_secrets_redacted(stream: io.StringIO) -> None:
    logging.getLogger("clouddesk.test").info(
        "tool call",
        extra={"tool": "get_customer", "duration_ms": 12, "api_key": "sk-123", "password": "x"},
    )
    [record] = lines(stream)
    assert record["tool"] == "get_customer"
    assert record["duration_ms"] == 12
    assert record["api_key"] == REDACTED
    assert record["password"] == REDACTED
    assert "sk-123" not in stream.getvalue()


def test_exceptions_are_serialised(stream: io.StringIO) -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        logging.getLogger("clouddesk.test").exception("failed")
    [record] = lines(stream)
    assert "ValueError: boom" in record["exception"]


def test_setup_is_idempotent(stream: io.StringIO) -> None:
    setup_logging(stream=stream)
    logging.getLogger("clouddesk.test").info("once")
    assert len(lines(stream)) == 1
