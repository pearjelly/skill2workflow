"""Built-in connector manifests and local connector execution."""

from __future__ import annotations

import copy
import json
import socket
import urllib.error
import urllib.request
from typing import Dict, List


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


def execute_connector(node: Dict[str, object]) -> ConnectorResult:
    """Execute a node's connector binding and return a normalized result."""
    binding = node.get("connector")
    ref = connector_ref(binding)
    if not ref["id"]:
        raise ConnectorExecutionError(f"{node.get('id', '<node>')} has no connector binding")
    if ref["id"] == "http":
        return _execute_http_connector(binding)
    if ref["id"] == "manual":
        raise ConnectorExecutionError("manual connector is resumed through human gate state")
    raise ConnectorExecutionError(f"unsupported connector: {ref['id']}")


def _execute_http_connector(binding: object) -> ConnectorResult:
    if not isinstance(binding, dict):
        raise ConnectorExecutionError("http connector binding must be an object")
    request_spec = binding.get("request")
    if not isinstance(request_spec, dict):
        raise ConnectorExecutionError("http connector requires connector.request")

    url = str(request_spec.get("url") or "")
    if not url.startswith(("http://", "https://")):
        raise ConnectorExecutionError("http connector request.url must be http:// or https://")

    method = str(request_spec.get("method") or "GET").upper()
    headers = _string_map(request_spec.get("headers"))
    body = request_spec.get("body")
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


def _timeout_seconds(value: object) -> float:
    if isinstance(value, (int, float)) and value > 0:
        return float(value) / 1000
    return 5.0
