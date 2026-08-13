"""Local trigger envelope helpers."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from typing import Dict


Trigger = Dict[str, object]
MAX_IDEMPOTENCY_KEY_BYTES = 128
MAX_TRIGGER_INPUT_BYTES = 1024 * 1024
_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.:+-]+$")


class TriggerIdempotencyError(ValueError):
    """Raised when a durable trigger key cannot safely be reused."""

    _MESSAGES = {
        "conflict": "idempotency key conflicts with an existing request",
        "unresolved": "idempotency key has an unresolved outcome; use a new key",
    }
    status_code = 409

    def __init__(self, reason: str):
        if reason not in self._MESSAGES:
            reason = "unresolved"
        self.reason = reason
        super().__init__(self._MESSAGES[reason])


def normalize_trigger_request(request: object) -> Trigger:
    """Validate and normalize a local trigger request envelope."""

    if not isinstance(request, dict):
        raise ValueError("trigger request must be a JSON object")

    workflow_id = _required_text(request, "workflow_id")
    version = _required_text(request, "version")
    trigger_input = request.get("input", {})
    if trigger_input is None:
        trigger_input = {}
    if not isinstance(trigger_input, dict):
        raise ValueError("trigger input must be a JSON object")
    normalized_input = normalize_trigger_input(trigger_input)
    idempotency_key = _optional_text(request, "idempotency_key")
    if idempotency_key:
        encoded_key = idempotency_key.encode("utf-8")
        if (
            len(encoded_key) > MAX_IDEMPOTENCY_KEY_BYTES
            or not _IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key)
        ):
            raise ValueError(
                "idempotency_key must contain only letters, numbers, _, ., :, +, or - "
                f"and be at most {MAX_IDEMPOTENCY_KEY_BYTES} UTF-8 bytes"
            )

    return {
        "trigger_id": _optional_text(request, "trigger_id") or f"trigger_{uuid.uuid4().hex[:12]}",
        "workflow_id": workflow_id,
        "version": version,
        "source": _optional_text(request, "source") or "local",
        "idempotency_key": idempotency_key,
        "input": normalized_input,
        "input_keys": sorted(normalized_input.keys()),
    }


def normalize_trigger_input(value: object, label: str = "trigger input") -> Dict[str, object]:
    """Copy one JSON object under the shared bounded trigger-input contract."""

    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return _json_object_copy(value, label)


def trigger_request_fingerprint(trigger: Trigger) -> str:
    """Hash the replay-relevant trigger request without persisting its values."""

    payload = {
        "workflow_id": str(trigger.get("workflow_id", "")),
        "version": str(trigger.get("version", "")),
        "source": str(trigger.get("source", "")),
        "idempotency_key": str(trigger.get("idempotency_key", "")),
        "input": copy.deepcopy(trigger.get("input", {}))
        if isinstance(trigger.get("input", {}), dict)
        else {},
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def trigger_audit_fields(trigger: Trigger) -> Dict[str, object]:
    """Return compact trigger metadata suitable for control-plane audit events."""

    return {
        "trigger_id": str(trigger.get("trigger_id", "")),
        "trigger_source": str(trigger.get("source", "local")),
        "idempotency_key": str(trigger.get("idempotency_key", "")),
        "input_keys": list(trigger.get("input_keys", [])) if isinstance(trigger.get("input_keys"), list) else [],
    }


def trigger_response(trigger: Trigger, state: Dict[str, object]) -> Dict[str, object]:
    """Return a compact response for a triggered published run."""

    return {
        "trigger_id": str(trigger.get("trigger_id", "")),
        "workflow_id": str(trigger.get("workflow_id", "")),
        "workflow_version": str(trigger.get("version", "")),
        "run_id": str(state.get("run_id", "")),
        "run_status": str(state.get("status", "")),
        "source": str(trigger.get("source", "local")),
        "idempotency_key": str(trigger.get("idempotency_key", "")),
        "input_keys": list(trigger.get("input_keys", [])) if isinstance(trigger.get("input_keys"), list) else [],
    }


def trigger_run_context(trigger: Trigger) -> Dict[str, object]:
    """Return durable run context derived from a normalized trigger."""

    return {
        "trigger": {
            "trigger_id": str(trigger.get("trigger_id", "")),
            "source": str(trigger.get("source", "local")),
            "idempotency_key": str(trigger.get("idempotency_key", "")),
            "input_keys": list(trigger.get("input_keys", [])) if isinstance(trigger.get("input_keys"), list) else [],
        },
        "input": copy.deepcopy(trigger.get("input", {})) if isinstance(trigger.get("input"), dict) else {},
    }


def _required_text(request: Dict[str, object], key: str) -> str:
    value = request.get(key)
    if value is None or str(value).strip() == "":
        raise ValueError(f"{key} is required")
    return str(value)


def _optional_text(request: Dict[str, object], key: str) -> str:
    value = request.get(key, "")
    if value is None:
        return ""
    return str(value)


def _json_object_copy(value: Dict[str, object], label: str) -> Dict[str, object]:
    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError(f"{label} must be JSON serializable: {error}")
    encoded = serialized.encode("utf-8")
    if len(encoded) > MAX_TRIGGER_INPUT_BYTES:
        raise ValueError(
            f"{label} exceeds {MAX_TRIGGER_INPUT_BYTES} bytes"
        )
    try:
        copied = json.loads(serialized)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} must be JSON serializable: {error}")
    if not isinstance(copied, dict):
        raise ValueError(f"{label} must be a JSON object")
    return copied
