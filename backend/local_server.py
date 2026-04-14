"""Local HTTP server for development — mirrors the Lambda routing without SAM.

Usage:
    pip install -r requirements.txt
    cp .env.example .env   # fill in your DB credentials
    python local_server.py

The server listens on http://localhost:3001
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

# Add project root to sys.path so imports resolve the same as in Lambda
sys.path.insert(0, os.path.dirname(__file__))

from handlers import health, usage, impact, roi  # noqa: E402


_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Api-Key,Authorization",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}

PORT = int(os.environ.get("LOCAL_PORT", 3001))


def _send_json(handler: BaseHTTPRequestHandler, status: int, body: dict) -> None:
    payload = json.dumps(body).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    for k, v in _CORS_HEADERS.items():
        handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(payload)


def _extract_params(qs: dict) -> dict:
    org_id_raw = (qs.get("org_id") or [None])[0]
    start_date = (qs.get("start_date") or [""])[0]
    end_date = (qs.get("end_date") or [""])[0]

    if not org_id_raw:
        raise ValueError("org_id is required")
    try:
        org_id = int(org_id_raw)
    except (TypeError, ValueError):
        raise ValueError("org_id must be an integer")

    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required (YYYY-MM-DD)")

    return {"org_id": org_id, "start_date": start_date, "end_date": end_date}


def _is_authenticated(headers: dict) -> bool:
    expected_key = os.environ.get("DASHBOARD_API_KEY", "")
    if not expected_key:
        return True
    provided = headers.get("X-Api-Key") or headers.get("x-api-key", "")
    return provided == expected_key


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # suppress default access log
        print(f"  {self.command} {self.path} → {args[1] if len(args) > 1 else ''}")

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        headers = dict(self.headers)

        if not _is_authenticated(headers):
            _send_json(self, 401, {"error": "Unauthorized"})
            return

        try:
            if path == "/health":
                _send_json(self, 200, health.handle())
                return

            params = _extract_params(qs)

            if path == "/api/v1/usage":
                _send_json(self, 200, usage.handle(params))
            elif path == "/api/v1/impact":
                _send_json(self, 200, impact.handle(params))
            elif path == "/api/v1/roi":
                _send_json(self, 200, roi.handle(params))
            else:
                _send_json(self, 404, {"error": "Not found"})

        except ValueError as exc:
            _send_json(self, 400, {"error": str(exc)})
        except Exception as exc:
            traceback.print_exc()
            _send_json(self, 500, {"error": "Internal server error"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"Local dashboard server running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
