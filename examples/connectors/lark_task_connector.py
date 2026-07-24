"""Dry-run-default Lark/Feishu task connector with scoped live support."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
from datetime import datetime
from typing import Dict, List, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request

from skill2workflow.connectors import (
    CONNECTOR_EXECUTION_CONTRACT_VERSION,
    CONNECTOR_MANIFEST_VERSION,
    ConnectorExecutionError,
)
from skill2workflow.credentials import CredentialResolutionError


LIVE_ENVIRONMENT_SWITCH = "SKILL2WORKFLOW_LARK_TASK_LIVE"
LIVE_URL = "https://open.feishu.cn/open-apis/task/v2/tasks?user_id_type=open_id"
LIVE_TIMEOUT_SECONDS = 10.0
REQUIRED_CREDENTIAL_HANDLE = "lark_bot_access_token"
PROVIDER_CODE_STATUS = {
    1470400: "validation_failed",
    1470403: "permission_denied",
    1470404: "resource_not_found",
    1470422: "idempotency_conflict",
    1470500: "provider_unavailable",
}


MANIFEST = {
    "manifest_version": CONNECTOR_MANIFEST_VERSION,
    "id": "lark_task",
    "name": "Lark/Feishu Task Connector",
    "kind": "lark_task",
    "status": "active",
    "node_types": ["tool_call"],
    "description": "Explicit dry-run-default connector with opt-in scoped Feishu task creation.",
    "config_schema": {
        "type": "object",
        "properties": {
            "operation": {"type": "string"},
            "mode": {"type": "string", "enum": ["dry_run", "live"]},
            "request": {
                "type": "object",
                "properties": {
                    "body": {"type": "object"},
                    "input_mapping": {"type": "array"},
                },
            },
        },
    },
    "execution_contract": {
        "contract_version": CONNECTOR_EXECUTION_CONTRACT_VERSION,
        "mode": "external",
        "entrypoint": "examples/connectors/lark_task_connector.py:execute",
        "receives": ["node.connector", "run_context", "credential_provider"],
        "returns": ["status", "connector", "output", "error", "audit", "input_mapping", "credentials"],
    },
    "credential_contract": {
        "supports_handles": True,
        "targets": ["header"],
        "resolved_value_policy": "never_in_workflow_run_state_or_audit",
    },
    "audit_contract": {
        "value_policy": "compact_no_payload_values",
        "events": ["connector_started", "connector_completed", "connector_failed"],
    },
}


def execute(binding: Dict[str, object], credential_provider=None, context=None, transport=None) -> Dict[str, object]:
    """Validate or execute a scoped Lark task create request."""
    if not isinstance(binding, dict):
        raise ConnectorExecutionError("lark_task connector binding must be an object")

    operation = str(binding.get("operation") or "")
    if operation != "create_task":
        raise ConnectorExecutionError("lark_task connector only supports operation create_task")

    mode = str(binding.get("mode") or "dry_run")
    if mode not in ("dry_run", "live"):
        raise ConnectorExecutionError("lark_task connector only supports modes dry_run and live")

    request = binding.get("request", {})
    if request is None:
        request = {}
    if not isinstance(request, dict):
        raise ConnectorExecutionError("lark_task connector.request must be an object")

    body, mapping_summary = _mapped_body(request, context)
    audit = _task_audit_metadata(operation, mode, body)

    if mode == "live":
        if not _live_enabled():
            return _live_result("failed", audit, "live_disabled", mapping_summary)

        try:
            payload = _provider_request_body(body, context)
        except ConnectorExecutionError:
            return _failed_live_result(
                audit,
                "validation_failed",
                mapping_summary,
                idempotency_key_present=False,
            )

        try:
            credential_summary, credential_values = _resolve_credentials(
                binding.get("credentials", []), credential_provider
            )
            if REQUIRED_CREDENTIAL_HANDLE not in credential_values:
                raise ConnectorExecutionError(
                    f"credential handle not found: {REQUIRED_CREDENTIAL_HANDLE}"
                )
        except ConnectorExecutionError:
            return _failed_live_result(
                audit,
                "credential_failed",
                mapping_summary,
                credential_summary={
                    "status": "failed",
                    "handles": [REQUIRED_CREDENTIAL_HANDLE],
                },
                idempotency_key_present=True,
            )

        try:
            live_request = _request(payload, credential_values[REQUIRED_CREDENTIAL_HANDLE])
        except Exception:
            return _failed_live_result(
                audit,
                "credential_failed",
                mapping_summary,
                credential_summary,
                idempotency_key_present=True,
            )

        provider_status, task_id_present = _transport_outcome(live_request, transport or _default_transport)
        if provider_status != "completed" or not task_id_present:
            return _failed_live_result(
                audit,
                provider_status,
                mapping_summary,
                credential_summary,
                idempotency_key_present=True,
            )
        return _live_result(
            "completed",
            audit,
            "completed",
            mapping_summary,
            credential_summary,
            True,
            True,
        )

    credential_summary, _credential_values = _resolve_credentials(
        binding.get("credentials", []), credential_provider
    )
    if not audit["task_title_present"]:
        raise ConnectorExecutionError("lark_task connector task title is required")

    output = dict(audit)
    output["input_mapping_keys"] = mapping_summary.get("input_keys", [])
    output["credential_handles"] = credential_summary["handles"]

    return {
        "status": "completed",
        "connector": {"id": "lark_task", "kind": "lark_task"},
        "output": output,
        "audit": audit,
        "credentials": credential_summary,
        "input_mapping": mapping_summary,
    }


def preflight(binding: Dict[str, object], context=None) -> Dict[str, object]:
    """Construct the fixed live payload without resolving a credential or using transport."""
    audit = {
        "operation": "",
        "mode": "",
        "task_title_present": False,
        "task_description_present": False,
        "assignee_present": False,
        "due_at_present": False,
    }
    mapping_summary = {"status": "not_applied", "input_keys": []}
    ready = False
    try:
        if not isinstance(binding, dict):
            raise ConnectorExecutionError("lark_task connector binding must be an object")
        operation = str(binding.get("operation") or "")
        if operation != "create_task":
            raise ConnectorExecutionError("lark_task connector only supports operation create_task")
        mode = str(binding.get("mode") or "")
        if mode != "live":
            raise ConnectorExecutionError("lark_task preflight requires mode live")
        request = binding.get("request", {})
        if request is None:
            request = {}
        if not isinstance(request, dict):
            raise ConnectorExecutionError("lark_task connector.request must be an object")
        body, mapping_summary = _mapped_body(request, context)
        audit = _task_audit_metadata(operation, mode, body)
        _provider_request_body(body, context)
        ready = True
    except ConnectorExecutionError:
        pass
    return {
        "status": "ready" if ready else "invalid",
        "connector": {"id": "lark_task", "kind": "lark_task"},
        "output": {
            "operation": audit["operation"],
            "mode": audit["mode"],
            "provider_payload_constructed": ready,
            "credential_resolution_attempted": False,
            "network_called": False,
        },
        "audit": audit,
        "input_mapping": mapping_summary,
    }


def _task_audit_metadata(operation: str, mode: str, body: Dict[str, object]) -> Dict[str, object]:
    return {
        "operation": operation,
        "mode": mode,
        "task_title_present": _present(body.get("title")),
        "task_description_present": _present(body.get("description")),
        "assignee_present": _present(body.get("assignee_open_id")),
        "due_at_present": _present(body.get("due_at")),
    }


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _live_enabled() -> bool:
    return os.environ.get(LIVE_ENVIRONMENT_SWITCH) == "1"


def _execution_identity(context: object) -> List[str]:
    context_root = context if isinstance(context, dict) else {}
    execution = context_root.get("_execution", {})
    if not isinstance(execution, dict):
        return []
    values = [
        str(execution.get("workflow_id") or ""),
        str(execution.get("workflow_version") or ""),
        str(execution.get("run_id") or ""),
        str(execution.get("node_id") or ""),
    ]
    return values if all(values) else []


def _client_token(context: object) -> str:
    identity = _execution_identity(context)
    if not identity:
        raise ConnectorExecutionError("lark_task live execution identity is required")
    canonical = json.dumps(identity, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _provider_request_body(body: Dict[str, object], context: object) -> Dict[str, object]:
    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ConnectorExecutionError("lark_task connector task title is required")
    if len(title) > 3000:
        raise ConnectorExecutionError("lark_task connector task title exceeds the provider limit")

    payload: Dict[str, object] = {
        "summary": title,
        "client_token": _client_token(context),
    }
    description = body.get("description")
    if description is not None:
        if not isinstance(description, str):
            raise ConnectorExecutionError("lark_task connector description must be a string")
        if len(description) > 3000:
            raise ConnectorExecutionError(
                "lark_task connector description exceeds the provider limit"
            )
        payload["description"] = description

    assignee = body.get("assignee_open_id")
    if assignee is not None:
        if not isinstance(assignee, str) or not assignee.strip():
            raise ConnectorExecutionError("lark_task connector assignee_open_id must be a non-empty string")
        payload["members"] = [{"id": assignee, "type": "user", "role": "assignee"}]

    due_at = body.get("due_at")
    if due_at is not None:
        payload["due"] = {"timestamp": _due_timestamp(due_at), "is_all_day": False}
    return payload


def _due_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConnectorExecutionError("lark_task connector due_at must be an RFC 3339 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        raise ConnectorExecutionError("lark_task connector due_at must be an RFC 3339 string")
    if parsed.tzinfo is None:
        raise ConnectorExecutionError("lark_task connector due_at must include a timezone")
    return str(int(parsed.timestamp() * 1000))


def _request(payload: Dict[str, object], token: str) -> urllib_request.Request:
    return urllib_request.Request(
        LIVE_URL,
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )


def _default_transport(request: urllib_request.Request, timeout: float):
    return urllib_request.urlopen(request, timeout=timeout)


def _http_status(status: int) -> str:
    if status == 400:
        return "validation_failed"
    if status == 401:
        return "authorization_failed"
    if status == 403:
        return "permission_denied"
    if status == 404:
        return "resource_not_found"
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "provider_unavailable"
    return "malformed_response"


def _decode_provider(raw: bytes):
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _provider_outcome(status: int, raw: bytes) -> Tuple[str, bool]:
    payload = _decode_provider(raw)
    if payload is not None:
        code = payload.get("code")
        if isinstance(code, int) and code in PROVIDER_CODE_STATUS:
            return PROVIDER_CODE_STATUS[code], False
        if code == 0:
            if status < 200 or status >= 300:
                return _http_status(status), False
            data = payload.get("data", {})
            task = data.get("task", {}) if isinstance(data, dict) else {}
            guid = task.get("guid") if isinstance(task, dict) else ""
            if isinstance(guid, str) and guid:
                return "completed", True
            return "malformed_response", False
    return _http_status(status), False


def _safe_close(response) -> None:
    try:
        close = getattr(response, "close", None)
        if callable(close):
            close()
    except Exception:
        return


def _read_provider_outcome(response, status: int) -> Tuple[str, bool]:
    try:
        raw = response.read()
    except (TimeoutError, socket.timeout):
        return "timeout", False
    except urllib_error.URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            return "timeout", False
        return "provider_unavailable", False
    except Exception:
        return "provider_unavailable", False
    finally:
        _safe_close(response)
    return _provider_outcome(status, raw)


def _transport_outcome(request: urllib_request.Request, transport) -> Tuple[str, bool]:
    try:
        response = transport(request, LIVE_TIMEOUT_SECONDS)
    except urllib_error.HTTPError as error:
        try:
            status = int(error.code)
        except Exception:
            _safe_close(error)
            return "malformed_response", False
        return _read_provider_outcome(error, status)
    except (TimeoutError, socket.timeout):
        return "timeout", False
    except urllib_error.URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            return "timeout", False
        return "provider_unavailable", False
    except Exception:
        return "provider_unavailable", False

    try:
        status = int(getattr(response, "status", 0))
    except Exception:
        _safe_close(response)
        return "malformed_response", False
    return _read_provider_outcome(response, status)


def _resolve_credentials(
    credentials: object, credential_provider
) -> Tuple[Dict[str, object], Dict[str, str]]:
    if credentials in (None, []):
        return {"status": "skipped", "handles": []}, {}
    if not isinstance(credentials, list):
        raise ConnectorExecutionError("connector.credentials must be a list")

    handles: List[str] = []
    values: Dict[str, str] = {}
    for index, credential in enumerate(credentials):
        if not isinstance(credential, dict):
            raise ConnectorExecutionError(f"connector.credentials[{index}] must be an object")
        target = str(credential.get("target") or "")
        if target != "header":
            raise ConnectorExecutionError(f"connector.credentials[{index}].target must be header")
        handle = str(credential.get("handle") or "")
        if not handle:
            raise ConnectorExecutionError(f"connector.credentials[{index}].handle is required")
        if handle != REQUIRED_CREDENTIAL_HANDLE:
            continue
        if credential_provider is None:
            raise ConnectorExecutionError(f"credential handle not found: {handle}")
        try:
            values[handle] = credential_provider.resolve(handle)
        except CredentialResolutionError as error:
            raise ConnectorExecutionError(str(error))
        handles.append(handle)

    return {"status": "resolved", "handles": sorted(handles)}, values


def _live_result(
    status: str,
    audit: Dict[str, object],
    provider_status: str,
    mapping_summary: Dict[str, object],
    credential_summary: Dict[str, object] = None,
    idempotency_key_present: bool = False,
    task_id_present: bool = False,
) -> Dict[str, object]:
    compact = dict(audit)
    compact.update(
        {
            "credential_status": str((credential_summary or {}).get("status") or "skipped"),
            "idempotency_key_present": idempotency_key_present,
            "provider_status": provider_status,
            "lark_task_id_present": task_id_present,
        }
    )
    result = {
        "status": status,
        "connector": {"id": "lark_task", "kind": "lark_task"},
        "output": dict(compact),
        "audit": compact,
        "input_mapping": mapping_summary,
    }
    if credential_summary:
        result["credentials"] = credential_summary
    if status == "failed":
        result["error"] = f"lark_task live request failed: {provider_status}"
    return result


def _failed_live_result(
    audit: Dict[str, object],
    provider_status: str,
    mapping_summary: Dict[str, object],
    credential_summary: Dict[str, object] = None,
    idempotency_key_present: bool = False,
) -> Dict[str, object]:
    compact = dict(audit)
    compact.update(
        {
            "credential_status": str((credential_summary or {}).get("status") or "skipped"),
            "idempotency_key_present": idempotency_key_present,
            "provider_status": provider_status,
            "lark_task_id_present": False,
        }
    )
    result = {
        "status": "failed",
        "connector": {"id": "lark_task", "kind": "lark_task"},
        "output": dict(compact),
        "error": f"lark_task live request failed: {provider_status}",
        "audit": compact,
        "input_mapping": mapping_summary,
    }
    if credential_summary:
        result["credentials"] = credential_summary
    return result


def _mapped_body(request: Dict[str, object], context: object):
    body = copy.deepcopy(request.get("body", {}))
    if body is None:
        body = {}
    if not isinstance(body, dict):
        raise ConnectorExecutionError("lark_task connector.request.body must be an object")

    mappings = request.get("input_mapping", [])
    if mappings in (None, []):
        return body, {"status": "skipped", "input_keys": []}
    if not isinstance(mappings, list):
        raise ConnectorExecutionError("connector.request.input_mapping must be a list")

    context_root = context if isinstance(context, dict) else {}
    mapped_keys = []
    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            raise ConnectorExecutionError(f"connector.request.input_mapping[{index}] must be an object")
        source = str(mapping.get("from") or "")
        target = str(mapping.get("to") or "")
        if not source.startswith("/input/") or source == "/input/":
            raise ConnectorExecutionError(f"connector.request.input_mapping[{index}].from must start with /input/")
        if not target.startswith("/body/") or target == "/body/":
            raise ConnectorExecutionError(f"connector.request.input_mapping[{index}].to must start with /body/")
        required = mapping.get("required", True)
        if not isinstance(required, bool):
            raise ConnectorExecutionError(f"connector.request.input_mapping[{index}].required must be a boolean")
        value = _json_pointer_get(context_root, source)
        if value is _MISSING:
            if required:
                raise ConnectorExecutionError(f"required input mapping value missing: {source}")
            continue
        _json_pointer_set_body(body, target, copy.deepcopy(value))
        mapped_keys.append(_input_key(source))

    mapped_keys = sorted({key for key in mapped_keys if key})
    return body, {
        "status": "applied" if mapped_keys else "skipped",
        "input_keys": mapped_keys,
    }


_MISSING = object()


def _json_pointer_get(root: object, pointer: str):
    current = root
    for token in _json_pointer_tokens(pointer):
        if isinstance(current, dict):
            if token not in current:
                return _MISSING
            current = current[token]
            continue
        return _MISSING
    return current


def _json_pointer_set_body(body: Dict[str, object], pointer: str, value: object) -> None:
    tokens = _json_pointer_tokens(pointer)
    if not tokens or tokens[0] != "body" or len(tokens) < 2:
        raise ConnectorExecutionError("input mapping target must start with /body/")
    current = body
    for token in tokens[1:-1]:
        existing = current.get(token)
        if existing is None:
            existing = {}
            current[token] = existing
        if not isinstance(existing, dict):
            raise ConnectorExecutionError(f"input mapping target parent is not an object: /body/{token}")
        current = existing
    current[tokens[-1]] = value


def _json_pointer_tokens(pointer: str) -> List[str]:
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]


def _input_key(source: str) -> str:
    tokens = _json_pointer_tokens(source)
    if len(tokens) >= 2 and tokens[0] == "input":
        return tokens[1]
    return ""
