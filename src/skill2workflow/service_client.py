"""Safe client for authenticated self-hosted service actions."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict
from urllib.parse import urlsplit, urlunsplit

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
    endpoint = service_endpoint(service_url, path)
    token = read_service_bearer_token(token_file)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        },
        method="POST",
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
