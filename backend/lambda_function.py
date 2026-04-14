"""AI Governance Dashboard — Lambda entry point.

Routes API Gateway GET requests to the appropriate handler.
Auth: X-Api-Key header checked against DASHBOARD_API_KEY env var.
"""

from __future__ import annotations

import json
import os
import traceback
from typing import Any, Dict
from urllib.parse import parse_qs

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

from services.logging_utils import log_json, set_invocation_context
from handlers import health, usage, impact, license_efficiency


_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Api-Key,Authorization",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}


def _response(status_code: int, body: Any, extra_headers: dict | None = None) -> dict:
    headers = {**_CORS_HEADERS, "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body),
    }


def _extract_params(event: dict) -> dict:
    qs = event.get("queryStringParameters") or {}
    org_id_raw = qs.get("org_id")
    start_date = qs.get("start_date", "")
    end_date = qs.get("end_date", "")

    if not org_id_raw:
        raise ValueError("org_id is required")
    try:
        org_id = int(org_id_raw)
    except (TypeError, ValueError):
        raise ValueError("org_id must be an integer")

    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required (YYYY-MM-DD)")

    return {"org_id": org_id, "start_date": start_date, "end_date": end_date}


def _is_authenticated(event: dict) -> bool:
    expected_key = os.environ.get("DASHBOARD_API_KEY", "")
    if not expected_key:
        return True  # no key configured → open (dev mode)

    headers = event.get("headers") or {}
    # API Gateway normalises header names to lowercase
    provided = (
        headers.get("x-api-key")
        or headers.get("X-Api-Key")
        or headers.get("authorization", "").removeprefix("Bearer ").strip()
    )
    return provided == expected_key


def handle_api_gateway_event(event: dict) -> dict:
    rc = event.get("requestContext", {}).get("http", {})
    method = rc.get("method", "").upper()
    path = rc.get("path", "")

    set_invocation_context(event=event)
    log_json("info", "request", f"{method} {path}")

    # CORS preflight
    if method == "OPTIONS":
        return _response(204, "")

    # Auth
    if not _is_authenticated(event):
        return _response(401, {"error": "Unauthorized"})

    # Health — no params required
    if method == "GET" and path == "/health":
        try:
            result = health.handle()
            return _response(200, result)
        except Exception as exc:
            log_json("error", "health", str(exc), traceback=traceback.format_exc())
            return _response(503, {"error": "Service unavailable"})

    # Parameterised endpoints
    if method == "GET":
        try:
            params = _extract_params(event)
        except ValueError as exc:
            return _response(400, {"error": str(exc)})

        try:
            if path == "/api/v1/usage":
                return _response(200, usage.handle(params))
            if path == "/api/v1/impact":
                return _response(200, impact.handle(params))
            if path == "/api/v1/license-efficiency":
                return _response(200, license_efficiency.handle(params))
        except Exception as exc:
            log_json("error", "handler", str(exc), traceback=traceback.format_exc())
            return _response(500, {"error": "Internal server error"})

    return _response(404, {"error": "Not found"})


def lambda_handler(event: dict, context: Any) -> dict:
    set_invocation_context(context=context)

    if event.get("requestContext"):
        return handle_api_gateway_event(event)

    log_json("warn", "request", "Unsupported invocation mode")
    return _response(400, {"error": "Unsupported invocation mode"})
