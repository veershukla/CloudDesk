"""JSON logging with `request_id` and `workflow_id` on every line (CLAUDE.md §16).

Call `setup_logging()` once at startup. Code that knows the current request or workflow binds it
with `log_context(...)` (or `request_id_var` / `workflow_id_var` directly in middleware); every log
record emitted inside that context carries the ids, including records from async tasks spawned
inside it.

Secrets must never reach the logs (CLAUDE.md §9): values passed via `extra=` under a sensitive key
name are replaced with "[REDACTED]".
"""

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
workflow_id_var: ContextVar[str | None] = ContextVar("workflow_id", default=None)

REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
)

# Attributes every LogRecord has; anything else on a record came from `extra=`.
_STANDARD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", (), None)).keys() | {"message", "asctime", "taskName"}
)
_HANDLER_NAME = "clouddesk-json"


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


class ContextFilter(logging.Filter):
    """Copy the current request/workflow ids onto each record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.workflow_id = workflow_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "workflow_id": getattr(record, "workflow_id", None),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS or key in payload:
                continue
            payload[key] = REDACTED if _is_sensitive(key) else value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def setup_logging(level: int | str = logging.INFO, stream: Any = None) -> None:
    """Route all logging (root, uvicorn, libraries) through one JSON handler on stdout.

    Safe to call more than once: the previous CloudDesk handler is replaced, not duplicated.
    """
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    for existing in list(root.handlers):
        if existing.get_name() == _HANDLER_NAME:
            root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)

    # Let uvicorn's loggers flow into the root handler instead of printing plain text.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True


@contextmanager
def log_context(*, request_id: str | None = None, workflow_id: str | None = None) -> Iterator[None]:
    """Bind ids for the duration of a block. Only the ids passed are changed."""
    tokens = []
    if request_id is not None:
        tokens.append((request_id_var, request_id_var.set(request_id)))
    if workflow_id is not None:
        tokens.append((workflow_id_var, workflow_id_var.set(workflow_id)))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)
