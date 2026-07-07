"""Local external connector fixture for Loop 33."""

from __future__ import annotations

import copy
from typing import Dict, List

from skill2workflow.connectors import (
    CONNECTOR_EXECUTION_CONTRACT_VERSION,
    CONNECTOR_MANIFEST_VERSION,
    ConnectorExecutionError,
)
from skill2workflow.credentials import CredentialResolutionError


MANIFEST = {
    "manifest_version": CONNECTOR_MANIFEST_VERSION,
    "id": "local_echo",
    "name": "Local Echo Connector",
    "kind": "local_echo",
    "status": "active",
    "node_types": ["tool_call"],
    "description": "External fixture connector that echoes compact request metadata for local tests.",
    "config_schema": {
        "type": "object",
        "properties": {
            "request": {
                "type": "object",
                "properties": {
                    "body": {"type": "object"},
                    "input_mapping": {"type": "array"},
                },
            }
        },
    },
    "execution_contract": {
        "contract_version": CONNECTOR_EXECUTION_CONTRACT_VERSION,
        "mode": "external",
        "entrypoint": "examples/connectors/local_echo_connector.py:execute",
        "receives": ["node.connector", "run_context", "credential_provider"],
        "returns": ["status", "connector", "output", "error", "input_mapping", "credentials"],
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


def execute(binding: Dict[str, object], credential_provider=None, context=None) -> Dict[str, object]:
    """Execute the local echo fixture without returning raw business values."""
    if not isinstance(binding, dict):
        raise ConnectorExecutionError("local_echo connector binding must be an object")

    request = binding.get("request", {})
    if request is None:
        request = {}
    if not isinstance(request, dict):
        raise ConnectorExecutionError("local_echo connector.request must be an object")

    body, mapping_summary = _mapped_body(request, context)
    credential_summary = _resolve_credentials(binding.get("credentials", []), credential_provider)

    return {
        "status": "completed",
        "connector": {"id": "local_echo", "kind": "local_echo"},
        "output": {
            "body_keys": sorted(str(key) for key in body.keys()),
            "credential_handles": credential_summary["handles"],
            "received_input_keys": mapping_summary.get("input_keys", []),
        },
        "credentials": credential_summary,
        "input_mapping": mapping_summary,
    }


def _resolve_credentials(credentials: object, credential_provider) -> Dict[str, object]:
    if credentials in (None, []):
        return {"status": "skipped", "handles": []}
    if not isinstance(credentials, list):
        raise ConnectorExecutionError("connector.credentials must be a list")

    handles: List[str] = []
    for index, credential in enumerate(credentials):
        if not isinstance(credential, dict):
            raise ConnectorExecutionError(f"connector.credentials[{index}] must be an object")
        target = str(credential.get("target") or "")
        if target != "header":
            raise ConnectorExecutionError(f"connector.credentials[{index}].target must be header")
        handle = str(credential.get("handle") or "")
        if not handle:
            raise ConnectorExecutionError(f"connector.credentials[{index}].handle is required")
        if credential_provider is None:
            raise ConnectorExecutionError(f"credential handle not found: {handle}")
        try:
            credential_provider.resolve(handle)
        except CredentialResolutionError as error:
            raise ConnectorExecutionError(str(error))
        handles.append(handle)

    return {"status": "resolved", "handles": sorted(handles)}


def _mapped_body(request: Dict[str, object], context: object):
    body = copy.deepcopy(request.get("body", {}))
    if body is None:
        body = {}
    if not isinstance(body, dict):
        raise ConnectorExecutionError("local_echo connector.request.body must be an object")

    mappings = request.get("input_mapping", [])
    if mappings in (None, []):
        return body, {}
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
