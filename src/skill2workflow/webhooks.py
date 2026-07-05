"""Local webhook adapter for published workflow triggers."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Dict
from urllib.parse import unquote, urlsplit


class WebhookError(Exception):
    """Raised when a local webhook request cannot be accepted."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def parse_webhook_request(method: str, path: str, body: bytes) -> Dict[str, object]:
    """Translate a local webhook HTTP request into a trigger request."""

    if str(method).upper() != "POST":
        raise WebhookError("webhook requests must use POST", status_code=405)

    workflow_id, version = _parse_webhook_path(path)
    payload = _parse_json_body(body)
    trigger_input = payload.get("input", {})
    if trigger_input is None:
        trigger_input = {}
    if not isinstance(trigger_input, dict):
        raise WebhookError("webhook input must be a JSON object", status_code=400)

    return {
        "workflow_id": workflow_id,
        "version": version,
        "source": _optional_text(payload, "source") or "local-webhook",
        "idempotency_key": _optional_text(payload, "idempotency_key"),
        "input": trigger_input,
    }


def handle_webhook_request(control_plane, method: str, path: str, body: bytes) -> Dict[str, object]:
    """Trigger a published workflow through the control-plane boundary."""

    return control_plane.trigger_workflow(parse_webhook_request(method, path, body))


def serve_webhook_requests(
    host: str,
    port: int,
    control_plane,
    once: bool = False,
    ready_callback: Callable[[HTTPServer], None] = None,
) -> None:
    """Serve local webhook requests with the Python standard library."""

    handler = _handler_for(control_plane)
    server = HTTPServer((host, int(port)), handler)
    try:
        if ready_callback:
            ready_callback(server)
        if once:
            server.handle_request()
        else:
            server.serve_forever()
    finally:
        server.server_close()


def _handler_for(control_plane):
    class LocalWebhookRequestHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            self._handle_webhook()

        def do_GET(self):
            self._handle_webhook()

        def do_PUT(self):
            self._handle_webhook()

        def do_DELETE(self):
            self._handle_webhook()

        def _handle_webhook(self):
            body = self.rfile.read(_content_length(self))
            try:
                payload = handle_webhook_request(control_plane, self.command, self.path, body)
                self._send_json(200, payload)
            except WebhookError as error:
                self._send_json(error.status_code, {"error": str(error)})
            except ValueError as error:
                self._send_json(400, {"error": str(error)})

        def _send_json(self, status_code: int, payload: Dict[str, object]) -> None:
            data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):
            return

    return LocalWebhookRequestHandler


def _parse_webhook_path(path: str):
    parsed = urlsplit(str(path))
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) != 3 or parts[0] != "webhooks" or not parts[1] or not parts[2]:
        raise WebhookError("webhook path must be /webhooks/<workflow_id>/<version>", status_code=404)
    return parts[1], parts[2]


def _parse_json_body(body: bytes) -> Dict[str, object]:
    if not body:
        return {}
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise WebhookError("webhook body must be valid JSON", status_code=400)
    if not isinstance(payload, dict):
        raise WebhookError("webhook body must be a JSON object", status_code=400)
    return payload


def _optional_text(payload: Dict[str, object], key: str) -> str:
    value = payload.get(key, "")
    if value is None:
        return ""
    return str(value)


def _content_length(handler: BaseHTTPRequestHandler) -> int:
    try:
        return int(handler.headers.get("Content-Length", "0") or "0")
    except ValueError:
        return 0
