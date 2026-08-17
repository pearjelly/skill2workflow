"""Built-in connector manifests and local connector execution."""

from __future__ import annotations

import copy
import json
import socket
import urllib.error
import urllib.request
from contextlib import closing
from dataclasses import dataclass
from typing import Callable, Dict, List
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .credentials import CredentialResolutionError


ConnectorBinding = Dict[str, object]
ConnectorResult = Dict[str, object]
ExternalConnectorExecutor = Callable[..., ConnectorResult]
ExternalConnectorPreflight = Callable[..., ConnectorResult]

CONNECTOR_MANIFEST_VERSION = "skill2workflow-connector-0.1.0"
CONNECTOR_EXECUTION_CONTRACT_VERSION = "skill2workflow-connector-execution-0.1.0"
MAX_HTTP_PAYLOAD_BYTES = 1_048_576
MAX_HTTP_URL_BYTES = 16_384
MAX_HTTP_HEADER_COUNT = 64
MAX_HTTP_HEADER_BYTES = 65_536
MAX_HTTP_METHOD_BYTES = 32
MAX_HTTP_ALLOWED_ORIGINS = 32
MAX_HTTP_ORIGIN_BYTES = 512
HTTP_RESPONSE_MODES = ("full", "metadata")
# External connector code is explicitly loaded, but its normalized result still
# crosses the durable executor boundary. Keep that handoff bounded independently
# of whatever I/O policy the extension chose internally.
MAX_EXTERNAL_CONNECTOR_RESULT_BYTES = 1_048_576


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
        "description": "Built-in connector for bounded HTTP requests from tool-call nodes.",
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
                        "allowed_origins": {
                            "type": "array",
                            "maxItems": MAX_HTTP_ALLOWED_ORIGINS,
                            "items": {"type": "string"},
                        },
                        "timeout_ms": {"type": "integer"},
                        "response_mode": {"type": "string", "enum": list(HTTP_RESPONSE_MODES)},
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


class _HTTPRedirectRejected(Exception):
    """Internal signal raised when an HTTP response attempts a redirect."""

    def __init__(self, code: int):
        self.code = code
        super().__init__(f"HTTP redirect {code}")


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject all HTTP redirects before urllib can replay a request."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            fp.close()
        except (AttributeError, OSError):
            pass
        raise _HTTPRedirectRejected(int(code))


@dataclass(frozen=True)
class ExternalConnector:
    """Explicitly registered external connector fixture."""

    manifest: Dict[str, object]
    executor: ExternalConnectorExecutor
    preflight: ExternalConnectorPreflight = None


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
            preflight=connector.preflight,
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
    try:
        result = connector.executor(
            copy.deepcopy(binding),
            credential_provider=credential_provider,
            context=context,
        )
    except ConnectorExecutionError:
        # Preserve the explicit connector contract for expected validation or
        # credential failures. Unexpected fixture exceptions use the fixed
        # boundary below so provider/transport text cannot cross the runtime.
        raise
    except Exception as error:
        raise ConnectorExecutionError("external connector execution failed") from error
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
    audit = _normalize_compact_metadata(result.get("audit"))
    if audit:
        normalized["audit"] = audit
    input_mapping = result.get("input_mapping")
    if isinstance(input_mapping, dict) and input_mapping:
        normalized["input_mapping"] = copy.deepcopy(input_mapping)
    credentials = _normalize_credential_summary(result.get("credentials"))
    if credentials:
        normalized["credentials"] = credentials
    try:
        encoded = json.dumps(
            normalized,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as error:
        raise ConnectorExecutionError(
            "external connector result must be JSON serializable"
        ) from error
    if len(encoded) > MAX_EXTERNAL_CONNECTOR_RESULT_BYTES:
        raise ConnectorExecutionError(
            "external connector result exceeds "
            f"{MAX_EXTERNAL_CONNECTOR_RESULT_BYTES} bytes"
        )
    # Round-trip through the standard JSON representation so arbitrary Python
    # objects from an extension cannot remain attached to durable run state.
    try:
        return json.loads(encoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ConnectorExecutionError(
            "external connector result must be JSON serializable"
        ) from error


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


def _normalize_compact_metadata(summary: object) -> Dict[str, object]:
    if not isinstance(summary, dict) or not summary:
        return {}

    normalized: Dict[str, object] = {}
    for key, value in summary.items():
        normalized_key = str(key)
        if not normalized_key:
            continue
        if isinstance(value, (str, bool, int, float)) or value is None:
            normalized[normalized_key] = value
            continue
        if isinstance(value, list):
            compact_values = []
            for item in value:
                if isinstance(item, (str, bool, int, float)) or item is None:
                    compact_values.append(item)
            normalized[normalized_key] = compact_values
    return normalized


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
    response_mode = _http_response_mode(request_spec.get("response_mode"))
    headers = _string_map(request_spec.get("headers"))
    _validate_http_request_metadata(url, method, headers)
    url, body, mapping_summary = _mapped_http_request(request_spec, context)
    _validate_http_request_metadata(url, method, headers)
    _validate_http_destination(url, request_spec.get("allowed_origins"))
    _apply_http_credentials(binding.get("credentials", []), headers, credential_provider)
    _validate_http_request_metadata(url, method, headers)
    data = None
    if body is not None:
        try:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        except (
            TypeError,
            ValueError,
            OverflowError,
            RecursionError,
            UnicodeError,
        ) as error:
            # The exception text can include a repr of a mapped value.  Keep
            # the durable connector failure fixed and value-free.
            raise ConnectorExecutionError(
                "http connector request.body must be JSON serializable"
            ) from error
        if len(data) > MAX_HTTP_PAYLOAD_BYTES:
            raise ConnectorExecutionError(
                f"http connector request body exceeds {MAX_HTTP_PAYLOAD_BYTES} bytes"
            )
        if not any(key.lower() == "content-type" for key in headers):
            headers["Content-Type"] = "application/json"
    _validate_http_request_metadata(url, method, headers)

    timeout_ms = request_spec.get("timeout_ms", 5000)
    timeout = _timeout_seconds(timeout_ms)
    try:
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
    except (TypeError, ValueError, UnicodeError) as error:
        raise ConnectorExecutionError("http connector request metadata is invalid") from error

    try:
        with _open_http_request(request, timeout=timeout) as response:
            payload = _read_http_payload(response, "response")
            return {
                "status": "completed",
                "connector": {"id": "http", "kind": "http"},
                "output": _http_response_output(response, int(response.status), payload, response_mode),
                "input_mapping": mapping_summary,
            }
    except _HTTPRedirectRejected as error:
        raise ConnectorExecutionError("http connector redirects are disabled") from error
    except urllib.error.HTTPError as error:
        with closing(error):
            payload = _read_http_payload(error, "response")
            return {
                "status": "failed",
                "connector": {"id": "http", "kind": "http"},
                "output": _http_response_output(error, int(error.code), payload, response_mode),
                "error": f"HTTP {error.code}",
                "input_mapping": mapping_summary,
            }
    except (TimeoutError, socket.timeout) as error:
        # Do not persist provider/network exception text: it may contain the
        # configured URL, proxy details, or other request-specific values.
        raise ConnectorExecutionError("http connector timed out") from error
    except urllib.error.URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            raise ConnectorExecutionError("http connector timed out") from error
        raise ConnectorExecutionError("http connector request failed") from error
    except OSError as error:
        # Some transports surface a raw socket/SSL error instead of URLError.
        raise ConnectorExecutionError("http connector request failed") from error


def _open_http_request(request: urllib.request.Request, timeout: float):
    """Open one direct HTTP request without proxy or redirect replay."""

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout)


def _http_response_mode(value: object) -> str:
    """Normalize the bounded response retention policy."""

    if value is None:
        return "full"
    if isinstance(value, str) and value in HTTP_RESPONSE_MODES:
        return value
    raise ConnectorExecutionError(
        "http connector request.response_mode must be full or metadata"
    )


def _validate_http_request_metadata(url: str, method: str, headers: Dict[str, str]) -> None:
    """Reject oversized or malformed request metadata before credential/network use."""

    try:
        url_bytes = url.encode("utf-8")
    except UnicodeError as error:
        raise ConnectorExecutionError("http connector request.url is invalid") from error
    if len(url_bytes) > MAX_HTTP_URL_BYTES:
        raise ConnectorExecutionError(
            f"http connector request URL exceeds {MAX_HTTP_URL_BYTES} bytes"
        )
    if any(character in url for character in "\r\n\x00"):
        raise ConnectorExecutionError("http connector request.url is invalid")
    try:
        parsed_url = urlsplit(url)
        hostname = parsed_url.hostname
        parsed_url.port
    except ValueError as error:
        raise ConnectorExecutionError("http connector request.url is invalid") from error
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc or not hostname:
        raise ConnectorExecutionError("http connector request.url is invalid")
    if parsed_url.username is not None or parsed_url.password is not None:
        raise ConnectorExecutionError("http connector request.url must not contain userinfo")

    try:
        method_bytes = method.encode("ascii")
    except UnicodeEncodeError as error:
        raise ConnectorExecutionError("http connector request.method is invalid") from error
    if not method_bytes or len(method_bytes) > MAX_HTTP_METHOD_BYTES or not _is_http_token(method):
        raise ConnectorExecutionError("http connector request.method is invalid")

    if len(headers) > MAX_HTTP_HEADER_COUNT:
        raise ConnectorExecutionError(
            f"http connector request headers exceed {MAX_HTTP_HEADER_COUNT} entries"
        )
    header_bytes = 0
    for name, value in headers.items():
        if not name or not _is_http_token(name) or any(character in value for character in "\r\n\x00"):
            raise ConnectorExecutionError("http connector request headers contain invalid characters")
        try:
            header_bytes += len(name.encode("utf-8")) + len(value.encode("utf-8")) + 2
        except UnicodeError as error:
            raise ConnectorExecutionError("http connector request headers contain invalid characters") from error
    if header_bytes > MAX_HTTP_HEADER_BYTES:
        raise ConnectorExecutionError(
            f"http connector request headers exceed {MAX_HTTP_HEADER_BYTES} bytes"
        )


def _is_http_token(value: str) -> bool:
    separators = '()<>@,;:\\"/[]?={} \t'
    return all(33 <= ord(character) <= 126 and character not in separators for character in value)


def _validate_http_destination(url: str, allowed_origins: object) -> None:
    """Enforce an optional exact-origin egress allowlist before credentials/network."""

    if allowed_origins is None:
        return
    if not isinstance(allowed_origins, list) or not allowed_origins:
        raise ConnectorExecutionError(
            "http connector request.allowed_origins must be a non-empty list"
        )
    if len(allowed_origins) > MAX_HTTP_ALLOWED_ORIGINS:
        raise ConnectorExecutionError(
            f"http connector request.allowed_origins exceeds {MAX_HTTP_ALLOWED_ORIGINS} entries"
        )
    request_origin = _normalize_http_origin(url, "http connector request.url")
    normalized = []
    for index, origin in enumerate(allowed_origins):
        if not isinstance(origin, str):
            raise ConnectorExecutionError(
                f"http connector request.allowed_origins[{index}] must be an origin string"
            )
        normalized.append(
            _normalize_http_origin(
                origin,
                f"http connector request.allowed_origins[{index}]",
                require_origin=True,
            )
        )
    if request_origin not in normalized:
        raise ConnectorExecutionError("http connector request URL is not in allowed_origins")


def _normalize_http_origin(value: str, label: str, require_origin: bool = False) -> str:
    try:
        if len(value.encode("utf-8")) > MAX_HTTP_ORIGIN_BYTES:
            raise ConnectorExecutionError(f"{label} exceeds {MAX_HTTP_ORIGIN_BYTES} bytes")
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except (UnicodeError, ValueError) as error:
        raise ConnectorExecutionError(f"{label} is invalid") from error
    if parsed.scheme not in ("http", "https") or not parsed.netloc or not hostname:
        raise ConnectorExecutionError(f"{label} is invalid")
    if parsed.username is not None or parsed.password is not None:
        raise ConnectorExecutionError(f"{label} must not contain userinfo")
    if require_origin and (parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ConnectorExecutionError(f"{label} must not contain a path, query, or fragment")
    default_port = 80 if parsed.scheme == "http" else 443
    port_suffix = "" if port in (None, default_port) else f":{port}"
    host = hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"{parsed.scheme}://{host}{port_suffix}"


def _http_response_output(response: object, status_code: int, payload: str, mode: str) -> Dict[str, object]:
    """Return a full or metadata-only response projection."""

    if mode == "metadata":
        return {
            "status_code": status_code,
            "header_count": len(dict(response.headers.items())),
            "body_bytes": len(payload.encode("utf-8")),
            "body_discarded": True,
        }
    return {
        "status_code": status_code,
        "headers": dict(response.headers.items()),
        "body": payload,
    }


def _read_http_payload(response: object, kind: str) -> str:
    """Read one bounded UTF-8 HTTP payload without retaining an oversized body."""

    try:
        raw = bytearray()
        while len(raw) < MAX_HTTP_PAYLOAD_BYTES + 1:
            chunk = response.read(MAX_HTTP_PAYLOAD_BYTES + 1 - len(raw))
            if not chunk:
                break
            if not isinstance(chunk, (bytes, bytearray)):
                raise ConnectorExecutionError(
                    f"http connector {kind} body could not be read"
                )
            raw.extend(chunk)
    except ConnectorExecutionError:
        raise
    except Exception as error:
        raise ConnectorExecutionError(
            f"http connector {kind} body could not be read"
        ) from error
    if len(raw) > MAX_HTTP_PAYLOAD_BYTES:
        raise ConnectorExecutionError(
            f"http connector {kind} body exceeds {MAX_HTTP_PAYLOAD_BYTES} bytes"
        )
    try:
        return bytes(raw).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ConnectorExecutionError(
            f"http connector {kind} body must be valid UTF-8"
        ) from error


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


def _mapped_http_request(request_spec: Dict[str, object], context: object):
    input_mapping = request_spec.get("input_mapping", [])
    if input_mapping in (None, []):
        return str(request_spec.get("url") or ""), request_spec.get("body"), {}

    mappings = _normalize_input_mapping(input_mapping)
    body = copy.deepcopy(request_spec.get("body"))
    body_mapped = any(mapping["target_kind"] == "body" for mapping in mappings)
    if body_mapped:
        if body is None:
            body = {}
        if not isinstance(body, dict):
            raise ConnectorExecutionError(
                "http connector request.body must be an object when body input_mapping is used"
            )

    url = str(request_spec.get("url") or "")
    query_parts = None
    query_url = None
    if any(mapping["target_kind"] == "query" for mapping in mappings):
        try:
            query_url = urlsplit(url)
        except ValueError as error:
            raise ConnectorExecutionError("http connector request.url is invalid") from error
        query_parts = parse_qsl(query_url.query, keep_blank_values=True)

    context_root = context if isinstance(context, dict) else {}
    mapped_keys = []
    for mapping in mappings:
        value = _json_pointer_get(context_root, mapping["from"])
        if value is _MISSING:
            if mapping["required"]:
                raise ConnectorExecutionError(f"required input mapping value missing: {mapping['from']}")
            continue
        if mapping["target_kind"] == "body":
            _json_pointer_set_body(body, mapping["to"], copy.deepcopy(value))
        else:
            query_value = _query_string_value(value)
            query_parts = [
                (key, existing)
                for key, existing in (query_parts or [])
                if key != mapping["query_key"]
            ]
            query_parts.append((mapping["query_key"], query_value))
        mapped_keys.append(_input_key(mapping["from"]))

    mapped_keys = sorted({key for key in mapped_keys if key})
    if query_url is not None:
        url = urlunsplit(
            (
                query_url.scheme,
                query_url.netloc,
                query_url.path,
                urlencode(query_parts or [], doseq=True),
                query_url.fragment,
            )
        )
    return url, body, {
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
        if target.startswith("/body/") and target != "/body/":
            target_kind = "body"
            query_key = ""
        elif target.startswith("/query/"):
            query_tokens = _json_pointer_tokens(target)
            if len(query_tokens) != 2 or not query_tokens[1]:
                raise ConnectorExecutionError(
                    f"connector.request.input_mapping[{index}].to must be /query/<name>"
                )
            target_kind = "query"
            query_key = query_tokens[1]
        else:
            raise ConnectorExecutionError(
                f"connector.request.input_mapping[{index}].to must start with /body/ or /query/"
            )
        required = mapping.get("required", True)
        if not isinstance(required, bool):
            raise ConnectorExecutionError(f"connector.request.input_mapping[{index}].required must be a boolean")
        normalized.append(
            {
                "from": source,
                "to": target,
                "required": required,
                "target_kind": target_kind,
                "query_key": query_key,
            }
        )
    return normalized


def _query_string_value(value: object) -> str:
    """Convert one input value to a deterministic scalar query parameter."""

    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            encoded = None
        if encoded is not None:
            return encoded
    raise ConnectorExecutionError(
        "http connector query input mapping value must be a string, number, or boolean"
    )


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
