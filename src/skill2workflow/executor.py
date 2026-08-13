"""Durable local Workflow DSL executor."""

from __future__ import annotations

import copy
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List

from .connectors import ConnectorExecutionError, ConnectorRuntime, connector_ref
from .storage import create_run_store


RunState = Dict[str, object]
MAX_ACTIVE_TIMEOUT_MS = 86_400_000
MAX_WORKFLOW_TIMEOUT_MS = 2_592_000_000
MAX_RETRY_BACKOFF_MS = 60_000
MAX_WORKFLOW_DEADLINE_SWEEP_RUNS = 256


class LocalExecutor:
    """Execute Workflow DSL with pluggable local run-state storage."""

    def __init__(
        self,
        state_dir: Path,
        storage: str = "json",
        credential_provider=None,
        connector_runtime=None,
        execution_owner: str = "",
        clock: Callable[[], str] = None,
        sleeper: Callable[[float], None] = None,
    ):
        self.state_dir = Path(state_dir)
        self.store = create_run_store(self.state_dir, storage)
        self.credential_provider = credential_provider
        self.connector_runtime = connector_runtime or ConnectorRuntime()
        self.execution_owner = str(execution_owner or "")
        self._clock = clock or _now
        self._sleep = sleeper or time.sleep
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

        timeout_ms = _execution_timeout_ms(workflow)
        workflow_timeout_ms = _workflow_timeout_ms(workflow)

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
            "execution": {
                "timeout_ms": timeout_ms,
                "started_at": "",
                "deadline_at": "",
                "workflow_timeout_ms": workflow_timeout_ms,
                "workflow_started_at": "",
                "workflow_deadline_at": "",
            },
        }
        self._start_workflow_window(state)
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
            "timestamp": self._now(),
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
                "timestamp": self._now(),
            }
        )
        state["status"] = "running"
        self._start_workflow_window(state)
        timed_out = self._workflow_timeout_if_exceeded(state)
        if timed_out is not None:
            return timed_out
        state["current_node"] = next_node
        self._clear_execution_window(state)
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

    def expire_workflow_deadlines(
        self, now: str = None, limit: int = MAX_WORKFLOW_DEADLINE_SWEEP_RUNS
    ) -> List[RunState]:
        """Expire bounded waiting runs without resuming workflow execution."""

        timestamp = self._now() if now is None else str(now)
        return self.store.expire_waiting_workflow_deadlines(timestamp, limit=limit)

    def list_workflow_timeout_runs(
        self, limit: int = MAX_WORKFLOW_DEADLINE_SWEEP_RUNS
    ) -> List[RunState]:
        """Return bounded terminal timeout states for audit reconciliation."""

        return self.store.list_workflow_timeout_runs(limit=limit)

    def _drive(self, state: RunState) -> RunState:
        if state.get("status") == "cancelled":
            return state
        workflow = state["workflow"]
        node_map = self._node_map(workflow)
        state["status"] = "running"
        self._start_workflow_window(state)
        self._start_execution_window(state)
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
            timed_out = self._workflow_timeout_if_exceeded(state)
            if timed_out is not None:
                return timed_out
            timed_out = self._timeout_if_exceeded(state)
            if timed_out is not None:
                return timed_out
            self._ensure_execution_active(state)
            current_id = state["current_node"]
            node = node_map[current_id]
            node_type = node.get("type")

            if node_type == "end":
                state["status"] = "completed"
                self._clear_execution_window(state)
                self._clear_workflow_window(state)
                state["node_results"][current_id] = {
                    "status": "completed",
                    "title": node.get("title", current_id),
                    "timestamp": self._now(),
                }
                self._event(state, "run_completed", current_id)
                self._save(state)
                return state

            if node_type == "failure":
                state["status"] = "failed"
                self._clear_execution_window(state)
                self._clear_workflow_window(state)
                state["node_results"][current_id] = {
                    "status": "failed",
                    "title": node.get("title", current_id),
                    "timestamp": self._now(),
                }
                self._event(state, "run_failed", current_id)
                self._save(state)
                return state

            if node_type == "human_gate":
                state["status"] = "waiting"
                self._clear_execution_window(state)
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
                "timestamp": self._now(),
            }
            self._event(state, "node_completed", current_id)

            next_node = node.get("on_success")
            if not isinstance(next_node, str) or next_node not in node_map:
                state["status"] = "failed"
                state["error"] = f"{current_id} has no valid on_success target"
                self._clear_workflow_window(state)
                self._event(state, "run_failed", current_id)
                self._save(state)
                return state

            state["current_node"] = next_node
            self._save(state)

        state["status"] = "failed"
        state["error"] = "execution exceeded workflow node count"
        self._clear_workflow_window(state)
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
            self._clear_workflow_window(state)
            state["node_results"][current_id] = {
                "status": "failed",
                "title": node.get("title", current_id),
                "error": state["error"],
                "timestamp": self._now(),
            }
            self._event(state, "run_failed", current_id)
            self._save(state)
            return state

        max_attempts = _retry_max_attempts(node, state.get("workflow", {}))
        backoff_ms = _retry_backoff_ms(node, state.get("workflow", {}))
        self._event(
            state,
            "node_started",
            current_id,
            {"max_attempts": max_attempts, "backoff_ms": backoff_ms},
        )
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

            timed_out = self._workflow_timeout_if_exceeded(state)
            if timed_out is None:
                timed_out = self._timeout_if_exceeded(state)
            if timed_out is not None:
                timed_out["node_results"][current_id] = {
                    "status": "failed",
                    "title": node.get("title", current_id),
                    "connector": ref,
                    "attempts": attempts,
                    "max_attempts": max_attempts,
                    "error_code": timed_out.get("error_code", "execution_timeout"),
                    "timestamp": self._now(),
                }
                self._save(timed_out)
                return timed_out

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
                        "backoff_ms": backoff_ms,
                        "error": last_error,
                    },
                )
            self._save(state)
            if state.get("status") == "cancelled":
                return state
            if attempt <= max_attempts and backoff_ms:
                self._sleep(backoff_ms / 1000.0)
                cancelled = self._cancel_if_requested(state)
                if cancelled is not None:
                    return cancelled
                timed_out = self._workflow_timeout_if_exceeded(state)
                if timed_out is None:
                    timed_out = self._timeout_if_exceeded(state)
                if timed_out is not None:
                    timed_out["node_results"][current_id] = {
                        "status": "failed",
                        "title": node.get("title", current_id),
                        "connector": ref,
                        "attempts": attempts,
                        "max_attempts": max_attempts,
                        "backoff_ms": backoff_ms,
                        "error_code": timed_out.get("error_code", "execution_timeout"),
                        "timestamp": self._now(),
                    }
                    self._save(timed_out)
                    return timed_out

        result_status = str(connector_result.get("status", "failed"))
        node_result = {
            "status": result_status,
            "title": node.get("title", current_id),
            "connector": connector_result.get("connector", ref),
            "output": connector_result.get("output", {}),
            "attempts": attempts,
            "max_attempts": max_attempts,
            "backoff_ms": backoff_ms,
            "timestamp": self._now(),
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
            fallback_target = node.get("on_fallback")
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
            if isinstance(fallback_target, str) and fallback_target:
                node_result["fallback_target"] = fallback_target
                self._event(
                    state,
                    "node_fallback",
                    current_id,
                    {
                        "target": fallback_target,
                        "attempt": attempts,
                        "max_attempts": max_attempts,
                        "error": last_error,
                    },
                )
                next_node = fallback_target
            else:
                next_node = node.get("on_failure")

        cancelled = self._cancel_if_requested(state)
        if cancelled is not None:
            return cancelled

        if not isinstance(next_node, str) or next_node not in node_map:
            state["status"] = "failed"
            state["error"] = f"{current_id} has no valid connector transition target"
            self._clear_workflow_window(state)
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
        self._clear_execution_window(state)
        self._clear_workflow_window(state)
        self._event(state, "run_cancelled", str(state.get("current_node", "")))
        self._save(state)
        self.store.mark_cancellation_applied(run_id)
        return state

    def _event(self, state: RunState, event_type: str, node_id: str, extra: Dict[str, object] = None) -> None:
        event = {
            "type": event_type,
            "node_id": node_id,
            "timestamp": self._now(),
        }
        if extra:
            event.update(extra)
        state["events"].append(event)

    def _now(self) -> str:
        return str(self._clock())

    def _start_execution_window(self, state: RunState) -> None:
        execution = state.get("execution")
        if not isinstance(execution, dict):
            execution = {
                "timeout_ms": _execution_timeout_ms(state.get("workflow", {})),
                "started_at": "",
                "deadline_at": "",
                "workflow_timeout_ms": _workflow_timeout_ms(state.get("workflow", {})),
                "workflow_started_at": "",
                "workflow_deadline_at": "",
            }
            state["execution"] = execution
        timeout_ms = _non_negative_int(execution.get("timeout_ms"))
        if timeout_ms <= 0 or str(execution.get("deadline_at", "")):
            return
        started_at = self._now()
        execution["started_at"] = started_at
        execution["deadline_at"] = _deadline_after(started_at, timeout_ms)

    def _start_workflow_window(self, state: RunState) -> None:
        execution = state.get("execution")
        if not isinstance(execution, dict):
            execution = {
                "timeout_ms": _execution_timeout_ms(state.get("workflow", {})),
                "started_at": "",
                "deadline_at": "",
                "workflow_timeout_ms": _workflow_timeout_ms(state.get("workflow", {})),
                "workflow_started_at": "",
                "workflow_deadline_at": "",
            }
            state["execution"] = execution
        execution.setdefault(
            "workflow_timeout_ms",
            _workflow_timeout_ms(state.get("workflow", {})),
        )
        execution.setdefault("workflow_started_at", "")
        execution.setdefault("workflow_deadline_at", "")
        timeout_ms = _non_negative_int(execution.get("workflow_timeout_ms"))
        if timeout_ms <= 0 or str(execution.get("workflow_deadline_at", "")):
            return
        started_at = str(execution.get("workflow_started_at", "")) or self._now()
        execution["workflow_started_at"] = started_at
        execution["workflow_deadline_at"] = _deadline_after(started_at, timeout_ms)

    @staticmethod
    def _clear_execution_window(state: RunState) -> None:
        execution = state.get("execution")
        if not isinstance(execution, dict):
            return
        execution["started_at"] = ""
        execution["deadline_at"] = ""

    @staticmethod
    def _clear_workflow_window(state: RunState) -> None:
        execution = state.get("execution")
        if not isinstance(execution, dict):
            return
        execution["workflow_started_at"] = ""
        execution["workflow_deadline_at"] = ""

    def _workflow_timeout_if_exceeded(self, state: RunState):
        execution = state.get("execution")
        if not isinstance(execution, dict):
            return None
        deadline_at = str(execution.get("workflow_deadline_at", ""))
        if not deadline_at:
            return None
        try:
            expired = _parse_timestamp(self._now()) >= _parse_timestamp(deadline_at)
        except ValueError:
            expired = True
        if not expired:
            return None
        current_id = str(state.get("current_node", ""))
        timeout_ms = _non_negative_int(execution.get("workflow_timeout_ms"))
        state["status"] = "failed"
        state["error_code"] = "workflow_timeout"
        state["error"] = "workflow wall-clock deadline exceeded"
        self._clear_execution_window(state)
        self._clear_workflow_window(state)
        self._event(
            state,
            "run_failed",
            current_id,
            {"error_code": "workflow_timeout", "timeout_ms": timeout_ms},
        )
        self._save(state)
        return state

    def _timeout_if_exceeded(self, state: RunState):
        execution = state.get("execution")
        if not isinstance(execution, dict):
            return None
        deadline_at = str(execution.get("deadline_at", ""))
        if not deadline_at:
            return None
        try:
            expired = _parse_timestamp(self._now()) >= _parse_timestamp(deadline_at)
        except ValueError:
            expired = True
        if not expired:
            return None
        current_id = str(state.get("current_node", ""))
        timeout_ms = _non_negative_int(execution.get("timeout_ms"))
        state["status"] = "failed"
        state["error_code"] = "execution_timeout"
        state["error"] = "workflow active execution exceeded default_timeout_ms"
        self._clear_execution_window(state)
        self._event(
            state,
            "run_failed",
            current_id,
            {"error_code": "execution_timeout", "timeout_ms": timeout_ms},
        )
        self._save(state)
        return state

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


def _execution_timeout_ms(workflow: object) -> int:
    if not isinstance(workflow, dict):
        return 0
    policies = workflow.get("policies")
    if policies is None:
        return 0
    if not isinstance(policies, dict):
        raise ValueError("workflow.policies must be an object")
    if "default_timeout_ms" not in policies:
        return 0
    value = policies.get("default_timeout_ms")
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > MAX_ACTIVE_TIMEOUT_MS
    ):
        raise ValueError(
            "policies.default_timeout_ms must be an integer between 0 and "
            f"{MAX_ACTIVE_TIMEOUT_MS}"
        )
    return value


def _workflow_timeout_ms(workflow: object) -> int:
    if not isinstance(workflow, dict):
        return 0
    policies = workflow.get("policies")
    if policies is None:
        return 0
    if not isinstance(policies, dict):
        raise ValueError("workflow.policies must be an object")
    if "workflow_timeout_ms" not in policies:
        return 0
    value = policies.get("workflow_timeout_ms")
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > MAX_WORKFLOW_TIMEOUT_MS
    ):
        raise ValueError(
            "policies.workflow_timeout_ms must be an integer between 0 and "
            f"{MAX_WORKFLOW_TIMEOUT_MS}"
        )
    return value


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _deadline_after(started_at: str, timeout_ms: int) -> str:
    return (_parse_timestamp(started_at) + timedelta(milliseconds=timeout_ms)).isoformat()


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


def _retry_backoff_ms(node: Dict[str, object], workflow: object) -> int:
    retry = node.get("retry")
    if isinstance(retry, dict) and retry.get("backoff_ms") is not None:
        return _bounded_non_negative_int(retry.get("backoff_ms"), MAX_RETRY_BACKOFF_MS)

    if isinstance(workflow, dict):
        policies = workflow.get("policies")
        if isinstance(policies, dict):
            default_retry = policies.get("default_retry")
            if isinstance(default_retry, dict):
                return _bounded_non_negative_int(
                    default_retry.get("backoff_ms"), MAX_RETRY_BACKOFF_MS
                )
    return 0


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value > 0:
        return value
    return 0


def _bounded_non_negative_int(value: object, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return min(value, maximum)


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
