from __future__ import annotations

"""Anthropic Admin API client for Claude Code usage extraction."""

import json
from typing import Any, Dict, List, Optional, Tuple

import requests

from .logging_utils import log_json

# Legacy Anthropic Admin API endpoints.
# Active runtime now uses Claude Code OpenTelemetry instead of these endpoints.
ORG_ME_PATH = "/v1/organizations/me"
USERS_PATH = "/v1/organizations/users"
INVITES_PATH = "/v1/organizations/invites"
CLAUDE_CODE_ANALYTICS_PATH = "/v1/organizations/usage_report/claude_code"
MESSAGES_USAGE_PATH = "/v1/organizations/usage_report/messages"


class ClaudeCodeReportsError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class ClaudeCodeReportsClient:
    BASE_URL = "https://api.anthropic.com"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str, api_base_url: Optional[str] = None) -> None:
        self.api_key = api_key
        self.api_base_url = (api_base_url or self.BASE_URL).rstrip("/")
        self.session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

    def _request_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
        url = f"{self.api_base_url}{path}"
        try:
            response = self.session.get(url, headers=self._headers(), params=params or {}, timeout=30)
        except requests.RequestException as exc:
            raise ClaudeCodeReportsError(
                f"Claude Code reports request failed: {exc}",
                status_code=None,
                payload={"error": str(exc)},
            ) from exc

        status_code = response.status_code
        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text}

        if not response.ok:
            raise ClaudeCodeReportsError(
                f"Claude Code reports request failed with status {status_code}",
                status_code=status_code,
                payload=payload,
            )
        return status_code, payload

    def fetch_claude_code_analytics(
        self,
        *,
        starting_at: str,
        limit: int = 1000,
        path_override: Optional[str] = None,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Fetch Claude Code analytics (sessions, tokens, costs, tool usage) per user/day.

        Endpoint: GET /v1/organizations/usage_report/claude_code
        Param starting_at: YYYY-MM-DD  (data available with up to 1-hour delay)
        Pagination: opaque cursor via 'page' param + 'next_page' in response.
        """
        path = path_override or CLAUDE_CODE_ANALYTICS_PATH

        all_records: List[Dict[str, Any]] = []
        page_cursor: Optional[str] = None
        last_status_code = 200

        while True:
            params: Dict[str, Any] = {"starting_at": starting_at, "limit": limit}
            if page_cursor:
                params["page"] = page_cursor

            last_status_code, payload = self._request_json(path, params)

            if not isinstance(payload, dict):
                break

            page_data = payload.get("data")
            if isinstance(page_data, list):
                all_records.extend([item for item in page_data if isinstance(item, dict)])

            next_page = payload.get("next_page")
            if not next_page:
                break
            page_cursor = str(next_page)

        return last_status_code, all_records

    def fetch_current_organization(self) -> Tuple[int, Dict[str, Any]]:
        """Fetch the organization bound to the current admin API key."""
        status_code, payload = self._request_json(ORG_ME_PATH)
        return status_code, payload if isinstance(payload, dict) else {}

    def fetch_organization_users(
        self,
        *,
        limit: int = 1000,
        email: Optional[str] = None,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Fetch organization members using cursor pagination."""
        all_users: List[Dict[str, Any]] = []
        after_id: Optional[str] = None
        last_status_code = 200

        while True:
            params: Dict[str, Any] = {"limit": limit}
            if after_id:
                params["after_id"] = after_id
            if email:
                params["email"] = email

            last_status_code, payload = self._request_json(USERS_PATH, params)

            if not isinstance(payload, dict):
                break

            page_data = payload.get("data")
            if isinstance(page_data, list):
                all_users.extend([item for item in page_data if isinstance(item, dict)])

            has_more = bool(payload.get("has_more"))
            last_id = payload.get("last_id")
            if not has_more or not last_id:
                break
            after_id = str(last_id)

        return last_status_code, all_users

    def fetch_organization_invites(
        self,
        *,
        limit: int = 1000,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Fetch organization invites using cursor pagination."""
        all_invites: List[Dict[str, Any]] = []
        after_id: Optional[str] = None
        last_status_code = 200

        while True:
            params: Dict[str, Any] = {"limit": limit}
            if after_id:
                params["after_id"] = after_id

            last_status_code, payload = self._request_json(INVITES_PATH, params)

            if not isinstance(payload, dict):
                break

            page_data = payload.get("data")
            if isinstance(page_data, list):
                all_invites.extend([item for item in page_data if isinstance(item, dict)])

            has_more = bool(payload.get("has_more"))
            last_id = payload.get("last_id")
            if not has_more or not last_id:
                break
            after_id = str(last_id)

        return last_status_code, all_invites

    def fetch_messages_usage(
        self,
        *,
        starting_at: str,
        ending_at: Optional[str] = None,
        bucket_width: str = "1d",
        limit: int = 31,
        group_by: Optional[List[str]] = None,
        path_override: Optional[str] = None,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Fetch aggregated messages token/cost usage buckets for the org.

        Endpoint: GET /v1/organizations/usage_report/messages
        Param starting_at: RFC 3339 timestamp (e.g. 2026-03-01T00:00:00Z)
        Param bucket_width: '1d', '1h', or '1m'
        """
        path = path_override or MESSAGES_USAGE_PATH

        params: Dict[str, Any] = {
            "starting_at": starting_at,
            "bucket_width": bucket_width,
            "limit": limit,
        }
        if ending_at:
            params["ending_at"] = ending_at
        if group_by:
            params["group_by"] = group_by

        last_status_code, payload = self._request_json(path, params)

        records: List[Dict[str, Any]] = []
        if isinstance(payload, dict):
            page_data = payload.get("data")
            if isinstance(page_data, list):
                records = [item for item in page_data if isinstance(item, dict)]

        return last_status_code, records

    def log_failure(
        self,
        *,
        note: str,
        path: str,
        status_code: Optional[int],
        payload: Any,
    ) -> None:
        log_json(
            "warning",
            "claude_code_reports",
            note,
            status="failed",
            extra={
                "path": path,
                "http_status": status_code,
                "payload": json.dumps(payload) if payload is not None else None,
            },
        )

__all__ = [
    "ClaudeCodeReportsClient",
    "ClaudeCodeReportsError",
    "ORG_ME_PATH",
    "USERS_PATH",
    "INVITES_PATH",
    "CLAUDE_CODE_ANALYTICS_PATH",
    "MESSAGES_USAGE_PATH",
]
