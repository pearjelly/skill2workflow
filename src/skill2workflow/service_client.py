"""Safe client for authenticated self-hosted service actions."""

from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import quote, urlsplit, urlunsplit

from .backup import BACKUP_READINESS_SCHEMA_VERSION
from .retention import RETENTION_READINESS_SCHEMA_VERSION
from .operational_readiness import OPERATIONAL_READINESS_SCHEMA_VERSION
from .dashboard import (
    MAX_RECURRING_SCHEDULE_LIST_ITEMS,
    MAX_RECURRING_SCHEDULE_DISPATCH_LIST_ITEMS,
    MAX_REMOTE_WORKFLOW_ARTIFACT_REPORT_ISSUES,
    MAX_WORKFLOW_INVENTORY_ITEMS,
    WORKFLOW_INVENTORY_SCHEMA_VERSION,
    RECURRING_SCHEDULE_DISPATCH_LIST_SCHEMA_VERSION,
    RUN_DETAIL_SCHEMA_VERSION,
    RUN_LIST_SCHEMA_VERSION,
    RECURRING_SCHEDULE_ACTION_SCHEMA_VERSION,
    RECURRING_SCHEDULE_LIST_SCHEMA_VERSION,
    SUPPORT_BUNDLE_SCHEMA_VERSION,
)
from .control_plane import (
    MAX_RUN_AUDIT_REPORT_RUNS,
    MAX_RUN_AUDIT_REPORT_TYPES,
    RUN_AUDIT_REPORT_SCHEMA_VERSION,
    WORKFLOW_ARTIFACT_REPORT_SCHEMA_VERSION,
    WORKFLOW_DIFF_SCHEMA_VERSION,
)
from .service import (
    RUNTIME_INFO_SCHEMA_VERSION,
    SERVICE_SCHEMA_VERSION,
    WORKFLOW_RELEASE_SCHEMA_VERSION,
    WORKFLOW_PROMOTION_SCHEMA_VERSION,
    WORKFLOW_DEPRECATION_SCHEMA_VERSION,
    WORKFLOW_DSL_SCHEMA_VERSION,
    read_service_bearer_token,
)
from .storage import AUDIT_INTEGRITY_ALGORITHM, AUDIT_INTEGRITY_SCHEMA_VERSION
from .triggers import normalize_trigger_request
from .webhooks import MAX_REQUEST_BODY_BYTES


MAX_SERVICE_ACTION_RESPONSE_BYTES = 64 * 1024
MAX_SUPPORT_BUNDLE_RESPONSE_BYTES = 128 * 1024
MAX_AUDIT_CONSISTENCY_RESPONSE_BYTES = 64 * 1024
MAX_RECURRING_SCHEDULE_LIST_RESPONSE_BYTES = 64 * 1024
MAX_RECURRING_SCHEDULE_DISPATCH_LIST_RESPONSE_BYTES = 64 * 1024
MAX_WORKFLOW_ARTIFACT_REPORT_RESPONSE_BYTES = 64 * 1024
MAX_BACKUP_READINESS_RESPONSE_BYTES = 16 * 1024
MAX_RETENTION_READINESS_REQUEST_BYTES = 64 * 1024
MAX_RETENTION_READINESS_RESPONSE_BYTES = 16 * 1024
MAX_OPERATIONAL_READINESS_RESPONSE_BYTES = 16 * 1024
MAX_AUDIT_INTEGRITY_RESPONSE_BYTES = 16 * 1024
MAX_RUNTIME_INFO_RESPONSE_BYTES = 16 * 1024
MAX_REMOTE_TRIGGER_REQUEST_BYTES = MAX_REQUEST_BODY_BYTES
MAX_REMOTE_WORKFLOW_RELEASE_REQUEST_BYTES = MAX_REQUEST_BODY_BYTES
MAX_REMOTE_WORKFLOW_RELEASE_RESPONSE_BYTES = 16 * 1024
MAX_REMOTE_WORKFLOW_PROMOTION_REQUEST_BYTES = MAX_REQUEST_BODY_BYTES
MAX_REMOTE_WORKFLOW_PROMOTION_RESPONSE_BYTES = 16 * 1024
MAX_REMOTE_WORKFLOW_DIFF_RESPONSE_BYTES = 64 * 1024
MAX_REMOTE_WORKFLOW_DEPRECATION_REQUEST_BYTES = MAX_REQUEST_BODY_BYTES
MAX_REMOTE_WORKFLOW_DEPRECATION_RESPONSE_BYTES = 16 * 1024
MAX_REMOTE_WORKFLOW_INVENTORY_RESPONSE_BYTES = 64 * 1024
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
_WORKFLOW_ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")


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


def fetch_recurring_schedule_list(
    service_url: str,
    token_file: Path,
) -> Dict[str, object]:
    """Fetch the bounded, authenticated recurring-schedule projection."""

    payload = _get_json(
        service_url,
        token_file,
        "/api/v1/recurring-schedules",
        conflict_message="recurring schedule list unavailable",
        max_response_bytes=MAX_RECURRING_SCHEDULE_LIST_RESPONSE_BYTES,
    )
    _validate_recurring_schedule_list(payload)
    return payload


def fetch_workflow_artifact_report(
    service_url: str,
    token_file: Path,
) -> Dict[str, object]:
    """Fetch the bounded, authenticated workflow artifact consistency report."""

    payload = _get_json(
        service_url,
        token_file,
        "/api/v1/workflow-artifacts",
        conflict_message="workflow artifact report unavailable",
        max_response_bytes=MAX_WORKFLOW_ARTIFACT_REPORT_RESPONSE_BYTES,
    )
    _validate_workflow_artifact_report(payload)
    return payload


def fetch_workflow_inventory(
    service_url: str,
    token_file: Path,
) -> Dict[str, object]:
    """Fetch bounded published-version metadata without workflow content."""

    payload = _get_json(
        service_url,
        token_file,
        "/api/v1/workflows",
        conflict_message="workflow inventory unavailable",
        max_response_bytes=MAX_REMOTE_WORKFLOW_INVENTORY_RESPONSE_BYTES,
    )
    _validate_workflow_inventory(payload)
    return payload


def fetch_backup_readiness(
    service_url: str,
    token_file: Path,
) -> Dict[str, object]:
    """Fetch the authenticated, read-only offline-backup preflight report."""

    payload = _get_json(
        service_url,
        token_file,
        "/api/v1/backup-readiness",
        conflict_message="backup readiness unavailable",
        max_response_bytes=MAX_BACKUP_READINESS_RESPONSE_BYTES,
    )
    _validate_backup_readiness(payload)
    return payload


def fetch_retention_readiness(
    service_url: str,
    token_file: Path,
    policy: Dict[str, object],
) -> Dict[str, object]:
    """Fetch a policy-bound, authenticated retention preflight."""

    if not isinstance(policy, dict):
        raise ValueError("retention policy must be a JSON object")
    payload = _post_json(
        service_url,
        token_file,
        "/api/v1/retention-readiness",
        {"policy": policy},
        conflict_message="retention readiness unavailable",
        max_request_bytes=MAX_RETENTION_READINESS_REQUEST_BYTES,
        max_response_bytes=MAX_RETENTION_READINESS_RESPONSE_BYTES,
    )
    _validate_retention_readiness(payload)
    return payload


def fetch_operational_readiness(
    service_url: str,
    token_file: Path,
) -> Dict[str, object]:
    """Fetch the authenticated aggregate operator readiness report."""

    payload = _get_json(
        service_url,
        token_file,
        "/api/v1/operational-readiness",
        conflict_message="operational readiness unavailable",
        max_response_bytes=MAX_OPERATIONAL_READINESS_RESPONSE_BYTES,
    )
    _validate_operational_readiness(payload)
    return payload


def fetch_audit_integrity(
    service_url: str,
    token_file: Path,
) -> Dict[str, object]:
    """Fetch the authenticated, payload-free SQLite audit-chain result."""

    payload = _get_json(
        service_url,
        token_file,
        "/api/v1/audit-integrity",
        conflict_message="audit integrity unavailable",
        max_response_bytes=MAX_AUDIT_INTEGRITY_RESPONSE_BYTES,
    )
    _validate_audit_integrity(payload)
    return payload


def fetch_runtime_info(
    service_url: str,
    token_file: Path,
) -> Dict[str, object]:
    """Fetch fixed runtime identity and compatibility metadata."""

    payload = _get_json(
        service_url,
        token_file,
        "/api/v1/runtime-info",
        conflict_message="runtime info unavailable",
        max_response_bytes=MAX_RUNTIME_INFO_RESPONSE_BYTES,
    )
    _validate_runtime_info(payload)
    return payload


def fetch_workflow_diff(
    service_url: str,
    token_file: Path,
    workflow_id: str,
    from_version: str,
    to_version: str,
) -> Dict[str, object]:
    """Fetch a bounded, value-free diff of two published workflow versions."""

    normalized_workflow_id = _validate_workflow_ref(workflow_id, "workflow_id")
    normalized_from = _validate_workflow_ref(from_version, "from_version")
    normalized_to = _validate_workflow_ref(to_version, "to_version")
    payload = _get_json(
        service_url,
        token_file,
        "/api/v1/workflow-diffs/{}/{}/{}".format(
            quote(normalized_workflow_id, safe=""),
            quote(normalized_from, safe=""),
            quote(normalized_to, safe=""),
        ),
        conflict_message="workflow diff unavailable",
        not_found_message="workflow version not found",
        max_response_bytes=MAX_REMOTE_WORKFLOW_DIFF_RESPONSE_BYTES,
    )
    _validate_workflow_diff_response(
        payload,
        workflow_id=normalized_workflow_id,
        from_version=normalized_from,
        to_version=normalized_to,
    )
    return payload


def post_workflow_trigger(
    service_url: str,
    token_file: Path,
    workflow_id: str,
    version: str,
    *,
    idempotency_key: str,
    source: str = "service-cli",
    trigger_input: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Trigger one published workflow through the authenticated service."""

    normalized_workflow_id = _validate_workflow_ref(workflow_id, "workflow_id")
    normalized_version = _validate_workflow_ref(version, "version")
    if not isinstance(idempotency_key, str) or not idempotency_key:
        raise ValueError("idempotency_key is required for remote triggers")
    if (
        not isinstance(source, str)
        or not source
        or len(source) > 128
        or any(ord(char) < 0x20 or ord(char) == 0x7F for char in source)
    ):
        raise ValueError("source must be a non-empty string of at most 128 characters")
    request = normalize_trigger_request(
        {
            "workflow_id": normalized_workflow_id,
            "version": normalized_version,
            "source": source,
            "idempotency_key": idempotency_key,
            "input": {} if trigger_input is None else trigger_input,
        }
    )
    payload = _post_json(
        service_url,
        token_file,
        "/webhooks/{}/{}".format(
            quote(normalized_workflow_id, safe=""),
            quote(normalized_version, safe=""),
        ),
        {
            "source": request["source"],
            "idempotency_key": request["idempotency_key"],
            "input": request["input"],
        },
        conflict_message="trigger idempotency conflict",
        max_request_bytes=MAX_REMOTE_TRIGGER_REQUEST_BYTES,
    )
    _validate_trigger_response(
        payload,
        workflow_id=normalized_workflow_id,
        source=str(request["source"]),
        idempotency_key=str(request["idempotency_key"]),
        input_keys=sorted(request["input"].keys()),
    )
    return payload


def post_workflow_release(
    service_url: str,
    token_file: Path,
    workflow: Dict[str, object],
) -> Dict[str, object]:
    """Publish one immutable Workflow DSL document through the service."""

    if not isinstance(workflow, dict):
        raise ValueError("workflow release must be a JSON object")
    payload = _post_json(
        service_url,
        token_file,
        "/api/v1/workflow-releases",
        {"workflow": workflow},
        conflict_message="workflow version is immutable",
        max_request_bytes=MAX_REMOTE_WORKFLOW_RELEASE_REQUEST_BYTES,
        max_response_bytes=MAX_REMOTE_WORKFLOW_RELEASE_RESPONSE_BYTES,
    )
    _validate_workflow_release_response(payload)
    return payload


def post_workflow_promotion(
    service_url: str,
    token_file: Path,
    workflow_id: str,
    version: str,
    *,
    alias: str = "production",
    expected_current_version: str = "",
) -> Dict[str, object]:
    """Promote one immutable workflow version through the service boundary."""

    normalized_workflow_id = _validate_workflow_ref(workflow_id, "workflow_id")
    normalized_version = _validate_workflow_ref(version, "version")
    normalized_alias = _validate_workflow_alias(alias)
    if not isinstance(expected_current_version, str):
        raise ValueError("expected_current_version must be a string")
    normalized_expected = (
        ""
        if not expected_current_version
        else _validate_workflow_ref(expected_current_version, "expected_current_version")
    )
    payload = _post_json(
        service_url,
        token_file,
        "/api/v1/workflow-promotions",
        {
            "workflow_id": normalized_workflow_id,
            "version": normalized_version,
            "alias": normalized_alias,
            "expected_current_version": normalized_expected,
        },
        conflict_message="workflow alias precondition failed",
        not_found_message="workflow version not found",
        max_request_bytes=MAX_REMOTE_WORKFLOW_PROMOTION_REQUEST_BYTES,
        max_response_bytes=MAX_REMOTE_WORKFLOW_PROMOTION_RESPONSE_BYTES,
    )
    _validate_workflow_promotion_response(
        payload,
        workflow_id=normalized_workflow_id,
        version=normalized_version,
        alias=normalized_alias,
    )
    return payload


def post_workflow_deprecation(
    service_url: str,
    token_file: Path,
    workflow_id: str,
    version: str,
) -> Dict[str, object]:
    """Deprecate one published workflow version through the service boundary."""

    normalized_workflow_id = _validate_workflow_ref(workflow_id, "workflow_id")
    normalized_version = _validate_workflow_ref(version, "version")
    payload = _post_json(
        service_url,
        token_file,
        "/api/v1/workflow-deprecations",
        {
            "workflow_id": normalized_workflow_id,
            "version": normalized_version,
        },
        conflict_message="workflow deprecation rejected",
        not_found_message="workflow version not found",
        max_request_bytes=MAX_REMOTE_WORKFLOW_DEPRECATION_REQUEST_BYTES,
        max_response_bytes=MAX_REMOTE_WORKFLOW_DEPRECATION_RESPONSE_BYTES,
    )
    _validate_workflow_deprecation_response(
        payload,
        workflow_id=normalized_workflow_id,
        version=normalized_version,
    )
    return payload


def post_recurring_schedule_state(
    service_url: str,
    token_file: Path,
    schedule_id: str,
    enabled: bool,
) -> Dict[str, object]:
    """Enable or disable one recurring schedule through the service boundary."""

    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    normalized_schedule_id = _validate_schedule_id(schedule_id)
    action = "enable" if enabled else "disable"
    payload = _post_json(
        service_url,
        token_file,
        f"/api/v1/recurring-schedules/{normalized_schedule_id}/{action}",
        {},
        conflict_message="recurring schedule action conflicts with current state",
        not_found_message="recurring schedule not found",
    )
    _validate_recurring_schedule_action(payload, normalized_schedule_id, enabled)
    return payload


def fetch_recurring_schedule_dispatches(
    service_url: str,
    token_file: Path,
    schedule_id: str = "",
) -> Dict[str, object]:
    """Fetch bounded recurring dispatch evidence, optionally for one schedule."""

    normalized_schedule_id = _validate_schedule_id(schedule_id) if schedule_id else ""
    path = "/api/v1/recurring-schedule-dispatches"
    if normalized_schedule_id:
        path = f"/api/v1/recurring-schedules/{normalized_schedule_id}/dispatches"
    payload = _get_json(
        service_url,
        token_file,
        path,
        conflict_message="recurring schedule dispatch list unavailable",
        max_response_bytes=MAX_RECURRING_SCHEDULE_DISPATCH_LIST_RESPONSE_BYTES,
    )
    _validate_recurring_schedule_dispatch_list(payload, normalized_schedule_id)
    return payload


def fetch_support_bundle(
    service_url: str,
    token_file: Path,
) -> Dict[str, object]:
    """Fetch one authenticated, redacted diagnostic package."""

    payload = _get_json(
        service_url,
        token_file,
        "/api/v1/support-bundle",
        conflict_message="support bundle unavailable",
        max_response_bytes=MAX_SUPPORT_BUNDLE_RESPONSE_BYTES,
    )
    _validate_support_bundle(payload)
    return payload


def fetch_audit_consistency(
    service_url: str,
    token_file: Path,
    run_id: str = "",
) -> Dict[str, object]:
    """Fetch the bounded, authenticated run/audit consistency projection."""

    normalized_run_id = _validate_run_id(run_id) if run_id else ""
    path = "/api/v1/audit-consistency"
    if normalized_run_id:
        path += f"/{normalized_run_id}"
    payload = _get_json(
        service_url,
        token_file,
        path,
        conflict_message="audit consistency unavailable",
        max_response_bytes=MAX_AUDIT_CONSISTENCY_RESPONSE_BYTES,
    )
    _validate_audit_consistency(payload)
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
    not_found_message: str = "run not found",
    max_request_bytes: int = 0,
    max_response_bytes: int = MAX_SERVICE_ACTION_RESPONSE_BYTES,
) -> Dict[str, object]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if max_request_bytes and len(body) > max_request_bytes:
        raise ServiceActionError("service action body is too large", status_code=413)
    return _request_json(
        service_url,
        token_file,
        path,
        method="POST",
        body=body,
        conflict_message=conflict_message,
        not_found_message=not_found_message,
        max_response_bytes=max_response_bytes,
    )


def _get_json(
    service_url: str,
    token_file: Path,
    path: str,
    conflict_message: str,
    max_response_bytes: int = MAX_SERVICE_ACTION_RESPONSE_BYTES,
    not_found_message: str = "run not found",
) -> Dict[str, object]:
    return _request_json(
        service_url,
        token_file,
        path,
        method="GET",
        body=None,
        conflict_message=conflict_message,
        not_found_message=not_found_message,
        max_response_bytes=max_response_bytes,
    )


def _request_json(
    service_url: str,
    token_file: Path,
    path: str,
    *,
    method: str,
    body: Optional[bytes],
    conflict_message: str,
    max_response_bytes: int = MAX_SERVICE_ACTION_RESPONSE_BYTES,
    not_found_message: str = "run not found",
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
            if response.status != 200 or not _safe_json_response_headers(
                response, max_response_bytes=max_response_bytes
            ):
                raise ServiceActionError(status_code=int(response.status))
            return _decode_response(response, max_response_bytes=max_response_bytes)
    except urllib.error.HTTPError as error:
        try:
            status_code = int(error.code)
        finally:
            error.close()
        raise ServiceActionError(
            _error_message(status_code, conflict_message, not_found_message),
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


def _validate_recurring_schedule_list(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed redacted recurring-schedule contract."""

    if set(payload) != {"schema_version", "summary", "schedules", "window"}:
        raise ServiceActionError()
    if payload.get("schema_version") != RECURRING_SCHEDULE_LIST_SCHEMA_VERSION:
        raise ServiceActionError()
    statuses = {"active", "disabled", "other"}
    summary = payload.get("summary")
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
    schedules = payload.get("schedules")
    schedule_fields = {
        "schedule_id", "workflow_id", "workflow_version", "status", "enabled",
        "starts_at", "next_run_at", "interval_seconds", "missed_run_policy",
        "last_scheduled_for", "last_run_id", "last_trigger_id",
    }
    if not isinstance(schedules, list) or len(schedules) > MAX_RECURRING_SCHEDULE_LIST_ITEMS:
        raise ServiceActionError()
    for schedule in schedules:
        if (
            not isinstance(schedule, dict)
            or set(schedule) != schedule_fields
            or not isinstance(schedule.get("schedule_id"), str)
            or not schedule.get("schedule_id")
            or not isinstance(schedule.get("workflow_id"), str)
            or not isinstance(schedule.get("workflow_version"), str)
            or schedule.get("status") not in statuses
            or not isinstance(schedule.get("enabled"), bool)
            or any(
                not isinstance(schedule.get(field), str)
                for field in (
                    "starts_at", "next_run_at", "missed_run_policy",
                    "last_scheduled_for", "last_run_id", "last_trigger_id",
                )
            )
            or schedule.get("missed_run_policy") not in {"latest", "skip"}
            or not _is_non_negative_integer(schedule.get("interval_seconds"))
            or schedule.get("interval_seconds") < 1
        ):
            raise ServiceActionError()
    window = payload.get("window")
    if (
        not isinstance(window, dict)
        or set(window) != {"max_items", "total", "returned", "truncated"}
        or not _is_non_negative_integer(window.get("max_items"))
        or window.get("max_items") < 1
        or window.get("max_items") > MAX_RECURRING_SCHEDULE_LIST_ITEMS
        or not _is_non_negative_integer(window.get("total"))
        or not _is_non_negative_integer(window.get("returned"))
        or window.get("returned") != len(schedules)
        or window.get("returned") > window.get("total")
        or window.get("returned") > window.get("max_items")
        or not isinstance(window.get("truncated"), bool)
        or window.get("truncated") != (window.get("returned") < window.get("total"))
        or window.get("total") != summary.get("total")
    ):
        raise ServiceActionError()


def _validate_workflow_artifact_report(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed value-free artifact report contract."""

    if set(payload) != {"schema_version", "status", "summary", "issues"}:
        raise ServiceActionError()
    if payload.get("schema_version") != WORKFLOW_ARTIFACT_REPORT_SCHEMA_VERSION:
        raise ServiceActionError()
    if payload.get("status") not in {"clean", "attention"}:
        raise ServiceActionError()
    summary = payload.get("summary")
    summary_fields = {
        "registry_records", "referenced_artifacts", "filesystem_artifacts", "healthy",
        "issue_count", "missing", "unsafe_reference", "unsafe_artifact", "invalid_json",
        "oversized", "checksum_mismatch", "orphaned", "truncated",
    }
    if (
        not isinstance(summary, dict)
        or set(summary) != summary_fields
        or any(
            not _is_non_negative_integer(summary.get(field))
            for field in summary_fields
            if field != "truncated"
        )
        or not isinstance(summary.get("truncated"), bool)
    ):
        raise ServiceActionError()
    issue_counts = {
        "missing", "unsafe_reference", "unsafe_artifact", "invalid_json",
        "oversized", "checksum_mismatch", "orphaned",
    }
    if sum(summary.get(field, 0) for field in issue_counts) != summary["issue_count"]:
        raise ServiceActionError()
    issues = payload.get("issues")
    if (
        not isinstance(issues, list)
        or len(issues) > MAX_REMOTE_WORKFLOW_ARTIFACT_REPORT_ISSUES
    ):
        raise ServiceActionError()
    allowed_kinds = issue_counts
    for issue in issues:
        if (
            not isinstance(issue, dict)
            or "kind" not in issue
            or "artifact" not in issue
            or set(issue) - {"kind", "artifact", "workflow_id", "version"}
            or issue.get("kind") not in allowed_kinds
            or not isinstance(issue.get("artifact"), str)
            or len(issue.get("artifact")) > 1024
            or ("workflow_id" in issue and (
                not isinstance(issue.get("workflow_id"), str)
                or len(issue.get("workflow_id")) > 256
            ))
            or ("version" in issue and (
                not isinstance(issue.get("version"), str)
                or len(issue.get("version")) > 128
            ))
        ):
            raise ServiceActionError()
    if payload["status"] != ("clean" if summary["issue_count"] == 0 else "attention"):
        raise ServiceActionError()
    if summary["truncated"] != (len(issues) < summary["issue_count"]):
        raise ServiceActionError()


def _validate_workflow_inventory(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed redacted workflow inventory contract."""

    if set(payload) != {"schema_version", "summary", "versions", "window"}:
        raise ServiceActionError()
    if payload.get("schema_version") != WORKFLOW_INVENTORY_SCHEMA_VERSION:
        raise ServiceActionError()
    summary = payload.get("summary")
    if (
        not isinstance(summary, dict)
        or set(summary) != {"total", "status_counts"}
        or not _is_non_negative_integer(summary.get("total"))
    ):
        raise ServiceActionError()
    status_counts = summary.get("status_counts")
    if (
        not isinstance(status_counts, dict)
        or set(status_counts) != {"published", "deprecated", "other"}
        or any(not _is_non_negative_integer(status_counts.get(key)) for key in status_counts)
    ):
        raise ServiceActionError()
    versions = payload.get("versions")
    version_fields = {"workflow_id", "version", "status", "aliases", "checksum"}
    if not isinstance(versions, list) or len(versions) > MAX_WORKFLOW_INVENTORY_ITEMS:
        raise ServiceActionError()
    for version in versions:
        if (
            not isinstance(version, dict)
            or set(version) != version_fields
            or not isinstance(version.get("workflow_id"), str)
            or not version.get("workflow_id")
            or not isinstance(version.get("version"), str)
            or not version.get("version")
            or version.get("status") not in {"published", "deprecated", "other"}
            or not isinstance(version.get("aliases"), list)
            or len(version.get("aliases")) > 16
            or any(
                not isinstance(alias, str) or not alias
                for alias in version.get("aliases")
            )
            or not _is_hex_digest(version.get("checksum"))
        ):
            raise ServiceActionError()
    window = payload.get("window")
    if (
        not isinstance(window, dict)
        or set(window) != {"max_items", "total", "returned", "truncated"}
        or not _is_non_negative_integer(window.get("max_items"))
        or window.get("max_items") < 1
        or window.get("max_items") > MAX_WORKFLOW_INVENTORY_ITEMS
        or not _is_non_negative_integer(window.get("total"))
        or not _is_non_negative_integer(window.get("returned"))
        or window.get("returned") != len(versions)
        or window.get("returned") > window.get("total")
        or window.get("returned") > window.get("max_items")
        or not isinstance(window.get("truncated"), bool)
        or window.get("truncated") != (window.get("returned") < window.get("total"))
        or window.get("total") != summary.get("total")
    ):
        raise ServiceActionError()
    if sum(status_counts.values()) != summary["total"]:
        raise ServiceActionError()


def _validate_backup_readiness(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed backup-readiness contract."""

    fields = {
        "schema_version", "status", "storage", "state_layout_version", "database_count",
        "workflow_artifact_count", "active_scheduler_lease",
        "scheduler_database_synthesized", "backup_allowed", "blocking_reasons",
    }
    if set(payload) != fields:
        raise ServiceActionError()
    if (
        payload.get("schema_version") != BACKUP_READINESS_SCHEMA_VERSION
        or payload.get("status") not in {"ready", "blocked"}
        or payload.get("storage") != "sqlite"
        or payload.get("state_layout_version") not in {
            "skill2workflow-sqlite-layout-legacy-unversioned",
            "skill2workflow-sqlite-layout-0.1.0",
        }
        or payload.get("database_count") != 3
        or not _is_non_negative_integer(payload.get("workflow_artifact_count"))
        or not isinstance(payload.get("active_scheduler_lease"), bool)
        or not isinstance(payload.get("scheduler_database_synthesized"), bool)
        or not isinstance(payload.get("backup_allowed"), bool)
        or payload.get("backup_allowed") is payload.get("active_scheduler_lease")
        or not isinstance(payload.get("blocking_reasons"), list)
        or payload.get("blocking_reasons") not in ([], ["active_scheduler_lease"])
        or payload.get("blocking_reasons")
        != (["active_scheduler_lease"] if payload.get("active_scheduler_lease") else [])
        or payload.get("status")
        != ("blocked" if payload.get("active_scheduler_lease") else "ready")
    ):
        raise ServiceActionError()


def _validate_retention_readiness(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed retention-readiness contract."""

    fields = {
        "schema_version", "status", "storage", "state_layout_version",
        "active_scheduler_lease", "plan_available", "policy_sha256",
        "delete_before", "eligible", "preserved", "blocking_reasons",
    }
    if set(payload) != fields:
        raise ServiceActionError()
    active = payload.get("active_scheduler_lease")
    if (
        payload.get("schema_version") != RETENTION_READINESS_SCHEMA_VERSION
        or payload.get("status") not in {"ready", "blocked"}
        or payload.get("storage") != "sqlite"
        or payload.get("state_layout_version") != "skill2workflow-sqlite-layout-0.1.0"
        or not isinstance(active, bool)
        or not isinstance(payload.get("plan_available"), bool)
        or payload.get("plan_available") is active
        or not _is_hex_digest(payload.get("policy_sha256"))
        or not isinstance(payload.get("delete_before"), str)
        or not payload.get("delete_before")
        or not isinstance(payload.get("blocking_reasons"), list)
        or payload.get("blocking_reasons") != (["active_scheduler_lease"] if active else [])
        or payload.get("status") != ("blocked" if active else "ready")
    ):
        raise ServiceActionError()

    eligible = payload.get("eligible")
    preserved = payload.get("preserved")
    eligible_fields = {
        "terminal_runs", "run_events", "run_cancellations",
        "run_executions", "run_audit_events", "terminal_dispatches",
    }
    preserved_fields = {"nonterminal_runs", "claimed_dispatches"}
    if (
        not isinstance(eligible, dict)
        or set(eligible) != eligible_fields
        or not isinstance(preserved, dict)
        or set(preserved) != preserved_fields
    ):
        raise ServiceActionError()
    values = list(eligible.values()) + list(preserved.values())
    if active:
        if any(value is not None for value in values):
            raise ServiceActionError()
    elif any(not _is_non_negative_integer(value) for value in values):
        raise ServiceActionError()


def _validate_operational_readiness(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed aggregate readiness contract."""

    fields = {
        "schema_version",
        "status",
        "service",
        "checks",
        "blocking_reasons",
        "operator_notes",
    }
    if set(payload) != fields or payload.get("schema_version") != OPERATIONAL_READINESS_SCHEMA_VERSION:
        raise ServiceActionError()
    service = payload.get("service")
    if (
        not isinstance(service, dict)
        or set(service)
        != {
            "status",
            "ready",
            "storage",
            "state_layout_version",
            "scheduler_lease_owned",
        }
        or service.get("status") not in {"starting", "ready", "draining", "stopped"}
        or not isinstance(service.get("ready"), bool)
        or service.get("storage") != "sqlite"
        or service.get("state_layout_version")
        != "skill2workflow-sqlite-layout-0.1.0"
        or not isinstance(service.get("scheduler_lease_owned"), bool)
    ):
        raise ServiceActionError()
    checks = payload.get("checks")
    if not isinstance(checks, dict) or set(checks) != {
        "workflow_artifacts", "audit_integrity", "offline_backup"
    }:
        raise ServiceActionError()
    artifacts = checks.get("workflow_artifacts")
    if (
        not isinstance(artifacts, dict)
        or set(artifacts) != {"status", "issue_count"}
        or artifacts.get("status") not in {"clean", "attention", "unavailable"}
        or (
            artifacts.get("issue_count") is not None
            and not _is_non_negative_integer(artifacts.get("issue_count"))
        )
        or (artifacts.get("status") == "unavailable" and artifacts.get("issue_count") is not None)
        or (artifacts.get("status") != "unavailable" and artifacts.get("issue_count") is None)
    ):
        raise ServiceActionError()
    audit = checks.get("audit_integrity")
    if (
        not isinstance(audit, dict)
        or set(audit) != {"status"}
        or audit.get("status") not in {"valid", "invalid", "legacy_unsealed", "unavailable"}
    ):
        raise ServiceActionError()
    backup = checks.get("offline_backup")
    if (
        not isinstance(backup, dict)
        or set(backup) != {"status", "active_scheduler_lease"}
        or backup.get("status") not in {"ready", "blocked", "unavailable"}
        or (
            backup.get("active_scheduler_lease") is not None
            and not isinstance(backup.get("active_scheduler_lease"), bool)
        )
        or (backup.get("status") == "unavailable" and backup.get("active_scheduler_lease") is not None)
        or (backup.get("status") != "unavailable" and backup.get("active_scheduler_lease") is None)
    ):
        raise ServiceActionError()
    reasons = payload.get("blocking_reasons")
    allowed_reasons = {
        "service_not_ready",
        "state_layout_not_current",
        "workflow_artifacts_attention",
        "workflow_artifacts_unavailable",
        "audit_integrity_not_valid",
        "audit_integrity_unavailable",
        "offline_backup_unavailable",
    }
    if (
        not isinstance(reasons, list)
        or len(reasons) > len(allowed_reasons)
        or any(reason not in allowed_reasons for reason in reasons)
        or len(set(reasons)) != len(reasons)
    ):
        raise ServiceActionError()
    notes = payload.get("operator_notes")
    if (
        not isinstance(notes, list)
        or len(notes) > 1
        or any(note != "offline_backup_requires_stop" for note in notes)
        or ("offline_backup_requires_stop" in notes
            and backup.get("status") != "blocked")
        or (backup.get("status") == "blocked"
            and notes != ["offline_backup_requires_stop"])
    ):
        raise ServiceActionError()
    if payload.get("status") not in {"ready", "attention"}:
        raise ServiceActionError()
    expected_status = "ready" if not reasons else "attention"
    if payload.get("status") != expected_status:
        raise ServiceActionError()


def _validate_audit_integrity(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed audit-integrity contract."""

    fields = {
        "schema_version", "status", "algorithm", "event_count",
        "head_digest", "first_invalid_sequence", "reason",
    }
    if set(payload) != fields:
        raise ServiceActionError()
    status = payload.get("status")
    reason = payload.get("reason")
    algorithm = payload.get("algorithm")
    head_digest = payload.get("head_digest")
    if (
        payload.get("schema_version") != AUDIT_INTEGRITY_SCHEMA_VERSION
        or status not in {"valid", "invalid", "legacy_unsealed"}
        or algorithm not in {AUDIT_INTEGRITY_ALGORITHM, ""}
        or not _is_non_negative_integer(payload.get("event_count"))
        or not isinstance(head_digest, str)
        or not _is_non_negative_integer(payload.get("first_invalid_sequence"))
        or reason not in {
            "", "sqlite_storage_required", "integrity_columns_missing",
            "schema_mismatch", "sequence_invalid", "sequence_out_of_order",
            "payload_invalid", "column_mismatch", "prev_digest_mismatch",
            "digest_mismatch",
        }
    ):
        raise ServiceActionError()
    if status == "valid":
        if (
            algorithm != AUDIT_INTEGRITY_ALGORITHM
            or reason != ""
            or payload.get("first_invalid_sequence") != 0
            or (
                (payload.get("event_count") == 0 and head_digest != "")
                or (
                    payload.get("event_count") > 0
                    and not _is_hex_digest(head_digest)
                )
            )
        ):
            raise ServiceActionError()
    elif status == "legacy_unsealed":
        if (
            algorithm != ""
            or reason != "sqlite_storage_required"
            or payload.get("first_invalid_sequence") != 0
            or head_digest != ""
        ):
            raise ServiceActionError()
    elif (
        algorithm != AUDIT_INTEGRITY_ALGORITHM
        or reason == ""
        or head_digest != ""
    ):
        raise ServiceActionError()


def _validate_runtime_info(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed runtime-info contract."""

    fields = {
        "schema_version", "package_version", "compatibility_line",
        "service_schema_version", "workflow_dsl_schema_version", "storage",
        "state_layout_version", "service_status", "service_ready",
        "scheduler_lease_owned",
    }
    if set(payload) != fields:
        raise ServiceActionError()
    package_version = payload.get("package_version")
    service_status = payload.get("service_status")
    if (
        payload.get("schema_version") != RUNTIME_INFO_SCHEMA_VERSION
        or not isinstance(package_version, str)
        or not package_version
        or len(package_version) > 64
        or any(character.isspace() for character in package_version)
        or payload.get("compatibility_line") != "0.1.x"
        or payload.get("service_schema_version") != SERVICE_SCHEMA_VERSION
        or payload.get("workflow_dsl_schema_version") != WORKFLOW_DSL_SCHEMA_VERSION
        or payload.get("storage") != "sqlite"
        or payload.get("state_layout_version") != "skill2workflow-sqlite-layout-0.1.0"
        or service_status not in {"starting", "ready", "draining", "stopped"}
        or not isinstance(payload.get("service_ready"), bool)
        or not isinstance(payload.get("scheduler_lease_owned"), bool)
        or (payload.get("service_ready") and service_status != "ready")
    ):
        raise ServiceActionError()


def _validate_recurring_schedule_action(
    payload: Dict[str, object], schedule_id: str, enabled: bool
) -> None:
    if (
        set(payload) != {"schema_version", "schedule_id", "enabled", "status", "changed"}
        or payload.get("schema_version") != RECURRING_SCHEDULE_ACTION_SCHEMA_VERSION
        or payload.get("schedule_id") != schedule_id
        or payload.get("enabled") is not enabled
        or payload.get("status") not in {"active", "disabled"}
        or not isinstance(payload.get("changed"), bool)
    ):
        raise ServiceActionError()


def _validate_recurring_schedule_dispatch_list(
    payload: Dict[str, object], schedule_id: str
) -> None:
    statuses = {"claimed", "completed", "failed", "skipped", "uncertain", "other"}
    if set(payload) != {"schema_version", "schedule_id", "summary", "dispatches", "window"}:
        raise ServiceActionError()
    if payload.get("schema_version") != RECURRING_SCHEDULE_DISPATCH_LIST_SCHEMA_VERSION:
        raise ServiceActionError()
    if payload.get("schedule_id") != schedule_id:
        raise ServiceActionError()
    summary = payload.get("summary")
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
    dispatches = payload.get("dispatches")
    fields = {
        "dispatch_id", "schedule_id", "scheduled_for", "status",
        "coalesced_occurrences", "run_id", "trigger_id", "error_type", "completed_at",
    }
    if not isinstance(dispatches, list) or len(dispatches) > MAX_RECURRING_SCHEDULE_DISPATCH_LIST_ITEMS:
        raise ServiceActionError()
    for dispatch in dispatches:
        if (
            not isinstance(dispatch, dict)
            or set(dispatch) != fields
            or not isinstance(dispatch.get("dispatch_id"), str)
            or not dispatch.get("dispatch_id")
            or len(dispatch.get("dispatch_id")) > 128
            or not isinstance(dispatch.get("schedule_id"), str)
            or not dispatch.get("schedule_id")
            or len(dispatch.get("schedule_id")) > 128
            or (schedule_id and dispatch.get("schedule_id") != schedule_id)
            or dispatch.get("status") not in statuses
            or any(not isinstance(dispatch.get(field), str) for field in (
                "scheduled_for", "run_id", "trigger_id", "error_type", "completed_at"
            ))
            or len(dispatch.get("error_type", "")) > 64
            or not _is_non_negative_integer(dispatch.get("coalesced_occurrences"))
        ):
            raise ServiceActionError()
    window = payload.get("window")
    if (
        not isinstance(window, dict)
        or set(window) != {"max_items", "total", "returned", "truncated"}
        or not _is_non_negative_integer(window.get("max_items"))
        or window.get("max_items") < 1
        or window.get("max_items") > MAX_RECURRING_SCHEDULE_DISPATCH_LIST_ITEMS
        or not _is_non_negative_integer(window.get("total"))
        or not _is_non_negative_integer(window.get("returned"))
        or window.get("returned") != len(dispatches)
        or window.get("returned") > window.get("total")
        or window.get("returned") > window.get("max_items")
        or not isinstance(window.get("truncated"), bool)
        or window.get("truncated") != (window.get("returned") < window.get("total"))
        or window.get("total") != summary.get("total")
    ):
        raise ServiceActionError()


def _validate_support_bundle(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed redacted support-bundle contract."""

    if set(payload) != {"schema_version", "service", "run_list", "observability"}:
        raise ServiceActionError()
    if payload.get("schema_version") != SUPPORT_BUNDLE_SCHEMA_VERSION:
        raise ServiceActionError()
    service = payload.get("service")
    statuses = {"starting", "ready", "draining", "stopped", "unknown"}
    if (
        not isinstance(service, dict)
        or set(service) != {"status", "ready", "storage", "scheduler_lease_owned"}
        or service.get("status") not in statuses
        or not isinstance(service.get("ready"), bool)
        or service.get("storage") != "sqlite"
        or not isinstance(service.get("scheduler_lease_owned"), bool)
    ):
        raise ServiceActionError()

    run_list = payload.get("run_list")
    if not isinstance(run_list, dict):
        raise ServiceActionError()
    _validate_run_list(run_list)

    observability = payload.get("observability")
    workflow_statuses = {"published", "deprecated", "other"}
    run_statuses = {
        "created", "running", "waiting", "completed", "failed", "cancelled", "interrupted", "other"
    }
    dispatch_statuses = {"claimed", "completed", "failed", "skipped", "uncertain", "other"}
    routes = {
        "health", "readiness", "metrics", "control_snapshot", "support_bundle", "run_list",
        "run_detail", "workflow_trigger", "run_cancel", "run_resume", "unknown",
    }
    status_classes = {"2xx", "4xx", "5xx"}

    def valid_counts(value, keys):
        return (
            isinstance(value, dict)
            and set(value) == keys
            and all(_is_non_negative_integer(item) for item in value.values())
        )

    http_requests = observability.get("http_requests") if isinstance(observability, dict) else None
    if (
        not isinstance(observability, dict)
        or set(observability) != {
            "service_status", "ready", "scheduler_lease_owned", "uptime_seconds",
            "workflow_status_counts", "run_status_counts", "dispatch_status_counts",
            "audit_event_count", "recurring_schedule_count", "http_requests",
        }
        or observability.get("service_status") not in statuses
        or observability.get("service_status") != service.get("status")
        or not isinstance(observability.get("ready"), bool)
        or observability.get("ready") != service.get("ready")
        or not isinstance(observability.get("scheduler_lease_owned"), bool)
        or observability.get("scheduler_lease_owned") != service.get("scheduler_lease_owned")
        or not isinstance(observability.get("uptime_seconds"), (int, float))
        or isinstance(observability.get("uptime_seconds"), bool)
        or not math.isfinite(float(observability.get("uptime_seconds")))
        or observability.get("uptime_seconds") < 0
        or not valid_counts(observability.get("workflow_status_counts"), workflow_statuses)
        or not valid_counts(observability.get("run_status_counts"), run_statuses)
        or not valid_counts(observability.get("dispatch_status_counts"), dispatch_statuses)
        or not _is_non_negative_integer(observability.get("audit_event_count"))
        or not _is_non_negative_integer(observability.get("recurring_schedule_count"))
        or not isinstance(http_requests, dict)
        or set(http_requests) != routes
        or any(
            not isinstance(counts, dict)
            or set(counts) != status_classes
            or any(not _is_non_negative_integer(item) for item in counts.values())
            for counts in http_requests.values()
        )
    ):
        raise ServiceActionError()


def _validate_audit_consistency(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed run-audit report contract."""

    if set(payload) != {"schema_version", "status", "summary", "runs"}:
        raise ServiceActionError()
    if payload.get("schema_version") != RUN_AUDIT_REPORT_SCHEMA_VERSION:
        raise ServiceActionError()
    if payload.get("status") not in {"clean", "attention"}:
        raise ServiceActionError()
    summary = payload.get("summary")
    summary_fields = {
        "run_count", "checked_runs", "attention_runs", "missing_events",
        "duplicate_events", "unexpected_events", "truncated",
    }
    if (
        not isinstance(summary, dict)
        or set(summary) != summary_fields
        or any(not _is_non_negative_integer(summary.get(field)) for field in summary_fields - {"truncated"})
        or not isinstance(summary.get("truncated"), bool)
        or summary.get("checked_runs") > MAX_RUN_AUDIT_REPORT_RUNS
        or summary.get("run_count") < summary.get("checked_runs")
    ):
        raise ServiceActionError()
    runs = payload.get("runs")
    if not isinstance(runs, list) or len(runs) > MAX_RUN_AUDIT_REPORT_RUNS:
        raise ServiceActionError()
    run_fields = {
        "run_id", "workflow_id", "workflow_version", "run_status", "status",
        "expected_event_count", "observed_event_count", "missing", "duplicate", "unexpected",
    }

    def valid_differences(value):
        return isinstance(value, list) and len(value) <= MAX_RUN_AUDIT_REPORT_TYPES and all(
            isinstance(item, dict)
            and set(item) == {"type", "count"}
            and isinstance(item.get("type"), str)
            and item.get("type")
            and _is_non_negative_integer(item.get("count"))
            and item.get("count") > 0
            for item in value
        )

    for run in runs:
        if (
            not isinstance(run, dict)
            or set(run) != run_fields
            or not _is_safe_run_identifier(run.get("run_id"))
            or any(
                not isinstance(run.get(field), str) or not run.get(field)
                for field in ("run_id", "workflow_id", "workflow_version", "run_status")
            )
            or run.get("status") not in {"clean", "attention"}
            or any(
                not _is_non_negative_integer(run.get(field))
                for field in ("expected_event_count", "observed_event_count")
            )
            or not valid_differences(run.get("missing"))
            or not valid_differences(run.get("duplicate"))
            or not valid_differences(run.get("unexpected"))
        ):
            raise ServiceActionError()
    if summary.get("checked_runs") != len(runs):
        raise ServiceActionError()


def _is_non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_hex_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char.isdigit() or "a" <= char <= "f" for char in value)
    )


def _is_safe_run_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("run_")
        and 5 <= len(value) <= 128
        and all(char.isalnum() or char in {"_", "-"} for char in value)
    )


def _safe_json_response_headers(
    response,
    *,
    max_response_bytes: int = MAX_SERVICE_ACTION_RESPONSE_BYTES,
) -> bool:
    declared_lengths = response.headers.get_all("Content-Length", [])
    if len(declared_lengths) > 1:
        return False
    if declared_lengths:
        try:
            declared_length = int(declared_lengths[0])
        except (TypeError, ValueError):
            return False
        if declared_length < 0 or declared_length > max_response_bytes:
            return False
    return (
        response.headers.get_content_type() == "application/json"
        and not response.headers.get("Content-Encoding", "")
        and "no-store" in response.headers.get("Cache-Control", "").lower()
    )


def _decode_response(
    response,
    *,
    max_response_bytes: int = MAX_SERVICE_ACTION_RESPONSE_BYTES,
) -> Dict[str, object]:
    body = response.read(max_response_bytes + 1)
    if len(body) > max_response_bytes:
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


def _validate_workflow_ref(value: str, field: str) -> str:
    """Validate one workflow path component before URL quoting."""

    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError(f"{field} must be a non-empty safe workflow identifier")
    if any(
        ord(char) < 0x20
        or ord(char) == 0x7F
        or char in {"/", "?", "#"}
        for char in value
    ):
        raise ValueError(f"{field} must be a non-empty safe workflow identifier")
    return value


def _validate_trigger_response(
    payload: Dict[str, object],
    *,
    workflow_id: str,
    source: str,
    idempotency_key: str,
    input_keys,
) -> None:
    """Reject responses outside the fixed published-trigger envelope."""

    fields = {
        "trigger_id",
        "workflow_id",
        "workflow_version",
        "run_id",
        "run_status",
        "source",
        "idempotency_key",
        "input_keys",
    }
    if set(payload) != fields:
        raise ServiceActionError()
    for field in ("trigger_id", "workflow_id", "workflow_version", "run_id", "run_status", "source", "idempotency_key"):
        if not isinstance(payload.get(field), str) or not payload.get(field):
            raise ServiceActionError()
    if payload["workflow_id"] != workflow_id or payload["source"] != source:
        raise ServiceActionError()
    if payload["idempotency_key"] != idempotency_key:
        raise ServiceActionError()
    if not payload["trigger_id"].startswith("trigger_"):
        raise ServiceActionError()
    try:
        _validate_run_id(payload["run_id"])
    except ValueError as error:
        raise ServiceActionError() from error
    if payload["run_status"] not in {
        "created",
        "running",
        "waiting",
        "completed",
        "failed",
        "cancelled",
        "interrupted",
    }:
        raise ServiceActionError()
    response_input_keys = payload["input_keys"]
    if (
        not isinstance(response_input_keys, list)
        or any(not isinstance(value, str) for value in response_input_keys)
        or response_input_keys != sorted(set(response_input_keys))
        or response_input_keys != list(input_keys)
    ):
        raise ServiceActionError()


def _validate_workflow_release_response(payload: Dict[str, object]) -> None:
    """Reject responses outside the fixed redacted release contract."""

    if set(payload) != {
        "schema_version",
        "workflow_id",
        "version",
        "status",
        "checksum",
    }:
        raise ServiceActionError()
    if payload.get("schema_version") != WORKFLOW_RELEASE_SCHEMA_VERSION:
        raise ServiceActionError()
    if any(
        not isinstance(payload.get(field), str) or not payload.get(field)
        for field in ("workflow_id", "version", "status", "checksum")
    ):
        raise ServiceActionError()
    if payload["status"] != "published" or not _is_hex_digest(payload["checksum"]):
        raise ServiceActionError()
    try:
        _validate_workflow_ref(payload["workflow_id"], "workflow_id")
        _validate_workflow_ref(payload["version"], "version")
    except ValueError as error:
        raise ServiceActionError() from error


def _validate_workflow_promotion_response(
    payload: Dict[str, object],
    *,
    workflow_id: str,
    version: str,
    alias: str,
) -> None:
    """Reject responses outside the fixed redacted promotion contract."""

    fields = {
        "schema_version",
        "workflow_id",
        "version",
        "alias",
        "status",
        "checksum",
    }
    if set(payload) != fields or payload.get("schema_version") != WORKFLOW_PROMOTION_SCHEMA_VERSION:
        raise ServiceActionError()
    if (
        payload.get("workflow_id") != workflow_id
        or payload.get("version") != version
        or payload.get("alias") != alias
        or payload.get("status") != "promoted"
        or not _is_hex_digest(payload.get("checksum"))
    ):
        raise ServiceActionError()


def _validate_workflow_deprecation_response(
    payload: Dict[str, object],
    *,
    workflow_id: str,
    version: str,
) -> None:
    """Reject responses outside the fixed redacted deprecation contract."""

    fields = {"schema_version", "workflow_id", "version", "status", "checksum"}
    if set(payload) != fields or payload.get("schema_version") != WORKFLOW_DEPRECATION_SCHEMA_VERSION:
        raise ServiceActionError()
    if (
        payload.get("workflow_id") != workflow_id
        or payload.get("version") != version
        or payload.get("status") != "deprecated"
        or not _is_hex_digest(payload.get("checksum"))
    ):
        raise ServiceActionError()


def _validate_workflow_diff_response(
    payload: Dict[str, object],
    *,
    workflow_id: str,
    from_version: str,
    to_version: str,
) -> None:
    """Reject responses outside the fixed structural diff contract."""

    if set(payload) != {"schema_version", "workflow_id", "from", "to", "changed", "changes"}:
        raise ServiceActionError()
    if (
        payload.get("schema_version") != WORKFLOW_DIFF_SCHEMA_VERSION
        or payload.get("workflow_id") != workflow_id
        or not isinstance(payload.get("changed"), bool)
    ):
        raise ServiceActionError()

    def validate_record(record, expected_version):
        if (
            not isinstance(record, dict)
            or set(record) != {"version", "status", "checksum", "aliases"}
            or record.get("version") != expected_version
            or record.get("status") not in {"published", "deprecated"}
            or not _is_hex_digest(record.get("checksum"))
            or not isinstance(record.get("aliases"), list)
            or record.get("aliases") != sorted(set(record.get("aliases")))
            or any(not isinstance(alias, str) or not alias for alias in record.get("aliases"))
        ):
            raise ServiceActionError()

    validate_record(payload.get("from"), from_version)
    validate_record(payload.get("to"), to_version)
    changes = payload.get("changes")
    if not isinstance(changes, dict) or set(changes) != {
        "sections",
        "workflow_changed",
        "entry_changed",
        "input_schema_changed",
        "policies_changed",
        "other_changed",
        "nodes",
        "edges",
    }:
        raise ServiceActionError()
    sections = changes.get("sections")
    if (
        not isinstance(sections, list)
        or len(sections) != len(set(sections))
        or any(
            section not in {"workflow", "entry", "input_schema", "policies", "nodes", "edges", "other"}
            for section in sections
        )
        or any(not isinstance(changes.get(field), bool) for field in (
            "workflow_changed", "entry_changed", "input_schema_changed",
            "policies_changed", "other_changed",
        ))
    ):
        raise ServiceActionError()
    for field in ("nodes", "edges"):
        value = changes.get(field)
        if (
            not isinstance(value, dict)
            or set(value) != {"added", "removed", "changed"}
            or any(
                not isinstance(value.get(key), list)
                or value.get(key) != sorted(set(value.get(key)))
                or any(not isinstance(item, str) or not item for item in value.get(key))
                for key in ("added", "removed", "changed")
            )
        ):
            raise ServiceActionError()
def _validate_workflow_alias(alias: str) -> str:
    value = str(alias).strip()
    if len(value.encode("utf-8")) > 64 or not _WORKFLOW_ALIAS_PATTERN.fullmatch(value):
        raise ValueError(
            "workflow alias must start with a lowercase letter and contain only "
            "lowercase letters, numbers, ., _, or - (at most 64 UTF-8 bytes)"
        )
    return value


def _validate_schedule_id(schedule_id: str) -> str:
    value = str(schedule_id)
    if (
        not value
        or len(value) > 128
        or any(not (char.isalnum() or char in {"-", "_", "."}) for char in value)
    ):
        raise ValueError("schedule_id must be a safe schedule identifier")
    return value


def _error_message(
    status_code: int, conflict_message: str, not_found_message: str = "run not found"
) -> str:
    return {
        400: "invalid service action",
        401: "authentication required",
        404: not_found_message,
        409: conflict_message,
        413: "service action body is too large",
        503: "service unavailable",
    }.get(status_code, "service action failed")
