"""Local trigger envelope helpers."""

from __future__ import annotations

import uuid
from typing import Dict


Trigger = Dict[str, object]


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

    return {
        "trigger_id": _optional_text(request, "trigger_id") or f"trigger_{uuid.uuid4().hex[:12]}",
        "workflow_id": workflow_id,
        "version": version,
        "source": _optional_text(request, "source") or "local",
        "idempotency_key": _optional_text(request, "idempotency_key"),
        "input_keys": sorted(str(key) for key in trigger_input.keys()),
    }


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
