"""Validate explicit Skill HTTP actions without credential or network access."""

import copy
import json

from .connectors import (
    ConnectorExecutionError,
    MAX_HTTP_PAYLOAD_BYTES,
    _is_http_token,
    _normalize_input_mapping,
    _validate_http_request_metadata,
    normalize_http_allowed_origins,
)


def skill_http_action_binding(config):
    """Return a copied existing HTTP binding with metadata-only retention default."""
    try:
        if not isinstance(config, dict) or set(config) - {"request", "credentials"}:
            raise ValueError()
        request = config.get("request")
        if not isinstance(request, dict) or set(request) - {
            "url", "method", "headers", "body", "timeout_ms",
            "allowed_origins", "input_mapping", "response_mode",
        }:
            raise ValueError()
        url, method, headers = request.get("url"), request.get("method", "GET"), request.get("headers", {})
        if not isinstance(url, str) or not isinstance(method, str) or not isinstance(headers, dict):
            raise ValueError()
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in headers.items()):
            raise ValueError()
        _validate_http_request_metadata(url, method, headers)
        if "timeout_ms" in request and (type(request["timeout_ms"]) is not int or not 0 <= request["timeout_ms"] <= 86400000):
            raise ValueError()
        if request.get("response_mode", "metadata") not in ("full", "metadata"):
            raise ValueError()
        if "allowed_origins" in request:
            if not isinstance(request["allowed_origins"], list):
                raise ValueError()
            normalize_http_allowed_origins(request["allowed_origins"])
        mappings = request.get("input_mapping", [])
        if not isinstance(mappings, list):
            raise ValueError()
        for mapping in mappings:
            if (not isinstance(mapping, dict) or set(mapping) - {"from", "to", "required"}
                    or not isinstance(mapping.get("from"), str) or not isinstance(mapping.get("to"), str)):
                raise ValueError()
        normalized = _normalize_input_mapping(mappings)
        body = request.get("body")
        if body is not None and not isinstance(body, dict) and any(item["target_kind"] == "body" for item in normalized):
            raise ValueError()
        if "body" in request:
            encoded = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
            if len(encoded) > MAX_HTTP_PAYLOAD_BYTES:
                raise ValueError()
        credentials = config.get("credentials", [])
        if not isinstance(credentials, list) or len(credentials) > 32:
            raise ValueError()
        credential_header_shape = dict(headers)
        for item in credentials:
            if (not isinstance(item, dict) or set(item) != {"target", "name", "handle"}
                    or item["target"] != "header" or not isinstance(item["name"], str)
                    or not item["name"] or not _is_http_token(item["name"])
                    or not isinstance(item["handle"], str) or not item["handle"]
                    or len(item["handle"].encode("utf-8")) > 1024):
                raise ValueError()
            credential_header_shape[item["name"]] = ""
        _validate_http_request_metadata(url, method, credential_header_shape)
        binding = copy.deepcopy(config)
        binding.update(id="http", kind="http")
        binding["request"].setdefault("response_mode", "metadata")
        return binding
    except (ConnectorExecutionError, ValueError, TypeError, AttributeError,
            UnicodeError, OverflowError, RecursionError) as error:
        raise ValueError("Invalid Skill step annotation") from error
