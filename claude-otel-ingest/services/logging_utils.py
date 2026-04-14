"""Structured logging helpers optimized for Amazon CloudWatch."""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_INVOCATION_CONTEXT: Dict[str, Optional[Any]] = {}
_RUNTIME_CONTEXT: Dict[str, Any] = {
    "function_name": os.environ.get("AWS_LAMBDA_FUNCTION_NAME"),
    "function_version": os.environ.get("AWS_LAMBDA_FUNCTION_VERSION"),
    "log_group": os.environ.get("AWS_LAMBDA_LOG_GROUP_NAME"),
    "log_stream": os.environ.get("AWS_LAMBDA_LOG_STREAM_NAME"),
    "aws_region": os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"),
}


def _current_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def set_invocation_context(
    *,
    context: Optional[Any] = None,
    event: Optional[Any] = None,
    request_id: Optional[str] = None,
) -> None:
    if context is not None and getattr(context, "aws_request_id", None):
        _INVOCATION_CONTEXT["request_id"] = context.aws_request_id

    if request_id:
        _INVOCATION_CONTEXT["request_id"] = request_id

    if event and isinstance(event, dict):
        event_org = event.get("organization_id")
        event_user = event.get("user_id")
        if event_org is not None:
            _INVOCATION_CONTEXT["organization_id"] = event_org
        if event_user is not None:
            _INVOCATION_CONTEXT["user_id"] = event_user


def log_json(
    level: str,
    log_type: str,
    message: str,
    *,
    status: Optional[str] = None,
    code: Optional[str] = None,
    request_id: Optional[str] = None,
    traceback: Optional[str] = None,
    duration_ms: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    **additional_fields: Any,
) -> None:
    payload = OrderedDict()

    base_fields = [
        ("message", message),
        ("type", log_type),
        ("timestamp", _current_timestamp()),
        ("level", level),
        ("status", status),
        ("request_id", request_id if request_id is not None else _INVOCATION_CONTEXT.get("request_id")),
        ("organization_id", _INVOCATION_CONTEXT.get("organization_id")),
        ("user_id", _INVOCATION_CONTEXT.get("user_id")),
        ("code", code),
        ("duration_ms", duration_ms),
        ("traceback", traceback),
    ]

    for key, value in base_fields:
        if value is not None:
            payload[key] = value

    for key, value in additional_fields.items():
        if value is not None:
            payload[key] = value

    if extra:
        for key, value in extra.items():
            if value is not None:
                payload[key] = value

    runtime_context = {key: value for key, value in _RUNTIME_CONTEXT.items() if value is not None}
    if runtime_context:
        payload["runtime"] = runtime_context

    print(json.dumps(payload, separators=(",", ":")))


__all__ = ["log_json", "set_invocation_context"]
