"""Durable local Workflow DSL executor."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .connectors import ConnectorExecutionError, ConnectorRuntime, connector_ref
from .storage import create_run_store


RunState = Dict[str, object]


class LocalExecutor:
    """Execute Workflow DSL with pluggable local run-state storage."""

    def __init__(
        self,
        state_dir: Path,
        storage: str = "json",
        credential_provider=None,
        connector_runtime=None,
        execution_owner: str = "",
    ):
        self.state_dir = Path(state_dir)
        self.store = create_run_store(self.state_dir, storage)
        self.credential_provider = credential_provider
        self.connector_runtime = connector_runtime or ConnectorRuntime()
        self.execution_owner = str(execution_owner or "")
        self._execution_ids: Dict[str, str] = {}

    def run(self, workflow: Dict[str, object], context: Dict[str, object] = None) -> RunState:
        workflow_meta = workflow.get("workflow", {})
        if not isinstance(workflow_meta, dict):
            workflow_meta = {}
        if context is None:
            run_context = {}
        elif isinstance(context, dict):
            run_context = copy.deepcopy(context)
        else:
            raise ValueError("run context must be a JSON object")

        state: RunState = {
            "run_id": f"run_{uuid.uuid4().hex[:12]}",
            "workflow_id": workflow_meta.get("id", "workflow"),
            "workflow_version": workflow_meta.get("version", "0.1.0"),
            "status": "created",
            "current_node": workflow.get("entry", "start"),
            "context": run_context,
            "node_results": {},
            "events": [],
            "workflow": workflow,
        }
        if self.execution_owner:
            execution_id = f"execution_{uuid.uuid4().hex}"
            self.store.start_execution(
                state, self.execution_owner, execution_id
            )
            self._execution_ids[str(state["run_id"])] = execution_id
        else:
            self._save(state)
        try:
            return self._drive(state)
        finally:
            self._execution_ids.pop(str(state["run_id"]), None)

    def resume(self, run_id: str, approved: bool = True) -> RunState:
        state = self._load(run_id)
        if state["status"] != "waiting":
            raise ValueError(f"run {run_id} is not waiting")

        workflow = state["workflow"]
        node = self._node_map(workflow)[state["current_node"]]
        next_node = node.get("on_success") if approved else node.get("on_failure")
        if not isinstance(next_node, str):
            raise ValueError(f"run {run_id} cannot resume from {node['id']}")

        if self.execution_owner:
            execution_id = f"execution_{uuid.uuid4().hex}"
            self.store.claim_execution(
                run_id, self.execution_owner, execution_id
            )
            self._execution_ids[run_id] = execution_id

        result = {
            "status": "approved" if approved else "rejected",
            "title": node.get("title", node["id"]),
            "approved": approved,
            "timestamp": _now(),
        }
        if node.get("type") == "human_gate":
            result["connector"] = connector_ref(node.get("connector") or {"id": "manual", "kind": "manual"})
        state["node_results"][node["id"]] = result
        state["events"].append(
            {
                "type": "human_gate_resumed",
                "node_id": node["id"],
                "approved": approved,
                "connector_id": "manual",
                "connector_kind": "manual",
                "timestamp": _now(),
            }
        )
        state["status"] = "running"
        state["current_node"] = next_node
        try:
            self._save(state)
            if state["status"] == "cancelled":
                return state
            return self._drive(state)
        finally:
            self._execution_ids.pop(run_id, None)

    def cancel(self, run_id: str) -> RunState:
        """Request durable cancellation and apply it immediately when safely waiting."""

        state, _ = self.request_cancel(run_id)
        return state

    def request_cancel(self, run_id: str):
        """Return cancellation state plus whether this call created the request."""

        return self.store.request_cancellation(run_id)

    def list_runs(self) -> List[RunState]:
        return [_summarize_run(state) for state in self.store.list()]

    def snapshot_window(self, limit: int) -> Dict[str, object]:
        """Return a bounded SQLite run window and aggregate status counts."""

        window = self.store.snapshot_window(limit)
        return {
            "total": window["total"],
            "status_counts": window["status_counts"],
            "items": [_summarize_run(state) for state in window["items"]],
        }

    def get_run(self, run_id: str) -> RunState:
        return self._load(run_id)

    def recover_interrupted_runs(self) -> List[RunState]:
        if not self.execution_owner:
            raise ValueError("interrupted run recovery requires an execution owner")
        return self.store.recover_interrupted(self.execution_owner)

    def _drive(self, state: RunState) -> RunState:
        if state.get("status") == "cancelled":
            return state
        workflow = state["workflow"]
        node_map = self._node_map(workflow)
        state["status"] = "running"
        self._save(state)
        if state["status"] == "cancelled":
            return state

        cancelled = self._cancel_if_requested(state)
        if cancelled is not None:
            return cancelled

        for _ in range(len(node_map) + 1):
            cancelled = self._cancel_if_requested(state)
            if cancelled is not None:
                return cancelled
            self._ensure_execution_active(state)
            current_id = state["current_node"]
            node = node_map[current_id]
            node_type = node.get("type")

            if node_type == "end":
                state["status"] = "completed"
                state["node_results"][current_id] = {
                    "status": "completed",
                    "title": node.get("title", current_id),
                    "timestamp": _now(),
                }
                self._event(state, "run_completed", current_id)
                self._save(state)
                return state

            if node_type == "failure":
                state["status"] = "failed"
                state["node_results"][current_id] = {
                    "status": "failed",
                    "title": node.get("title", current_id),
                    "timestamp": _now(),
                }
                self._event(state, "run_failed", current_id)
                self._save(state)
                return state

            if node_type == "human_gate":
                state["status"] = "waiting"
                self._event(
                    state,
                    "human_gate_waiting",
                    current_id,
                    {"connector_id": "manual", "connector_kind": "manual"},
                )
                self._save(state)
                return state

            if node_type == "tool_call":
                finished = self._execute_connector_node(state, node, current_id, node_map)
                if finished is not None:
                    return finished
                continue

            self._event(state, "node_started", current_id)
            state["node_results"][current_id] = {
                "status": "completed",
                "title": node.get("title", current_id),
                "timestamp": _now(),
            }
            self._event(state, "node_completed", current_id)

            next_node = node.get("on_success")
            if not isinstance(next_node, str) or next_node not in node_map:
                state["status"] = "failed"
                state["error"] = f"{current_id} has no valid on_success target"
                self._event(state, "run_failed", current_id)
                self._save(state)
                return state

            state["current_node"] = next_node
            self._save(state)

        state["status"] = "failed"
        state["error"] = "execution exceeded workflow node count"
        self._save(state)
        return state

    def _execute_connector_node(
        self,
        state: RunState,
        node: Dict[str, object],
        current_id: str,
        node_map: Dict[str, Dict[str, object]],
    ):
        ref = connector_ref(node.get("connector"))
        if not ref["id"]:
            state["status"] = "failed"
            state["error"] = f"{current_id} has no connector binding"
            state["node_results"][current_id] = {
                "status": "failed",
                "title": node.get("title", current_id),
                "error": state["error"],
                "timestamp": _now(),
            }
            self._event(state, "run_failed", current_id)
            self._save(state)
            return state

        max_attempts = _retry_max_attempts(node, state.get("workflow", {}))
        self._event(state, "node_started", current_id, {"max_attempts": max_attempts})
        last_error = ""
        connector_result = {}
        attempts = 0
        recovered = False

        for attempt in range(1, max_attempts + 2):
            cancelled = self._cancel_if_requested(state)
            if cancelled is not None:
                return cancelled
            self._ensure_execution_active(state)
            attempts = attempt
            self._event(
                state,
                "connector_started",
                current_id,
                {
                    "connector_id": ref["id"],
                    "connector_kind": ref["kind"],
                    "connector_status": "running",
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                },
            )
            self._save(state)
            if state.get("status") == "cancelled":
                return state
            self._ensure_execution_active(state)
            try:
                connector_result = self.connector_runtime.execute_connector(
                    node,
                    credential_provider=self.credential_provider,
                    context=_connector_context(state, current_id),
                )
            except ConnectorExecutionError as error:
                connector_result = {
                    "status": "failed",
                    "connector": ref,
                    "error": str(error),
                    "output": {},
                }

            result_status = str(connector_result.get("status", "failed"))
            if result_status == "completed":
                recovered = attempt > 1
                break

            last_error = str(connector_result.get("error") or "connector failed")
            self._event(
                state,
                "connector_failed",
                current_id,
                {
                    "connector_id": ref["id"],
                    "connector_kind": ref["kind"],
                    "connector_status": "failed",
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "error": last_error,
                },
            )
            cancelled = self._cancel_if_requested(state)
            if cancelled is not None:
                return cancelled
            if attempt <= max_attempts:
                self._event(
                    state,
                    "node_retrying",
                    current_id,
                    {
                        "attempt": attempt,
                        "next_attempt": attempt + 1,
                        "max_attempts": max_attempts,
                        "error": last_error,
                    },
                )
            self._save(state)
            if state.get("status") == "cancelled":
                return state

        result_status = str(connector_result.get("status", "failed"))
        node_result = {
            "status": result_status,
            "title": node.get("title", current_id),
            "connector": connector_result.get("connector", ref),
            "output": connector_result.get("output", {}),
            "attempts": attempts,
            "max_attempts": max_attempts,
            "timestamp": _now(),
        }
        mapping_summary = connector_result.get("input_mapping")
        if isinstance(mapping_summary, dict) and mapping_summary:
            node_result["input_mapping"] = mapping_summary
        credential_summary = connector_result.get("credentials")
        if isinstance(credential_summary, dict) and credential_summary:
            node_result["credentials"] = credential_summary
        audit_summary = connector_result.get("audit")
        if isinstance(audit_summary, dict) and audit_summary:
            node_result["audit"] = audit_summary
        if last_error:
            node_result["last_error"] = last_error
        if connector_result.get("error"):
            node_result["error"] = connector_result["error"]
        state["node_results"][current_id] = node_result

        if result_status == "completed":
            self._event(
                state,
                "connector_completed",
                current_id,
                {
                    "connector_id": ref["id"],
                    "connector_kind": ref["kind"],
                    "connector_status": "completed",
                    "attempt": attempts,
                    "max_attempts": max_attempts,
                    **_input_mapping_event_fields(mapping_summary),
                    **_credential_event_fields(credential_summary),
                    **_connector_audit_event_fields(audit_summary),
                },
            )
            if recovered:
                self._event(
                    state,
                    "node_recovered",
                    current_id,
                    {
                        "attempt": attempts,
                        "max_attempts": max_attempts,
                        "error": last_error,
                    },
                )
            self._event(state, "node_completed", current_id)
            next_node = node.get("on_success")
        else:
            self._event(
                state,
                "node_failed",
                current_id,
                {
                    "attempt": attempts,
                    "max_attempts": max_attempts,
                    "error": last_error,
                    **_input_mapping_event_fields(mapping_summary),
                    **_credential_event_fields(credential_summary),
                    **_connector_audit_event_fields(audit_summary),
                },
            )
            next_node = node.get("on_failure")

        cancelled = self._cancel_if_requested(state)
        if cancelled is not None:
            return cancelled

        if not isinstance(next_node, str) or next_node not in node_map:
            state["status"] = "failed"
            state["error"] = f"{current_id} has no valid connector transition target"
            self._event(state, "run_failed", current_id)
            self._save(state)
            return state

        state["current_node"] = next_node
        self._save(state)
        return None

    def _cancel_if_requested(self, state: RunState):
        run_id = str(state.get("run_id", ""))
        if not run_id or not self.store.cancellation_requested(run_id):
            return None
        if str(state.get("status", "")) in {
            "completed",
            "failed",
            "cancelled",
            "interrupted",
        }:
            return None
        self._event(state, "run_cancel_requested", str(state.get("current_node", "")))
        state["status"] = "cancelled"
        self._event(state, "run_cancelled", str(state.get("current_node", "")))
        self._save(state)
        self.store.mark_cancellation_applied(run_id)
        return state

    def _event(self, state: RunState, event_type: str, node_id: str, extra: Dict[str, object] = None) -> None:
        event = {
            "type": event_type,
            "node_id": node_id,
            "timestamp": _now(),
        }
        if extra:
            event.update(extra)
        state["events"].append(event)

    def _save(self, state: RunState) -> None:
        run_id = str(state.get("run_id", ""))
        execution_id = self._execution_ids.get(run_id, "")
        if self.execution_owner and execution_id:
            self.store.save_execution(
                state, self.execution_owner, execution_id
            )
            return
        self.store.save(state)

    def _ensure_execution_active(self, state: RunState) -> None:
        run_id = str(state.get("run_id", ""))
        execution_id = self._execution_ids.get(run_id, "")
        if self.execution_owner and execution_id:
            self.store.ensure_execution_active(
                run_id, self.execution_owner, execution_id
            )

    def _load(self, run_id: str) -> RunState:
        return self.store.load(run_id)

    @staticmethod
    def _node_map(workflow: Dict[str, object]) -> Dict[str, Dict[str, object]]:
        return {node["id"]: node for node in workflow.get("nodes", [])}


def _connector_context(state: RunState, node_id: str) -> Dict[str, object]:
    durable = state.get("context", {})
    context = copy.deepcopy(durable) if isinstance(durable, dict) else {}
    context["_execution"] = {
        "workflow_id": str(state.get("workflow_id", "")),
        "workflow_version": str(state.get("workflow_version", "")),
        "run_id": str(state.get("run_id", "")),
        "node_id": str(node_id),
    }
    return context


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _retry_max_attempts(node: Dict[str, object], workflow: object) -> int:
    retry = node.get("retry")
    if isinstance(retry, dict) and retry.get("max_attempts") is not None:
        return _non_negative_int(retry.get("max_attempts"))

    if isinstance(workflow, dict):
        policies = workflow.get("policies")
        if isinstance(policies, dict):
            default_retry = policies.get("default_retry")
            if isinstance(default_retry, dict):
                return _non_negative_int(default_retry.get("max_attempts"))
    return 0


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value > 0:
        return value
    return 0


def _input_mapping_event_fields(summary: object) -> Dict[str, object]:
    if not isinstance(summary, dict) or not summary:
        return {}
    fields = {"input_mapping_status": str(summary.get("status", ""))}
    keys = summary.get("input_keys", [])
    if isinstance(keys, list):
        fields["input_mapping_keys"] = [str(key) for key in keys]
    return fields


def _credential_event_fields(summary: object) -> Dict[str, object]:
    if not isinstance(summary, dict) or not summary:
        return {}
    fields = {"credential_status": str(summary.get("status", ""))}
    handles = summary.get("handles", [])
    if isinstance(handles, list):
        fields["credential_handles"] = [str(handle) for handle in handles]
    return fields


def _connector_audit_event_fields(summary: object) -> Dict[str, object]:
    if not isinstance(summary, dict) or not summary:
        return {}
    return {"connector_metadata": copy.deepcopy(summary)}


def _summarize_run(state: RunState) -> RunState:
    return {
        "run_id": state["run_id"],
        "workflow_id": state["workflow_id"],
        "workflow_version": state["workflow_version"],
        "status": state["status"],
        "current_node": state["current_node"],
        "event_count": len(state.get("events", [])),
        "node_result_count": len(state.get("node_results", {})),
    }
