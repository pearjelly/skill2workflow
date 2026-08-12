"""Safe client and private output helpers for live operator snapshots."""

from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict
from urllib.parse import urlsplit, urlunsplit

from .dashboard import MAX_LIVE_SNAPSHOT_BYTES, SNAPSHOT_SCHEMA_VERSION
from .service import read_service_bearer_token


_SNAPSHOT_PATH = "/api/v1/control-snapshot"
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def fetch_live_control_snapshot(service_url: str, token_file: Path) -> Dict[str, object]:
    """Fetch one bounded snapshot without placing the Bearer token in argv."""

    endpoint = _snapshot_endpoint(service_url)
    token = read_service_bearer_token(token_file)
    request = urllib.request.Request(
        endpoint,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirect,
        ).open(request, timeout=5) as response:
            content_type = response.headers.get_content_type()
            content_encoding = response.headers.get("Content-Encoding", "")
            cache_control = response.headers.get("Cache-Control", "")
            declared_lengths = response.headers.get_all("Content-Length", [])
            if len(declared_lengths) > 1:
                raise ValueError("live control snapshot unavailable")
            if declared_lengths:
                try:
                    declared_length = int(declared_lengths[0])
                    if declared_length < 0 or declared_length > MAX_LIVE_SNAPSHOT_BYTES:
                        raise ValueError("live control snapshot unavailable")
                except ValueError as error:
                    raise ValueError("live control snapshot unavailable") from error
            if (
                response.status != 200
                or content_type != "application/json"
                or content_encoding
                or "no-store" not in cache_control.lower()
            ):
                raise ValueError("live control snapshot unavailable")
            body = response.read(MAX_LIVE_SNAPSHOT_BYTES + 1)
    except ValueError:
        raise
    except (OSError, urllib.error.URLError) as error:
        if isinstance(error, urllib.error.HTTPError):
            error.close()
        raise ValueError("live control snapshot unavailable") from error
    if len(body) > MAX_LIVE_SNAPSHOT_BYTES:
        raise ValueError("live control snapshot unavailable")
    try:
        snapshot = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("live control snapshot unavailable") from error
    _validate_snapshot(snapshot)
    return snapshot


def write_private_snapshot(path: Path, snapshot: Dict[str, object]) -> None:
    """Atomically publish a snapshot as an owner-only regular file."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        dir=str(output.parent),
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
        output.chmod(0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _snapshot_endpoint(service_url: str) -> str:
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
    return urlunsplit((parsed.scheme, netloc, _SNAPSHOT_PATH, "", ""))


def _validate_snapshot(snapshot) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("live control snapshot unavailable")
    object_fields = ("summary", "operator_insights", "window")
    list_fields = (
        "workflows",
        "runs",
        "audit_events",
        "connectors",
        "version_comparisons",
    )
    if any(not isinstance(snapshot.get(field), dict) for field in object_fields) or any(
        not isinstance(snapshot.get(field), list) for field in list_fields
    ):
        raise ValueError("live control snapshot unavailable")
    if any(
        not all(isinstance(item, dict) for item in snapshot[field])
        for field in list_fields
    ):
        raise ValueError("live control snapshot unavailable")
    summary = snapshot["summary"]
    summary_counts = {
        "workflows": "workflow_count",
        "runs": "run_count",
        "audit_events": "audit_event_count",
        "connectors": "connector_count",
    }
    for summary_key in summary_counts.values():
        if not _is_non_negative_integer(summary.get(summary_key)):
            raise ValueError("live control snapshot unavailable")
    for map_key, total_key in (
        ("status_counts", "workflow_count"),
        ("run_status_counts", "run_count"),
    ):
        counts = summary.get(map_key)
        if (
            not isinstance(counts, dict)
            or any(
                not isinstance(key, str) or not _is_non_negative_integer(value)
                for key, value in counts.items()
            )
            or sum(counts.values()) != summary[total_key]
        ):
            raise ValueError("live control snapshot unavailable")
    max_items = snapshot["window"].get("max_items")
    if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items <= 0:
        raise ValueError("live control snapshot unavailable")
    for field in list_fields:
        window = snapshot["window"].get(field)
        if not isinstance(window, dict):
            raise ValueError("live control snapshot unavailable")
        total = window.get("total")
        returned = window.get("returned")
        truncated = window.get("truncated")
        if (
            not _is_non_negative_integer(total)
            or not _is_non_negative_integer(returned)
            or not isinstance(truncated, bool)
            or returned != len(snapshot[field])
            or returned > total
            or returned > max_items
            or truncated != (returned < total)
        ):
            raise ValueError("live control snapshot unavailable")
        summary_key = summary_counts.get(field)
        if summary_key and total != summary[summary_key]:
            raise ValueError("live control snapshot unavailable")


def _is_non_negative_integer(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0
