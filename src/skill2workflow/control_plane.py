"""Minimal local enterprise control plane for Workflow DSL artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .connectors import default_connectors
from .compiler import validate_workflow
from .executor import LocalExecutor, RunState
from .input_schema import InputSchemaValidationError, validate_trigger_input
from .storage import create_control_store
from .triggers import (
    TriggerIdempotencyError,
    normalize_trigger_request,
    trigger_audit_fields,
    trigger_request_fingerprint,
    trigger_response,
    trigger_run_context,
)


Workflow = Dict[str, object]
WorkflowRecord = Dict[str, object]
AuditEvent = Dict[str, object]


class LocalControlPlane:
    """Manage local workflow versions, published runs, and audit events."""

    def __init__(
        self,
        state_dir: Path,
        storage: str = "json",
        credential_provider=None,
        connector_runtime=None,
        execution_owner: str = "",
    ):
        self.state_dir = Path(state_dir)
        self.storage = storage
        self.workflows_dir = self.state_dir / "workflows"
        self.connectors_path = self.state_dir / "connectors.json"
        self.connector_runtime = connector_runtime
        self.executor = LocalExecutor(
            self.state_dir,
            storage=storage,
            credential_provider=credential_provider,
            connector_runtime=connector_runtime,
            execution_owner=execution_owner,
        )
        self.store = create_control_store(self.state_dir, storage=storage)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def publish_workflow(self, workflow: Workflow) -> WorkflowRecord:
        """Publish a validated workflow version as an immutable artifact."""
        errors = validate_workflow(workflow)
        if errors:
            raise ValueError("; ".join(errors))

        workflow_id, version = _workflow_identity(workflow)
        published = copy.deepcopy(workflow)
        workflow_meta = published.setdefault("workflow", {})
        if not isinstance(workflow_meta, dict):
            raise ValueError("workflow.workflow must be an object")
        workflow_meta["status"] = "published"

        artifact_path = self._artifact_path(workflow_id, version)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        checksum = _checksum(published)
        index = self._load_index()
        existing_record = index.get(_record_key(workflow_id, version))

        if artifact_path.exists():
            existing = _load_json(artifact_path)
            if _checksum(existing) != checksum:
                raise ValueError(f"published workflow version is immutable: {workflow_id}@{version}")
            if existing_record:
                return existing_record

        artifact_path.write_text(json.dumps(published, ensure_ascii=False, indent=2), encoding="utf-8")
        now = _now()
        record = {
            "workflow_id": workflow_id,
            "name": workflow_meta.get("name", workflow_id),
            "version": version,
            "status": "published",
            "checksum": checksum,
            "artifact": str(artifact_path.relative_to(self.state_dir)),
            "published_at": now,
        }
        index[_record_key(workflow_id, version)] = record
        self._save_index(index)
        self._append_audit(
            {
                "type": "workflow_published",
                "workflow_id": workflow_id,
                "workflow_version": version,
                "checksum": checksum,
                "timestamp": now,
            }
        )
        return record

    def deprecate_workflow(self, workflow_id: str, version: str) -> WorkflowRecord:
        """Mark a published workflow version as deprecated without mutating its artifact."""
        index = self._load_index()
        key = _record_key(workflow_id, version)
        if key not in index:
            raise ValueError(f"workflow version not found: {workflow_id}@{version}")

        record = dict(index[key])
        if record.get("status") != "deprecated":
            record["status"] = "deprecated"
            record["deprecated_at"] = _now()
            index[key] = record
            self._save_index(index)
            self._append_audit(
                {
                    "type": "workflow_deprecated",
                    "workflow_id": workflow_id,
                    "workflow_version": version,
                    "timestamp": record["deprecated_at"],
                }
            )
        return record

    def list_workflows(self) -> List[WorkflowRecord]:
        records = list(self._load_index().values())
        return sorted(records, key=lambda record: (str(record["workflow_id"]), str(record["version"])))

    def get_workflow(self, workflow_id: str, version: str) -> Workflow:
        record = self._workflow_record(workflow_id, version)
        return _load_json(self.state_dir / str(record["artifact"]))

    def run_published_workflow(self, workflow_id: str, version: str, trigger: Dict[str, object] = None) -> RunState:
        record = self._workflow_record(workflow_id, version)
        if record.get("status") != "published":
            raise ValueError(f"workflow version is not published: {workflow_id}@{version}")

        workflow = self.get_workflow(workflow_id, version)
        if trigger:
            try:
                validate_trigger_input(workflow.get("input_schema"), trigger.get("input", {}))
            except InputSchemaValidationError as error:
                raise ValueError(str(error)) from error

        started_at = _now()
        context = trigger_run_context(trigger) if trigger else None
        state = self.executor.run(workflow, context=context)
        started_event = {
            "type": "run_started",
            "run_id": state["run_id"],
            "workflow_id": workflow_id,
            "workflow_version": version,
            "timestamp": started_at,
        }
        if trigger:
            started_event.update(trigger_audit_fields(trigger))
        self._append_audit(started_event)
        self._append_runtime_audit_events(state, workflow_id, version)
        terminal_event = {
            "type": f"run_{state['status']}",
            "run_id": state["run_id"],
            "workflow_id": workflow_id,
            "workflow_version": version,
            "timestamp": _now(),
        }
        if state.get("error_code"):
            terminal_event["error_code"] = str(state["error_code"])
        self._append_audit(terminal_event)
        return state

    def trigger_workflow(self, request: Dict[str, object]) -> Dict[str, object]:
        """Trigger a published workflow through the local control-plane boundary."""

        trigger = normalize_trigger_request(request)
        workflow_id = str(trigger["workflow_id"])
        workflow_version = str(trigger["version"])
        idempotency_key = str(trigger.get("idempotency_key", ""))
        self._validate_trigger_input(workflow_id, workflow_version, trigger.get("input", {}))
        if self.storage != "sqlite" or not idempotency_key:
            return self._execute_trigger(trigger)

        record = self._workflow_record(workflow_id, workflow_version)
        if record.get("status") != "published":
            raise ValueError(
                f"workflow version is not published: {workflow_id}@{workflow_version}"
            )
        request_fingerprint = trigger_request_fingerprint(trigger)
        claim = self.store.claim_trigger_idempotency(
            workflow_id,
            workflow_version,
            idempotency_key,
            request_fingerprint,
        )
        if str(claim.get("request_fingerprint", "")) != request_fingerprint:
            raise TriggerIdempotencyError("conflict")
        status = str(claim.get("status", ""))
        if status == "completed":
            try:
                cached = json.loads(str(claim.get("response_json", "")))
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                raise TriggerIdempotencyError("unresolved") from error
            if not isinstance(cached, dict):
                raise TriggerIdempotencyError("unresolved")
            return copy.deepcopy(cached)
        if status != "claimed":
            raise TriggerIdempotencyError("unresolved")

        try:
            response = self._execute_trigger(trigger)
            self.store.complete_trigger_idempotency(
                workflow_id,
                workflow_version,
                idempotency_key,
                request_fingerprint,
                response,
            )
            return response
        except BaseException:
            self.store.mark_trigger_idempotency_unresolved(
                workflow_id,
                workflow_version,
                idempotency_key,
                request_fingerprint,
            )
            raise

    def _execute_trigger(self, trigger: Dict[str, object]) -> Dict[str, object]:
        state = self.run_published_workflow(
            str(trigger["workflow_id"]),
            str(trigger["version"]),
            trigger=trigger,
        )
        return trigger_response(trigger, state)

    def _validate_trigger_input(self, workflow_id: str, version: str, value: object) -> None:
        record = self._workflow_record(workflow_id, version)
        if record.get("status") != "published":
            raise ValueError(f"workflow version is not published: {workflow_id}@{version}")
        workflow = self.get_workflow(workflow_id, version)
        try:
            validate_trigger_input(workflow.get("input_schema"), value)
        except InputSchemaValidationError as error:
            raise ValueError(str(error)) from error

    def resume_published_run(self, run_id: str, approved: bool = True) -> RunState:
        current = self.executor.get_run(run_id)
        workflow_id = str(current.get("workflow_id", "workflow"))
        workflow_version = str(current.get("workflow_version", "0.1.0"))
        previous_event_count = len(current.get("events", [])) if isinstance(current.get("events"), list) else 0
        self._workflow_record(workflow_id, workflow_version)
        state = self.executor.resume(run_id, approved=approved)
        self._append_audit(
            {
                "type": "run_resumed",
                "run_id": run_id,
                "workflow_id": workflow_id,
                "workflow_version": workflow_version,
                "approved": approved,
                "timestamp": _now(),
            }
        )
        self._append_runtime_audit_events(state, workflow_id, workflow_version, start_index=previous_event_count)
        terminal_event = {
            "type": f"run_{state['status']}",
            "run_id": run_id,
            "workflow_id": workflow_id,
            "workflow_version": workflow_version,
            "timestamp": _now(),
        }
        if state.get("error_code"):
            terminal_event["error_code"] = str(state["error_code"])
        self._append_audit(terminal_event)
        return state

    def cancel_published_run(self, run_id: str) -> RunState:
        """Request an idempotent cancellation without accepting arbitrary reason text."""

        current = self.executor.get_run(run_id)
        workflow_id = str(current.get("workflow_id", "workflow"))
        workflow_version = str(current.get("workflow_version", "0.1.0"))
        self._workflow_record(workflow_id, workflow_version)
        state, newly_requested = self.executor.request_cancel(run_id)
        if newly_requested:
            self._append_audit(
                {
                    "type": "run_cancel_requested",
                    "run_id": run_id,
                    "workflow_id": workflow_id,
                    "workflow_version": workflow_version,
                    "timestamp": _now(),
                }
            )
            if state["status"] == "cancelled":
                self._append_audit(
                    {
                        "type": "run_cancelled",
                        "run_id": run_id,
                        "workflow_id": workflow_id,
                        "workflow_version": workflow_version,
                        "timestamp": _now(),
                    }
                )
        return state

    def list_runs(self) -> List[RunState]:
        return self.executor.list_runs()

    def get_run(self, run_id: str) -> RunState:
        return self.executor.get_run(run_id)

    def recover_interrupted_runs(self) -> int:
        """Fence abandoned service executions and expose their unknown outcome."""

        recovered = self.executor.recover_interrupted_runs()
        existing = {
            str(event.get("run_id", ""))
            for event in self.list_audit_events(event_type="run_interrupted")
        }
        candidates = {str(state.get("run_id", "")): state for state in recovered}
        for summary in self.executor.list_runs():
            if str(summary.get("status", "")) != "interrupted":
                continue
            run_id = str(summary.get("run_id", ""))
            if run_id and run_id not in candidates:
                candidates[run_id] = self.executor.get_run(run_id)
        for run_id, state in candidates.items():
            interruption = next(
                (
                    event
                    for event in state.get("events", [])
                    if isinstance(event, dict)
                    and event.get("type") == "run_interrupted"
                ),
                None,
            )
            if not interruption or run_id in existing:
                continue
            self._append_audit(
                {
                    "type": "run_interrupted",
                    "run_id": run_id,
                    "workflow_id": str(state.get("workflow_id", "workflow")),
                    "workflow_version": str(
                        state.get("workflow_version", "0.1.0")
                    ),
                    "timestamp": str(interruption.get("timestamp", "")) or _now(),
                }
            )
        return len(recovered)

    def list_audit_events(
        self,
        workflow_id: str = "",
        version: str = "",
        run_id: str = "",
        event_type: str = "",
    ) -> List[AuditEvent]:
        events = self.store.list_audit_events()
        if workflow_id:
            events = [event for event in events if str(event.get("workflow_id", "")) == workflow_id]
        if version:
            events = [event for event in events if str(event.get("workflow_version", "")) == version]
        if run_id:
            events = [event for event in events if str(event.get("run_id", "")) == run_id]
        if event_type:
            events = [event for event in events if str(event.get("type", "")) == event_type]
        return events

    def verify_audit_integrity(self) -> Dict[str, object]:
        """Verify the storage-backed audit evidence without exposing payloads."""

        return self.store.verify_audit_integrity()

    def record_ingress_authentication(
        self,
        authenticated: bool,
        method: str,
        route: str,
        reason: str = "",
    ) -> None:
        """Persist allowlisted authentication evidence without request credentials."""

        normalized_method = str(method).upper()
        if normalized_method not in {"GET", "POST", "PUT", "DELETE"}:
            normalized_method = "OTHER"
        normalized_route = str(route)
        if normalized_route not in {
            "workflow_trigger",
            "run_cancel",
            "run_resume",
            "run_list",
            "run_detail",
            "unknown",
        }:
            normalized_route = "unknown"
        normalized_reason = str(reason)
        if normalized_reason not in {"missing_or_malformed", "invalid", "provider_unavailable"}:
            normalized_reason = "unspecified"
        event = {
            "type": "ingress_authenticated" if authenticated else "ingress_authentication_denied",
            "method": normalized_method,
            "route": normalized_route,
            "timestamp": _now(),
        }
        if not authenticated:
            event["reason"] = normalized_reason
        self._append_audit(event)

    def list_connectors(self) -> List[Dict[str, object]]:
        if self.connectors_path.exists():
            connectors = _load_json(self.connectors_path)
            if isinstance(connectors, list):
                return connectors
        if self.connector_runtime is not None:
            return self.connector_runtime.list_connectors()
        return default_connectors()

    def _workflow_record(self, workflow_id: str, version: str) -> WorkflowRecord:
        index = self._load_index()
        key = _record_key(workflow_id, version)
        if key not in index:
            raise ValueError(f"workflow version not found: {workflow_id}@{version}")
        return index[key]

    def _artifact_path(self, workflow_id: str, version: str) -> Path:
        return self.workflows_dir / _safe_name(workflow_id) / f"{_safe_name(version)}.json"

    def _load_index(self) -> Dict[str, WorkflowRecord]:
        return self.store.load_index()

    def _save_index(self, index: Dict[str, WorkflowRecord]) -> None:
        self.store.save_index(index)

    def _append_audit(self, event: AuditEvent) -> None:
        self.store.append_audit(event)

    def _append_runtime_audit_events(
        self,
        state: RunState,
        workflow_id: str,
        workflow_version: str,
        start_index: int = 0,
    ) -> None:
        events = state.get("events", [])
        if not isinstance(events, list):
            return
        run_id = str(state.get("run_id", ""))
        for event in events[start_index:]:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type", ""))
            if not _promote_runtime_event(event_type):
                continue
            audit_event = {
                "type": event_type,
                "run_id": run_id,
                "workflow_id": workflow_id,
                "workflow_version": workflow_version,
                "node_id": event.get("node_id", ""),
                "timestamp": event.get("timestamp", _now()),
            }
            for key in (
                "connector_id",
                "connector_kind",
                "connector_status",
                "attempt",
                "next_attempt",
                "max_attempts",
                "target",
                "fallback_target",
                "error",
                "input_mapping_status",
                "input_mapping_keys",
                "credential_status",
                "credential_handles",
                "connector_metadata",
            ):
                if key in event:
                    audit_event[key] = event[key]
            self._append_audit(audit_event)


def _workflow_identity(workflow: Workflow) -> tuple:
    workflow_meta = workflow.get("workflow")
    if not isinstance(workflow_meta, dict):
        raise ValueError("workflow.workflow must be an object")

    workflow_id = workflow_meta.get("id")
    version = workflow_meta.get("version")
    if not workflow_id:
        raise ValueError("workflow.workflow.id is required")
    if not version:
        raise ValueError("workflow.workflow.version is required")
    return str(workflow_id), str(version)


def _record_key(workflow_id: str, version: str) -> str:
    return f"{workflow_id}@{version}"


def _checksum(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_name(value: str) -> str:
    text = str(value)
    if text in {"", ".", ".."}:
        raise ValueError("workflow id and version must map to a safe path segment")
    if (
        len(text.encode("utf-8")) <= 120
        and all(char.isalnum() or char in {"-", "_", "."} for char in text)
    ):
        return text
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    return f"identity_{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _promote_runtime_event(event_type: str) -> bool:
    return event_type.startswith("connector_") or event_type in {
        "node_retrying",
        "node_recovered",
        "node_failed",
        "node_fallback",
    }
