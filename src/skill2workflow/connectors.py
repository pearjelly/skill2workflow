"""Built-in connector manifests and local connector execution."""

from __future__ import annotations

import copy
import json
import socket
import urllib.error
import urllib.request
from typing import Dict, List

from .credentials import CredentialResolutionError


ConnectorBinding = Dict[str, object]
ConnectorResult = Dict[str, object]


DEFAULT_CONNECTORS: List[Dict[str, object]] = [
    {
        "id": "manual",
        "name": "Manual Human Gate",
        "kind": "manual",
        "status": "active",
        "node_types": ["human_gate"],
        "description": "Built-in connector for local human approval and manual review gates.",
        "config_schema": {"type": "object", "additionalProperties": True},
    },
    {
        "id": "http",
        "name": "HTTP Connector",
        "kind": "http",
        "status": "active",
        "node_types": ["tool_call"],
        "description": "Built-in connector for minimal HTTP requests from tool-call nodes.",
        "config_schema": {
            "type": "object",
            "properties": {
                "request": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string"},
                        "url": {"type": "string"},
                        "headers": {"type": "object"},
                        "body": {},
                        "input_mapping": {"type": "array"},
                        "timeout_ms": {"type": "integer"},
                    },
                    "required": ["url"],
                }
            },
        },
    },
]


class ConnectorExecutionError(Exception):
    """Raised when a connector binding cannot be executed."""


def default_connectors() -> List[Dict[str, object]]:
    """Return built-in connector manifests."""
    return copy.deepcopy(DEFAULT_CONNECTORS)


def default_connector_binding(node_type: str) -> ConnectorBinding:
    """Return the default connector binding for a DSL node type."""
    if node_type == "human_gate":
        return {"id": "manual", "kind": "manual"}
    if node_type == "tool_call":
        return {"id": "http", "kind": "http"}
    return {}


def connector_ref(binding: object) -> Dict[str, str]:
    """Return a small connector reference for events and node results."""
    if not isinstance(binding, dict):
        return {"id": "", "kind": ""}
    connector_id = str(binding.get("id") or "")
    connector_kind = str(binding.get("kind") or connector_id)
    return {"id": connector_id, "kind": connector_kind}


def execute_connector(node: Dict[str, object], credential_provider=None, context=None) -> ConnectorResult:
    """Execute a node's connector binding and return a normalized result."""
    binding = node.get("connector")
    ref = connector_ref(binding)
    if not ref["id"]:
        raise ConnectorExecutionError(f"{node.get('id', '<node>')} has no connector binding")
    if ref["id"] == "http":
        return _execute_http_connector(binding, credential_provider=credential_provider, context=context)
    if ref["id"] == "manual":
        raise ConnectorExecutionError("manual connector is resumed through human gate state")
    raise ConnectorExecutionError(f"unsupported connector: {ref['id']}")


def _execute_http_connector(binding: object, credential_provider=None, context=None) -> ConnectorResult:
    if not isinstance(binding, dict):
        raise ConnectorExecutionError("http connector binding must be an object")
    request_spec = binding.get("request")
    if not isinstance(request_spec, dict):
        raise ConnectorExecutionError("http connector requires connector.request")
    request_spec = copy.deepcopy(request_spec)

    url = str(request_spec.get("url") or "")
    if not url.startswith(("http://", "https://")):
        raise ConnectorExecutionError("http connector request.url must be http:// or https://")

    method = str(request_spec.get("method") or "GET").upper()
    headers = _string_map(request_spec.get("headers"))
    _apply_http_credentials(binding.get("credentials", []), headers, credential_provider)
    body, mapping_summary = _mapped_http_body(request_spec, context)
    data = None
    if body is not None:
        try:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise ConnectorExecutionError(f"http connector request.body must be JSON serializable: {error}")
        if not any(key.lower() == "content-type" for key in headers):
            headers["Content-Type"] = "application/json"

    timeout_ms = request_spec.get("timeout_ms", 5000)
    timeout = _timeout_seconds(timeout_ms)
    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return {
                "status": "completed",
                "connector": {"id": "http", "kind": "http"},
                "output": {
                    "status_code": int(response.status),
                    "headers": dict(response.headers.items()),
                    "body": payload,
                },
                "input_mapping": mapping_summary,
            }
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        return {
            "status": "failed",
            "connector": {"id": "http", "kind": "http"},
            "output": {
                "status_code": int(error.code),
                "headers": dict(error.headers.items()),
                "body": payload,
            },
            "error": f"HTTP {error.code}",
            "input_mapping": mapping_summary,
        }
    except (TimeoutError, socket.timeout) as error:
        raise ConnectorExecutionError(f"http connector timed out: {error}")
    except urllib.error.URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            raise ConnectorExecutionError(f"http connector timed out: {error.reason}")
        raise ConnectorExecutionError(str(error.reason))


def _string_map(value: object) -> Dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _apply_http_credentials(credentials: object, headers: Dict[str, str], credential_provider) -> None:
    if credentials in (None, []):
        return
    if not isinstance(credentials, list):
        raise ConnectorExecutionError("connector.credentials must be a list")

    for index, credential in enumerate(credentials):
        if not isinstance(credential, dict):
            raise ConnectorExecutionError(f"connector.credentials[{index}] must be an object")
        target = str(credential.get("target") or "")
        if target != "header":
            raise ConnectorExecutionError(f"connector.credentials[{index}].target must be header")
        name = str(credential.get("name") or "")
        if not name:
            raise ConnectorExecutionError(f"connector.credentials[{index}].name is required")
        handle = str(credential.get("handle") or "")
        if not handle:
            raise ConnectorExecutionError(f"connector.credentials[{index}].handle is required")
        if credential_provider is None:
            raise ConnectorExecutionError(f"credential handle not found: {handle}")
        try:
            value = credential_provider.resolve(handle)
        except CredentialResolutionError as error:
            raise ConnectorExecutionError(str(error))
        headers[name] = f"{credential.get('prefix', '') or ''}{value}"


def _mapped_http_body(request_spec: Dict[str, object], context: object):
    input_mapping = request_spec.get("input_mapping", [])
    if input_mapping in (None, []):
        return request_spec.get("body"), {}

    mappings = _normalize_input_mapping(input_mapping)
    body = copy.deepcopy(request_spec.get("body", {}))
    if body is None:
        body = {}
    if not isinstance(body, dict):
        raise ConnectorExecutionError("http connector request.body must be an object when input_mapping is used")

    context_root = context if isinstance(context, dict) else {}
    mapped_keys = []
    for mapping in mappings:
        value = _json_pointer_get(context_root, mapping["from"])
        if value is _MISSING:
            if mapping["required"]:
                raise ConnectorExecutionError(f"required input mapping value missing: {mapping['from']}")
            continue
        _json_pointer_set_body(body, mapping["to"], copy.deepcopy(value))
        mapped_keys.append(_input_key(mapping["from"]))

    mapped_keys = sorted({key for key in mapped_keys if key})
    return body, {
        "status": "applied" if mapped_keys else "skipped",
        "input_keys": mapped_keys,
    }


def _normalize_input_mapping(input_mapping: object) -> List[Dict[str, object]]:
    if not isinstance(input_mapping, list):
        raise ConnectorExecutionError("connector.request.input_mapping must be a list")
    normalized = []
    for index, mapping in enumerate(input_mapping):
        if not isinstance(mapping, dict):
            raise ConnectorExecutionError(f"connector.request.input_mapping[{index}] must be an object")
        source = str(mapping.get("from") or "")
        target = str(mapping.get("to") or "")
        if source == "/input/" or not source.startswith("/input/"):
            raise ConnectorExecutionError(f"connector.request.input_mapping[{index}].from must start with /input/")
        if target == "/body/" or not target.startswith("/body/"):
            raise ConnectorExecutionError(f"connector.request.input_mapping[{index}].to must start with /body/")
        required = mapping.get("required", True)
        if not isinstance(required, bool):
            raise ConnectorExecutionError(f"connector.request.input_mapping[{index}].required must be a boolean")
        normalized.append({"from": source, "to": target, "required": required})
    return normalized


_MISSING = object()


def _json_pointer_get(root: object, pointer: str):
    current = root
    for token in _json_pointer_tokens(pointer):
        if isinstance(current, dict):
            if token not in current:
                return _MISSING
            current = current[token]
            continue
        if isinstance(current, list) and token.isdigit():
            index = int(token)
            if index >= len(current):
                return _MISSING
            current = current[index]
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


def _timeout_seconds(value: object) -> float:
    if isinstance(value, (int, float)) and value > 0:
        return float(value) / 1000
    return 5.0
