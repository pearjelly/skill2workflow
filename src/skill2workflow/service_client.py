"""Safe client for authenticated self-hosted service actions."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlsplit, urlunsplit

from .dashboard import RUN_DETAIL_SCHEMA_VERSION, RUN_LIST_SCHEMA_VERSION
from .service import read_service_bearer_token


MAX_SERVICE_ACTION_RESPONSE_BYTES = 64 * 1024
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


class ServiceActionError(ValueError):
    """Raised when a remote service action cannot be completed safely."""

    def __init__(self, message: str = "service action unavailable", status_code: int = 0):
        super().__init__(message)
        self.status_code = int(status_code)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def post_run_resume(
    service_url: str,
    token_file: Path,
    run_id: str,
    approved: bool,
) -> Dict[str, object]:
    """Approve or reject one waiting run through the authenticated service."""

    if not isinstance(approved, bool):
        raise ValueError("approved must be a boolean")
    normalized_run_id = _validate_run_id(run_id)
    payload = _post_json(
        service_url,
        token_file,
        f"/runs/{normalized_run_id}/resume",
        {"approved": approved},
        conflict_message="run is not waiting",
    )
    if (
        set(payload) != {"run_id", "status", "approved"}
        or payload.get("run_id") != normalized_run_id
        or not isinstance(payload.get("status"), str)
        or not payload.get("status")
        or not isinstance(payload.get("approved"), bool)
        or payload.get("approved") != approved
    ):
        raise ServiceActionError()
    return payload


def post_run_cancel(
    service_url: str,
    token_file: Path,
    run_id: str,
) -> Dict[str, object]:
    """Request cooperative cancellation for one published run."""

    normalized_run_id = _validate_run_id(run_id)
    payload = _post_json(
        service_url,
        token_file,
        f"/runs/{normalized_run_id}/cancel",
        {},
        conflict_message="run cannot be cancelled",
    )
    if (
        set(payload) != {"run_id", "status"}
        or payload.get("run_id") != normalized_run_id
        or not isinstance(payload.get("status"), str)
        or not payload.get("status")
    ):
        raise ServiceActionError()
    return payload


def fetch_run_detail(
    service_url: str,
    token_file: Path,
    run_id: str,
) -> Dict[str, object]:
    """Fetch one authenticated, redacted operator detail projection."""

    normalized_run_id = _validate_run_id(run_id)
    payload = _get_json(
        service_url,
        token_file,
        f"/runs/{normalized_run_id}",
        conflict_message="run detail unavailable",
    )
    _validate_run_detail(payload, normalized_run_id)
    return payload


def fetch_run_list(
    service_url: str,
    token_file: Path,
) -> Dict[str, object]:
    """Fetch the bounded, authenticated run-discovery projection."""

    payload = _get_json(
        service_url,
        token_file,
        "/runs",
        conflict_message="run list unavailable",
    )
    _validate_run_list(payload)
    return payload


def service_endpoint(service_url: str, path: str) -> str:
    """Build one path under an unambiguous service origin."""

    if not isinstance(path, str) or not path.startswith("/") or "?" in path or "#" in path:
        raise ValueError("service URL must be an unambiguous HTTPS or loopback HTTP origin")
    try:
        parsed = urlsplit(str(service_url))
        port = parsed.port
    except ValueError as error:
        raise ValueError("service URL must be an unambiguous HTTPS or loopback HTTP origin") from error
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or (parsed.scheme == "http" and parsed.hostname not in _LOOPBACK_HOSTS)
    ):
        raise ValueError("service URL must be an unambiguous HTTPS or loopback HTTP origin")
    netloc = parsed.hostname
    if ":" in netloc and not netloc.startswith("["):
        netloc = f"[{netloc}]"
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunsplit((parsed.scheme, netloc, path, "", ""))


def _post_json(
    service_url: str,
    token_file: Path,
    path: str,
    payload: Dict[str, object],
    conflict_message: str,
) -> Dict[str, object]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _request_json(
        service_url,
        token_file,
        path,
        method="POST",
        body=body,
        conflict_message=conflict_message,
    )


def _get_json(
    service_url: str,
    token_file: Path,
    path: str,
    conflict_message: str,
) -> Dict[str, object]:
    return _request_json(
        service_url,
        token_file,
        path,
        method="GET",
        body=None,
        conflict_message=conflict_message,
    )


def _request_json(
    service_url: str,
    token_file: Path,
    path: str,
    *,
    method: str,
    body: Optional[bytes],
    conflict_message: str,
) -> Dict[str, object]:
    endpoint = service_endpoint(service_url, path)
    token = read_service_bearer_token(token_file)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if body is not None:
        headers.update(
            {
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            }
        )
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers=headers,
        method=method,
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirect,
    )
    try:
        with opener.open(request, timeout=5) as response:
            if response.status != 200 or not _safe_json_response_headers(response):
                raise ServiceActionError(status_code=int(response.status))
            return _decode_response(response)
    except urllib.error.HTTPError as error:
        try:
            status_code = int(error.code)
        finally:
            error.close()
        raise ServiceActionError(
            _error_message(status_code, conflict_message),
            status_code=status_code,
        ) from error
    except ServiceActionError:
        raise
    except (OSError, urllib.error.URLError, TimeoutError) as error:
        raise ServiceActionError() from error


def _validate_run_detail(payload: Dict[str, object], run_id: str) -> None:
    """Reject responses outside the reviewed redacted detail contract."""

    if set(payload) != {"schema_version", "run", "events", "window"}:
        raise ServiceActionError()
    if payload.get("schema_version") != RUN_DETAIL_SCHEMA_VERSION:
        raise ServiceActionError()
    run = payload.get("run")
    if not isinstance(run, dict) or set(run) != {
        "run_id", "workflow_id", "workflow_version", "status", "current_node",
        "event_count", "node_result_count", "node_overlays", "created_at", "updated_at",
    }:
        raise ServiceActionError()
    if run.get("run_id") != run_id or any(
        not isinstance(run.get(field), str)
        for field in ("run_id", "workflow_id", "workflow_version", "status", "current_node", "created_at", "updated_at")
    ):
        raise ServiceActionError()
    if any(
        isinstance(run.get(field), bool) or not isinstance(run.get(field), int) or run.get(field) < 0
        for field in ("event_count", "node_result_count")
    ):
        raise ServiceActionError()
    overlays = run.get("node_overlays")
    if not isinstance(overlays, dict) or any(
        not isinstance(node_id, str) or not isinstance(overlay, dict)
        or set(overlay) != {
            "node_id", "status", "current", "event_count", "latest_event_type", "result_status",
            "attempts", "max_attempts", "retry_count", "recovered", "connector_id", "connector_kind",
            "connector_status", "audit_event_count", "has_error",
        }
        or overlay.get("node_id") != node_id
        or any(
            not isinstance(overlay.get(field), str)
            for field in ("node_id", "status", "latest_event_type", "result_status", "connector_id", "connector_kind", "connector_status")
        )
        or any(
            isinstance(overlay.get(field), bool) or not isinstance(overlay.get(field), int) or overlay.get(field) < 0
            for field in ("event_count", "attempts", "max_attempts", "retry_count", "audit_event_count")
        )
        or any(not isinstance(overlay.get(field), bool) for field in ("current", "recovered", "has_error"))
        for node_id, overlay in overlays.items()
    ):
        raise ServiceActionError()
    events = payload.get("events")
    if not isinstance(events, list) or any(
        not isinstance(event, dict)
        or set(event) - {
            "sequence", "type", "node_id", "timestamp", "approved", "attempt", "max_attempts",
            "connector_id", "connector_kind", "connector_status", "has_error",
        }
        or not isinstance(event.get("sequence"), int) or isinstance(event.get("sequence"), bool)
        or not isinstance(event.get("type"), str) or not isinstance(event.get("has_error"), bool)
        or any(field in event and not isinstance(event.get(field), str) for field in ("node_id", "timestamp", "connector_id", "connector_kind", "connector_status"))
        or any(field in event and (isinstance(event.get(field), bool) or not isinstance(event.get(field), int) or event.get(field) < 0) for field in ("attempt", "max_attempts"))
        or ("approved" in event and not isinstance(event.get("approved"), bool))
        for event in events
    ):
        raise ServiceActionError()
    window = payload.get("window")
    if (
        not isinstance(window, dict)
        or set(window) != {"max_events", "total", "returned", "truncated"}
        or any(isinstance(window.get(field), bool) or not isinstance(window.get(field), int) or window.get(field) < 0 for field in ("max_events", "total", "returned"))
        or window.get("max_events") < 1 or window.get("max_events") > 50
        or window.get("returned") > window.get("max_events")
        or not isinstance(window.get("truncated"), bool)
        or window.get("returned") != len(events)
        or window.get("returned") > window.get("total")
        or window.get("truncated") != (window.get("returned") < window.get("total"))
    ):
        raise ServiceActionError()


def _validate_run_list(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed redacted run-list contract."""

    if set(payload) != {"schema_version", "summary", "runs", "window"}:
        raise ServiceActionError()
    if payload.get("schema_version") != RUN_LIST_SCHEMA_VERSION:
        raise ServiceActionError()
    summary = payload.get("summary")
    statuses = {"created", "running", "waiting", "completed", "failed", "cancelled", "interrupted", "other"}
    if (
        not isinstance(summary, dict)
        or set(summary) != {"total", "status_counts"}
        or not _is_non_negative_integer(summary.get("total"))
        or not isinstance(summary.get("status_counts"), dict)
        or set(summary["status_counts"]) != statuses
        or any(not _is_non_negative_integer(value) for value in summary["status_counts"].values())
        or sum(summary["status_counts"].values()) != summary["total"]
    ):
        raise ServiceActionError()
    runs = payload.get("runs")
    run_fields = {"run_id", "workflow_id", "workflow_version", "status", "current_node", "event_count", "node_result_count"}
    if not isinstance(runs, list) or any(
        not isinstance(run, dict)
        or set(run) != run_fields
        or not _is_safe_run_identifier(run.get("run_id"))
        or any(not isinstance(run.get(field), str) for field in ("run_id", "workflow_id", "workflow_version", "status", "current_node"))
        or run.get("status") not in statuses
        or any(not _is_non_negative_integer(run.get(field)) for field in ("event_count", "node_result_count"))
        for run in runs
    ):
        raise ServiceActionError()
    window = payload.get("window")
    if (
        not isinstance(window, dict)
        or set(window) != {"max_items", "total", "returned", "truncated"}
        or not _is_non_negative_integer(window.get("max_items"))
        or window.get("max_items") < 1 or window.get("max_items") > 100
        or not _is_non_negative_integer(window.get("total"))
        or not _is_non_negative_integer(window.get("returned"))
        or window.get("returned") != len(runs)
        or window.get("returned") > window.get("total")
        or window.get("returned") > window.get("max_items")
        or not isinstance(window.get("truncated"), bool)
        or window.get("truncated") != (window.get("returned") < window.get("total"))
        or window.get("total") != summary.get("total")
    ):
        raise ServiceActionError()


def _is_non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_safe_run_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("run_")
        and 5 <= len(value) <= 128
        and all(char.isalnum() or char in {"_", "-"} for char in value)
    )


def _safe_json_response_headers(response) -> bool:
    declared_lengths = response.headers.get_all("Content-Length", [])
    if len(declared_lengths) > 1:
        return False
    if declared_lengths:
        try:
            declared_length = int(declared_lengths[0])
        except (TypeError, ValueError):
            return False
        if declared_length < 0 or declared_length > MAX_SERVICE_ACTION_RESPONSE_BYTES:
            return False
    return (
        response.headers.get_content_type() == "application/json"
        and not response.headers.get("Content-Encoding", "")
        and "no-store" in response.headers.get("Cache-Control", "").lower()
    )


def _decode_response(response) -> Dict[str, object]:
    body = response.read(MAX_SERVICE_ACTION_RESPONSE_BYTES + 1)
    if len(body) > MAX_SERVICE_ACTION_RESPONSE_BYTES:
        raise ServiceActionError()
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ServiceActionError() from error
    if not isinstance(payload, dict):
        raise ServiceActionError()
    return payload


def _validate_run_id(run_id: str) -> str:
    value = str(run_id)
    if (
        not value.startswith("run_")
        or len(value) > 128
        or any(not (char.isalnum() or char in {"_", "-"}) for char in value)
    ):
        raise ValueError("run_id must be a safe run identifier")
    return value


def _error_message(status_code: int, conflict_message: str) -> str:
    return {
        400: "invalid service action",
        401: "authentication required",
        404: "run not found",
        409: conflict_message,
        413: "service action body is too large",
        503: "service unavailable",
    }.get(status_code, "service action failed")
