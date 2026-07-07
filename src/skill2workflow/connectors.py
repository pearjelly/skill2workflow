"""Built-in connector manifests and local connector execution."""

from __future__ import annotations

import copy
import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, List

from .credentials import CredentialResolutionError


ConnectorBinding = Dict[str, object]
ConnectorResult = Dict[str, object]
ExternalConnectorExecutor = Callable[..., ConnectorResult]

CONNECTOR_MANIFEST_VERSION = "skill2workflow-connector-0.1.0"
CONNECTOR_EXECUTION_CONTRACT_VERSION = "skill2workflow-connector-execution-0.1.0"


DEFAULT_CONNECTORS: List[Dict[str, object]] = [
    {
        "manifest_version": CONNECTOR_MANIFEST_VERSION,
        "id": "manual",
        "name": "Manual Human Gate",
        "kind": "manual",
        "status": "active",
        "node_types": ["human_gate"],
        "description": "Built-in connector for local human approval and manual review gates.",
        "config_schema": {"type": "object", "additionalProperties": True},
        "execution_contract": {
            "contract_version": CONNECTOR_EXECUTION_CONTRACT_VERSION,
            "mode": "built_in",
            "entrypoint": "human_gate_run_state",
            "receives": ["node.connector", "run_state"],
            "returns": ["run_event", "node_result"],
        },
        "credential_contract": {
            "supports_handles": False,
            "targets": [],
            "resolved_value_policy": "never_in_workflow_run_state_or_audit",
        },
        "audit_contract": {
            "value_policy": "compact_no_payload_values",
            "events": ["human_gate_waiting", "human_gate_resumed"],
        },
    },
    {
        "manifest_version": CONNECTOR_MANIFEST_VERSION,
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
        "execution_contract": {
            "contract_version": CONNECTOR_EXECUTION_CONTRACT_VERSION,
            "mode": "built_in",
            "entrypoint": "skill2workflow.connectors:execute_connector",
            "receives": ["node.connector", "run_context", "credential_provider"],
            "returns": ["status", "connector", "output", "error", "input_mapping"],
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
    },
]


class ConnectorExecutionError(Exception):
    """Raised when a connector binding cannot be executed."""


@dataclass(frozen=True)
class ExternalConnector:
    """Explicitly registered external connector fixture."""

    manifest: Dict[str, object]
    executor: ExternalConnectorExecutor


class ConnectorRuntime:
    """Execute built-in connectors plus explicitly registered external fixtures."""

    def __init__(self, external_connectors: List[ExternalConnector] = None):
        self._external_connectors: Dict[str, ExternalConnector] = {}
        for connector in external_connectors or []:
            self.register_external_connector(connector)

    def register_external_connector(self, connector: ExternalConnector) -> None:
        """Register one external connector fixture after validating its manifest."""
        if not isinstance(connector, ExternalConnector):
            raise ValueError("external connector must be an ExternalConnector")
        errors = validate_connector_manifest(connector.manifest)
        if errors:
            raise ValueError("; ".join(errors))
        execution_contract = connector.manifest.get("execution_contract", {})
        if not isinstance(execution_contract, dict) or execution_contract.get("mode") != "external":
            raise ValueError("external connector manifest must use execution_contract.mode external")
        connector_id = str(connector.manifest.get("id") or "")
        built_in_ids = {str(manifest["id"]) for manifest in DEFAULT_CONNECTORS}
        if connector_id in built_in_ids:
            raise ValueError(f"external connector id conflicts with built-in connector: {connector_id}")
        if not callable(connector.executor):
            raise ValueError("external connector executor must be callable")
        self._external_connectors[connector_id] = ExternalConnector(
            manifest=copy.deepcopy(connector.manifest),
            executor=connector.executor,
        )

    def list_connectors(self) -> List[Dict[str, object]]:
        """Return built-in manifests plus explicitly registered external manifests."""
        manifests = default_connectors()
        manifests.extend(copy.deepcopy(item.manifest) for item in self._external_connectors.values())
        return manifests

    def execute_connector(self, node: Dict[str, object], credential_provider=None, context=None) -> ConnectorResult:
        """Execute a connector through the built-in path or an explicit external fixture."""
        binding = node.get("connector")
        ref = connector_ref(binding)
        if ref["id"] in self._external_connectors:
            return _execute_external_connector(
                self._external_connectors[ref["id"]],
                binding,
                ref,
                credential_provider=credential_provider,
                context=context,
            )
        return execute_connector(node, credential_provider=credential_provider, context=context)


def default_connectors() -> List[Dict[str, object]]:
    """Return built-in connector manifests."""
    return copy.deepcopy(DEFAULT_CONNECTORS)


def validate_connector_manifest(manifest: object) -> List[str]:
    """Return connector manifest contract errors without loading external code."""
    if not isinstance(manifest, dict):
        return ["connector manifest must be an object"]

    errors = []
    if manifest.get("manifest_version") != CONNECTOR_MANIFEST_VERSION:
        errors.append(f"manifest_version must be {CONNECTOR_MANIFEST_VERSION}")
    if not str(manifest.get("id") or ""):
        errors.append("id is required")
    if not str(manifest.get("kind") or ""):
        errors.append("kind is required")
    if not str(manifest.get("status") or ""):
        errors.append("status is required")

    node_types = manifest.get("node_types")
    if not isinstance(node_types, list) or not node_types or not all(isinstance(item, str) and item for item in node_types):
        errors.append("node_types must be a non-empty list")
    if not isinstance(manifest.get("config_schema"), dict):
        errors.append("config_schema must be an object")

    execution_contract = manifest.get("execution_contract")
    if not isinstance(execution_contract, dict):
        errors.append("execution_contract must be an object")
    else:
        if execution_contract.get("contract_version") != CONNECTOR_EXECUTION_CONTRACT_VERSION:
            errors.append(f"execution_contract.contract_version must be {CONNECTOR_EXECUTION_CONTRACT_VERSION}")
        if execution_contract.get("mode") not in ("built_in", "external"):
            errors.append("execution_contract.mode must be built_in or external")
        if not str(execution_contract.get("entrypoint") or ""):
            errors.append("execution_contract.entrypoint is required")
        receives = execution_contract.get("receives")
        if not isinstance(receives, list) or not receives:
            errors.append("execution_contract.receives must be a non-empty list")
        returns = execution_contract.get("returns")
        if not isinstance(returns, list) or not returns:
            errors.append("execution_contract.returns must be a non-empty list")

    credential_contract = manifest.get("credential_contract")
    if not isinstance(credential_contract, dict):
        errors.append("credential_contract must be an object")
    else:
        if not isinstance(credential_contract.get("supports_handles"), bool):
            errors.append("credential_contract.supports_handles must be a boolean")
        targets = credential_contract.get("targets")
        if not isinstance(targets, list):
            errors.append("credential_contract.targets must be a list")
        if not str(credential_contract.get("resolved_value_policy") or ""):
            errors.append("credential_contract.resolved_value_policy is required")

    audit_contract = manifest.get("audit_contract")
    if not isinstance(audit_contract, dict):
        errors.append("audit_contract must be an object")
    else:
        if not str(audit_contract.get("value_policy") or ""):
            errors.append("audit_contract.value_policy is required")
        events = audit_contract.get("events")
        if not isinstance(events, list) or not events:
            errors.append("audit_contract.events must be a non-empty list")

    return errors


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


def _execute_external_connector(
    connector: ExternalConnector,
    binding: object,
    ref: Dict[str, str],
    credential_provider=None,
    context=None,
) -> ConnectorResult:
    if not isinstance(binding, dict):
        raise ConnectorExecutionError("external connector binding must be an object")
    result = connector.executor(copy.deepcopy(binding), credential_provider=credential_provider, context=context)
    if not isinstance(result, dict):
        raise ConnectorExecutionError("external connector executor must return an object")

    status = str(result.get("status") or "")
    if status not in {"completed", "failed"}:
        raise ConnectorExecutionError("external connector result.status must be completed or failed")

    result_connector = connector_ref(result.get("connector") or ref)
    if result_connector["id"] != ref["id"]:
        raise ConnectorExecutionError("external connector result.connector.id must match the binding connector.id")
    if not result_connector["kind"]:
        result_connector["kind"] = ref["kind"]

    normalized = {
        "status": status,
        "connector": result_connector,
        "output": result.get("output") if isinstance(result.get("output"), dict) else {},
    }
    if result.get("error"):
        normalized["error"] = str(result.get("error"))
    input_mapping = result.get("input_mapping")
    if isinstance(input_mapping, dict) and input_mapping:
        normalized["input_mapping"] = copy.deepcopy(input_mapping)
    credentials = _normalize_credential_summary(result.get("credentials"))
    if credentials:
        normalized["credentials"] = credentials
    return normalized


def _normalize_credential_summary(summary: object) -> Dict[str, object]:
    if not isinstance(summary, dict) or not summary:
        return {}
    handles = summary.get("handles", [])
    if not isinstance(handles, list):
        handles = []
    return {
        "status": str(summary.get("status") or ""),
        "handles": sorted({str(handle) for handle in handles if str(handle)}),
    }


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
