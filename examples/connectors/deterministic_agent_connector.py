"""Deterministic Agent protocol fixture; no network, provider or SDK."""

from skill2workflow.agent_protocol import AGENT_PROTOCOL_VERSION
from skill2workflow.connectors import CONNECTOR_MANIFEST_VERSION, CONNECTOR_EXECUTION_CONTRACT_VERSION

MANIFEST = {
    "manifest_version": CONNECTOR_MANIFEST_VERSION,
    "id": "deterministic_agent", "name": "Deterministic Agent Fixture",
    "kind": "agent", "status": "active", "node_types": ["tool_call"],
    "config_schema": {"type": "object"},
    "execution_contract": {
        "contract_version": CONNECTOR_EXECUTION_CONTRACT_VERSION, "mode": "external",
        "protocol": AGENT_PROTOCOL_VERSION,
        "entrypoint": "examples/connectors/deterministic_agent_connector.py:execute",
        "receives": ["instruction", "context"], "returns": ["status", "output"],
    },
    "credential_contract": {"supports_handles": False, "targets": [],
                            "resolved_value_policy": "never_in_workflow_run_state_or_audit"},
    "audit_contract": {"value_policy": "compact_no_payload_values",
                       "events": ["connector_started", "connector_completed", "connector_failed"]},
}


def execute(payload, credential_provider=None, context=None):
    risk = payload["context"]["input"].get("risk", "low")
    return {"status": "completed", "output": {
        "risk": "high" if risk == "high" else "low", "reason": {"source": "deterministic"},
    }}
