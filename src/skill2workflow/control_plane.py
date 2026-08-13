"""Minimal local enterprise control plane for Workflow DSL artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath
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
WORKFLOW_DIFF_SCHEMA_VERSION = "skill2workflow-workflow-diff-0.1.0"
WORKFLOW_ARTIFACT_REPORT_SCHEMA_VERSION = (
    "skill2workflow-workflow-artifact-report-0.1.0"
)
RUN_AUDIT_REPORT_SCHEMA_VERSION = "skill2workflow-run-audit-report-0.1.0"
MAX_WORKFLOW_ARTIFACT_REPORT_ISSUES = 256
MAX_WORKFLOW_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_RUN_AUDIT_REPORT_RUNS = 256
MAX_RUN_AUDIT_REPORT_TYPES = 64


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
        index = self._load_index() if self.storage != "sqlite" else {}
        existing_record = index.get(_record_key(workflow_id, version))

        artifact_created = _ensure_immutable_artifact(
            artifact_path,
            published,
            checksum,
            workflow_id=workflow_id,
            version=version,
            root=self.state_dir,
        )
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
        try:
            if self.storage == "sqlite" and hasattr(self.store, "publish_workflow_record"):
                return self.store.publish_workflow_record(
                    record,
                    artifact_path=artifact_path,
                    audit_event={
                        "type": "workflow_published",
                        "workflow_id": workflow_id,
                        "workflow_version": version,
                        "checksum": checksum,
                        "timestamp": now,
                    },
                )
            if existing_record:
                return existing_record
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
        except BaseException:
            if artifact_created and self.storage == "sqlite" and hasattr(
                self.store, "cleanup_unregistered_artifact"
            ):
                try:
                    self.store.cleanup_unregistered_artifact(
                        _record_key(workflow_id, version),
                        artifact_path,
                        checksum,
                    )
                except Exception:
                    pass
            raise

    def deprecate_workflow(self, workflow_id: str, version: str) -> WorkflowRecord:
        """Mark a published workflow version as deprecated without mutating its artifact."""
        if self.storage == "sqlite" and hasattr(self.store, "deprecate_workflow_record"):
            deprecated_at = _now()
            return self.store.deprecate_workflow_record(
                workflow_id,
                version,
                deprecated_at=deprecated_at,
                audit_event={
                    "type": "workflow_deprecated",
                    "workflow_id": workflow_id,
                    "workflow_version": version,
                    "timestamp": deprecated_at,
                },
            )

        index = self._load_index()
        key = _record_key(workflow_id, version)
        if key not in index:
            raise ValueError(f"workflow version not found: {workflow_id}@{version}")

        record = dict(index[key])
        was_deprecated = record.get("status") == "deprecated"
        aliases_removed = bool(_record_aliases(record))
        if aliases_removed:
            record.pop("aliases", None)
        if not was_deprecated:
            record["status"] = "deprecated"
            record["deprecated_at"] = _now()
        if aliases_removed or not was_deprecated:
            index[key] = record
            self._save_index(index)
        if not was_deprecated:
            self._append_audit(
                {
                    "type": "workflow_deprecated",
                    "workflow_id": workflow_id,
                    "workflow_version": version,
                    "timestamp": record["deprecated_at"],
                }
            )
        return record

    def promote_workflow(
        self,
        workflow_id: str,
        version: str,
        alias: str = "production",
        expected_current_version: str = "",
    ) -> WorkflowRecord:
        """Point a stable alias at one version with an optional CAS guard."""

        normalized_alias = _normalize_workflow_alias(alias)
        index = self._load_index()
        target_key = _record_key(workflow_id, version)
        if target_key not in index:
            raise ValueError(f"workflow version not found: {workflow_id}@{version}")
        target = dict(index[target_key])
        if target.get("status") != "published":
            raise ValueError(f"workflow version is not published: {workflow_id}@{version}")
        # Verify before changing alias metadata so a corrupted release cannot
        # become reachable through a stable production target.
        self.get_workflow(workflow_id, version)
        if self.storage == "sqlite" and hasattr(self.store, "promote_workflow_alias"):
            return self.store.promote_workflow_alias(
                workflow_id,
                version,
                normalized_alias,
                expected_current_version=expected_current_version,
                audit_event={
                    "type": "workflow_promoted",
                    "workflow_id": workflow_id,
                    "workflow_version": version,
                    "alias": normalized_alias,
                    "timestamp": _now(),
                },
            )
        if expected_current_version:
            current_versions = _published_alias_versions(
                index, workflow_id, normalized_alias
            )
            if current_versions != [str(expected_current_version)]:
                raise ValueError(
                    f"workflow alias precondition failed: {workflow_id}@{normalized_alias}"
                )

        changed = False
        for key, existing in list(index.items()):
            if str(existing.get("workflow_id", "")) != str(workflow_id):
                continue
            existing_aliases = _record_aliases(existing)
            if normalized_alias not in existing_aliases:
                continue
            updated = dict(existing)
            existing_aliases.remove(normalized_alias)
            if existing_aliases:
                updated["aliases"] = existing_aliases
            else:
                updated.pop("aliases", None)
            index[key] = updated
            changed = True

        target = dict(index[target_key])
        target_aliases = _record_aliases(target)
        if normalized_alias not in target_aliases:
            target_aliases.append(normalized_alias)
            target["aliases"] = sorted(set(target_aliases))
            index[target_key] = target
            changed = True

        if changed:
            self._save_index(index)
            self._append_audit(
                {
                    "type": "workflow_promoted",
                    "workflow_id": workflow_id,
                    "workflow_version": version,
                    "alias": normalized_alias,
                    "timestamp": _now(),
                }
            )
        return target

    def list_workflows(self) -> List[WorkflowRecord]:
        records = list(self._load_index().values())
        return sorted(records, key=lambda record: (str(record["workflow_id"]), str(record["version"])))

    def inspect_workflow_artifacts(self) -> Dict[str, object]:
        """Return a bounded, value-free registry/artifact consistency report."""

        index = self._load_index()
        issues = []
        referenced = set()
        healthy = 0

        for key, record in sorted(index.items(), key=lambda item: str(item[0])):
            workflow_id = str(record.get("workflow_id", ""))
            version = str(record.get("version", ""))
            artifact_value = record.get("artifact")
            relative = _safe_artifact_reference(artifact_value)
            if relative is None:
                issues.append(
                    _artifact_issue(
                        "unsafe_reference", "<invalid>", workflow_id, version
                    )
                )
                continue
            referenced.add(relative)
            path = self.state_dir.joinpath(*PurePosixPath(relative).parts)
            issue_kind = _inspect_artifact_file(
                self.state_dir,
                path,
                str(record.get("checksum", "")),
            )
            if issue_kind:
                issues.append(_artifact_issue(issue_kind, relative, workflow_id, version))
            else:
                healthy += 1

        filesystem = set(_iter_workflow_artifacts(self.workflows_dir, self.state_dir))
        for relative in sorted(filesystem - referenced):
            issues.append(_artifact_issue("orphaned", relative))

        issues.sort(key=lambda issue: (str(issue["kind"]), str(issue["artifact"])))

        issue_counts = {
            kind: sum(1 for issue in issues if issue["kind"] == kind)
            for kind in (
                "missing",
                "unsafe_reference",
                "unsafe_artifact",
                "invalid_json",
                "oversized",
                "checksum_mismatch",
                "orphaned",
            )
        }
        issue_count = len(issues)
        truncated = issue_count > MAX_WORKFLOW_ARTIFACT_REPORT_ISSUES
        issues = issues[:MAX_WORKFLOW_ARTIFACT_REPORT_ISSUES]
        return {
            "schema_version": WORKFLOW_ARTIFACT_REPORT_SCHEMA_VERSION,
            "status": "clean" if issue_count == 0 else "attention",
            "summary": {
                "registry_records": len(index),
                "referenced_artifacts": len(referenced),
                "filesystem_artifacts": len(filesystem),
                "healthy": healthy,
                "issue_count": issue_count,
                **issue_counts,
                "truncated": truncated,
            },
            "issues": issues,
        }

    def inspect_run_audit(self, run_id: str = "") -> Dict[str, object]:
        """Compare durable run-state event counts with control-plane audit counts.

        This is intentionally diagnostic only. It never replays a connector or
        rewrites an audit chain; it exposes enough bounded metadata for an
        operator to identify a cross-database interruption safely.
        """

        summaries = self.executor.list_runs()
        if run_id:
            summaries = [
                summary
                for summary in summaries
                if str(summary.get("run_id", "")) == str(run_id)
            ]
            if not summaries:
                raise ValueError(f"run not found: {run_id}")
        total_runs = len(summaries)
        truncated = total_runs > MAX_RUN_AUDIT_REPORT_RUNS
        summaries = summaries[:MAX_RUN_AUDIT_REPORT_RUNS]
        run_ids = [str(summary.get("run_id", "")) for summary in summaries]
        audit_by_run = self.store.audit_event_type_counts(run_ids)

        reports = []
        attention_runs = 0
        missing_events = 0
        duplicate_events = 0
        unexpected_events = 0
        for summary in summaries:
            current_run_id = str(summary.get("run_id", ""))
            state = self.executor.get_run(current_run_id)
            expected = _expected_run_audit_counts(state)
            observed = Counter(audit_by_run.get(current_run_id, {}))
            missing = _counter_differences(expected, observed)
            duplicate = _counter_differences(observed, expected)
            missing_total = sum(missing.values())
            duplicate_total = sum(
                count for event_type, count in duplicate.items() if event_type in expected
            )
            unexpected = [
                {"type": event_type, "count": count}
                for event_type, count in sorted(duplicate.items())
                if event_type not in expected
            ]
            unexpected_total = sum(item["count"] for item in unexpected)
            duplicate = [
                {"type": event_type, "count": count}
                for event_type, count in sorted(duplicate.items())
                if event_type in expected
            ]
            missing = [
                {"type": event_type, "count": count}
                for event_type, count in sorted(missing.items())
            ]
            missing = missing[:MAX_RUN_AUDIT_REPORT_TYPES]
            duplicate = duplicate[:MAX_RUN_AUDIT_REPORT_TYPES]
            unexpected = unexpected[:MAX_RUN_AUDIT_REPORT_TYPES]
            has_attention = bool(missing or duplicate or unexpected)
            if has_attention:
                attention_runs += 1
            missing_events += missing_total
            duplicate_events += duplicate_total
            unexpected_events += unexpected_total
            reports.append(
                {
                    "run_id": current_run_id,
                    "workflow_id": str(summary.get("workflow_id", "")),
                    "workflow_version": str(summary.get("workflow_version", "")),
                    "run_status": str(summary.get("status", "")),
                    "status": "attention" if has_attention else "clean",
                    "expected_event_count": sum(expected.values()),
                    "observed_event_count": sum(observed.values()),
                    "missing": missing,
                    "duplicate": duplicate,
                    "unexpected": unexpected,
                }
            )

        return {
            "schema_version": RUN_AUDIT_REPORT_SCHEMA_VERSION,
            "status": "attention" if attention_runs or truncated else "clean",
            "summary": {
                "run_count": total_runs,
                "checked_runs": len(reports),
                "attention_runs": attention_runs,
                "missing_events": missing_events,
                "duplicate_events": duplicate_events,
                "unexpected_events": unexpected_events,
                "truncated": truncated,
            },
            "runs": reports,
        }

    def diff_workflow_versions(
        self, workflow_id: str, from_version: str, to_version: str
    ) -> Dict[str, object]:
        """Return a bounded structural diff without copying workflow values."""

        from_record = self._workflow_record(workflow_id, from_version)
        to_record = self._workflow_record(workflow_id, to_version)
        from_workflow = self.get_workflow(workflow_id, from_version)
        to_workflow = self.get_workflow(workflow_id, to_version)
        return {
            "schema_version": WORKFLOW_DIFF_SCHEMA_VERSION,
            "workflow_id": str(workflow_id),
            "from": _workflow_diff_record(from_record),
            "to": _workflow_diff_record(to_record),
            "changed": _workflow_diff_changed(from_workflow, to_workflow),
            "changes": _workflow_diff_changes(from_workflow, to_workflow),
        }

    def get_workflow(self, workflow_id: str, version: str) -> Workflow:
        record = self._workflow_record(workflow_id, version)
        artifact_path = self.state_dir / str(record.get("artifact", ""))
        try:
            workflow = _load_json(artifact_path)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(
                f"published workflow artifact unavailable: {workflow_id}@{version}"
            ) from error

        expected_checksum = str(record.get("checksum", ""))
        if not expected_checksum:
            raise ValueError(
                f"published workflow artifact checksum unavailable: {workflow_id}@{version}"
            )
        if _checksum(workflow) != expected_checksum:
            raise ValueError(
                f"published workflow artifact checksum mismatch: {workflow_id}@{version}"
            )
        return workflow

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
        terminal_event = {
            "type": f"run_{state['status']}",
            "run_id": state["run_id"],
            "workflow_id": workflow_id,
            "workflow_version": version,
            "timestamp": _now(),
        }
        if state.get("error_code"):
            terminal_event["error_code"] = str(state["error_code"])
        self._append_audit_batch(
            [started_event]
            + self._runtime_audit_events(state, workflow_id, version)
            + [terminal_event]
        )
        return state

    def trigger_workflow(self, request: Dict[str, object]) -> Dict[str, object]:
        """Trigger a published workflow through the local control-plane boundary."""

        trigger = normalize_trigger_request(request)
        workflow_id = str(trigger["workflow_id"])
        requested_version = str(trigger["version"])
        workflow_version = self.resolve_workflow_version(workflow_id, requested_version)
        trigger["idempotency_version"] = requested_version
        trigger["version"] = workflow_version
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
        idempotency_version = str(trigger.get("idempotency_version", workflow_version))
        claim = self.store.claim_trigger_idempotency(
            workflow_id,
            idempotency_version,
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
                idempotency_version,
                idempotency_key,
                request_fingerprint,
                response,
            )
            return response
        except BaseException:
            self.store.mark_trigger_idempotency_unresolved(
                workflow_id,
                idempotency_version,
                idempotency_key,
                request_fingerprint,
            )
            raise

    def resolve_workflow_version(self, workflow_id: str, version: str) -> str:
        """Resolve an exact version or a published stable alias to its version."""

        requested = str(version)
        index = self._load_index()
        if _record_key(workflow_id, requested) in index:
            return requested
        matches = [
            str(record.get("version", ""))
            for record in index.values()
            if str(record.get("workflow_id", "")) == str(workflow_id)
            and record.get("status") == "published"
            and requested in _record_aliases(record)
        ]
        if len(matches) > 1:
            raise ValueError(f"workflow alias is ambiguous: {workflow_id}@{requested}")
        return matches[0] if matches else requested

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
        resumed_timestamp = _last_run_event_timestamp(
            state, "human_gate_resumed"
        ) or _now()
        terminal_timestamp = _last_run_event_timestamp(
            state, f"run_{state.get('status', '')}"
        ) or _now()
        terminal_event = {
            "type": f"run_{state['status']}",
            "run_id": run_id,
            "workflow_id": workflow_id,
            "workflow_version": workflow_version,
            "timestamp": terminal_timestamp,
        }
        if state.get("error_code"):
            terminal_event["error_code"] = str(state["error_code"])
        self._append_audit_batch(
            [
                {
                    "type": "run_resumed",
                    "run_id": run_id,
                    "workflow_id": workflow_id,
                    "workflow_version": workflow_version,
                    "approved": approved,
                    "timestamp": resumed_timestamp,
                }
            ]
            + self._runtime_audit_events(
                state,
                workflow_id,
                workflow_version,
                start_index=previous_event_count,
            )
            + [terminal_event]
        )
        return state

    def cancel_published_run(self, run_id: str) -> RunState:
        """Request an idempotent cancellation without accepting arbitrary reason text."""

        current = self.executor.get_run(run_id)
        workflow_id = str(current.get("workflow_id", "workflow"))
        workflow_version = str(current.get("workflow_version", "0.1.0"))
        self._workflow_record(workflow_id, workflow_version)
        state, newly_requested = self.executor.request_cancel(run_id)
        if newly_requested:
            events = [
                {
                    "type": "run_cancel_requested",
                    "run_id": run_id,
                    "workflow_id": workflow_id,
                    "workflow_version": workflow_version,
                    "timestamp": _now(),
                }
            ]
            if state["status"] == "cancelled":
                events.append(
                    {
                        "type": "run_cancelled",
                        "run_id": run_id,
                        "workflow_id": workflow_id,
                        "workflow_version": workflow_version,
                        "timestamp": _now(),
                    }
                )
            self._append_audit_batch(events)
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
        reconciliation_events = []
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
            reconciliation_events.append(
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
        if reconciliation_events:
            self._append_audit_batch(reconciliation_events)
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
            "recurring_schedule_action",
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

    def record_recurring_schedule_change(
        self,
        schedule_id: str,
        enabled: bool,
        changed: bool,
    ) -> None:
        """Persist bounded evidence for an authenticated schedule mutation."""

        normalized_id = str(schedule_id)
        if (
            not normalized_id
            or len(normalized_id) > 128
            or any(not (char.isalnum() or char in {"-", "_", "."}) for char in normalized_id)
        ):
            raise ValueError("schedule_id must be a safe schedule identifier")
        if not isinstance(enabled, bool) or not isinstance(changed, bool):
            raise ValueError("schedule mutation state must be boolean")
        self._append_audit(
            {
                "type": "recurring_schedule_updated",
                "schedule_id": normalized_id,
                "enabled": enabled,
                "changed": changed,
                "timestamp": _now(),
            }
        )

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

    def _append_audit_batch(self, events: List[AuditEvent]) -> None:
        if not events:
            return
        self.store.append_audit_batch(events)

    def _append_runtime_audit_events(
        self,
        state: RunState,
        workflow_id: str,
        workflow_version: str,
        start_index: int = 0,
    ) -> None:
        self._append_audit_batch(
            self._runtime_audit_events(
                state,
                workflow_id,
                workflow_version,
                start_index=start_index,
            )
        )

    def _runtime_audit_events(
        self,
        state: RunState,
        workflow_id: str,
        workflow_version: str,
        start_index: int = 0,
    ) -> List[AuditEvent]:
        events = state.get("events", [])
        projected = []
        if not isinstance(events, list):
            return projected
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
            projected.append(audit_event)
        return projected


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


_WORKFLOW_ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
MAX_WORKFLOW_ALIAS_BYTES = 64


def _normalize_workflow_alias(alias: str) -> str:
    value = str(alias).strip()
    if (
        len(value.encode("utf-8")) > MAX_WORKFLOW_ALIAS_BYTES
        or not _WORKFLOW_ALIAS_PATTERN.fullmatch(value)
    ):
        raise ValueError(
            "workflow alias must start with a lowercase letter and contain only "
            "lowercase letters, numbers, ., _, or - (at most 64 UTF-8 bytes)"
        )
    return value


def _record_aliases(record: WorkflowRecord) -> List[str]:
    value = record.get("aliases", [])
    if not isinstance(value, list):
        return []
    aliases = []
    seen = set()
    for alias in value:
        text = str(alias)
        if text and text not in seen:
            aliases.append(text)
            seen.add(text)
    return aliases


def _published_alias_versions(
    index: Dict[str, WorkflowRecord], workflow_id: str, alias: str
) -> List[str]:
    versions = {
        str(record.get("version", ""))
        for record in index.values()
        if str(record.get("workflow_id", "")) == str(workflow_id)
        and record.get("status") == "published"
        and alias in _record_aliases(record)
    }
    return sorted(version for version in versions if version)


def _workflow_diff_record(record: WorkflowRecord) -> Dict[str, object]:
    return {
        "version": str(record.get("version", "")),
        "status": str(record.get("status", "")),
        "checksum": str(record.get("checksum", "")),
        "aliases": sorted(_record_aliases(record)),
    }


def _workflow_diff_changed(from_workflow: Workflow, to_workflow: Workflow) -> bool:
    return bool(_workflow_diff_changes(from_workflow, to_workflow)["sections"])


def _workflow_diff_changes(
    from_workflow: Workflow, to_workflow: Workflow
) -> Dict[str, object]:
    from_meta = from_workflow.get("workflow", {})
    to_meta = to_workflow.get("workflow", {})
    workflow_changed = _canonical_without(from_meta, {"id", "version", "status"}) != _canonical_without(
        to_meta, {"id", "version", "status"}
    )
    entry_changed = from_workflow.get("entry") != to_workflow.get("entry")
    input_schema_changed = _field_changed(from_workflow, to_workflow, "input_schema")
    policies_changed = _field_changed(from_workflow, to_workflow, "policies")
    other_changed = _canonical_without(
        from_workflow,
        {
            "schema_version",
            "workflow",
            "entry",
            "nodes",
            "edges",
            "input_schema",
            "policies",
        },
    ) != _canonical_without(
        to_workflow,
        {
            "schema_version",
            "workflow",
            "entry",
            "nodes",
            "edges",
            "input_schema",
            "policies",
        },
    )
    node_changes = _named_item_changes(from_workflow.get("nodes"), to_workflow.get("nodes"))
    edge_changes = _named_item_changes(from_workflow.get("edges"), to_workflow.get("edges"))
    sections = []
    for name, changed in (
        ("workflow", workflow_changed),
        ("entry", entry_changed),
        ("input_schema", input_schema_changed),
        ("policies", policies_changed),
        ("nodes", bool(node_changes["added"] or node_changes["removed"] or node_changes["changed"])),
        ("edges", bool(edge_changes["added"] or edge_changes["removed"] or edge_changes["changed"])),
        ("other", other_changed),
    ):
        if changed:
            sections.append(name)
    return {
        "sections": sections,
        "workflow_changed": workflow_changed,
        "entry_changed": entry_changed,
        "input_schema_changed": input_schema_changed,
        "policies_changed": policies_changed,
        "other_changed": other_changed,
        "nodes": node_changes,
        "edges": edge_changes,
    }


def _named_item_changes(from_value: object, to_value: object) -> Dict[str, List[str]]:
    from_items = _named_item_map(from_value)
    to_items = _named_item_map(to_value)
    added = sorted(set(to_items) - set(from_items))
    removed = sorted(set(from_items) - set(to_items))
    changed = sorted(
        key
        for key in set(from_items) & set(to_items)
        if _canonical_without(from_items[key], {"id"})
        != _canonical_without(to_items[key], {"id"})
    )
    return {"added": added, "removed": removed, "changed": changed}


def _named_item_map(value: object) -> Dict[str, Dict[str, object]]:
    if not isinstance(value, list):
        return {}
    result: Dict[str, Dict[str, object]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        result[str(item["id"])] = item
    return result


def _field_changed(from_value: Dict[str, object], to_value: Dict[str, object], key: str) -> bool:
    return _field_marker(from_value, key) != _field_marker(to_value, key)


def _field_marker(value: Dict[str, object], key: str) -> object:
    return {"present": key in value, "value": value.get(key)}


def _canonical_without(value: object, excluded: set) -> object:
    if not isinstance(value, dict):
        return value
    return {key: item for key, item in value.items() if key not in excluded}


def _checksum(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ensure_immutable_artifact(
    path: Path,
    workflow: Workflow,
    checksum: str,
    *,
    workflow_id: str,
    version: str,
    root: Path,
) -> bool:
    """Create one artifact without allowing a concurrent writer to replace it."""

    payload = json.dumps(workflow, ensure_ascii=False, indent=2).encode("utf-8")

    def verify_existing() -> None:
        if _path_has_symlink_component(root, path):
            raise ValueError(
                f"published workflow artifact unavailable: {workflow_id}@{version}"
            )
        try:
            existing = _load_json(path)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(
                f"published workflow artifact unavailable: {workflow_id}@{version}"
            ) from error
        if _checksum(existing) != checksum:
            raise ValueError(
                f"published workflow version is immutable: {workflow_id}@{version}"
            )

    if _path_has_symlink_component(root, path):
        raise ValueError(
            f"published workflow artifact unavailable: {workflow_id}@{version}"
        )
    if path.exists():
        verify_existing()
        return False

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent)
    )
    descriptor_open = True
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor_open = False
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, str(path))
            return True
        except FileExistsError:
            verify_existing()
        except OSError as error:
            raise ValueError(
                f"published workflow artifact unavailable: {workflow_id}@{version}"
            ) from error
    finally:
        if descriptor_open:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        except OSError:
            pass


def _safe_artifact_reference(value: object):
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or relative.suffix != ".json"
        or not relative.parts
        or relative.parts[0] != "workflows"
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        return None
    normalized = relative.as_posix()
    if normalized == "workflows/index.json":
        return None
    return normalized


def _inspect_artifact_file(state_dir: Path, path: Path, checksum: str):
    if _path_has_symlink_component(state_dir, path):
        return "unsafe_artifact"
    try:
        details = path.lstat()
    except FileNotFoundError:
        return "missing"
    except (OSError, ValueError):
        return "unsafe_artifact"
    if not stat.S_ISREG(details.st_mode):
        return "unsafe_artifact"
    if details.st_size > MAX_WORKFLOW_ARTIFACT_BYTES:
        return "oversized"
    try:
        workflow = _load_json(path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return "invalid_json"
    if not checksum or _checksum(workflow) != checksum:
        return "checksum_mismatch"
    return None


def _path_has_symlink_component(root: Path, path: Path) -> bool:
    try:
        relative = Path(path).relative_to(Path(root))
    except ValueError:
        return True
    current = Path(root)
    try:
        if stat.S_ISLNK(current.lstat().st_mode):
            return True
    except OSError:
        return True
    for part in relative.parts:
        current = current / part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                return True
        except FileNotFoundError:
            return False
        except OSError:
            return True
    return False


def _iter_workflow_artifacts(root: Path, state_dir: Path):
    if not root.exists() or root.is_symlink():
        return []
    paths = []
    for base, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        directories[:] = [
            name for name in directories
            if not (Path(base) / name).is_symlink()
        ]
        for name in filenames:
            if not name.endswith(".json"):
                continue
            path = Path(base) / name
            try:
                relative = path.relative_to(state_dir).as_posix()
            except ValueError:
                continue
            if relative != "workflows/index.json":
                paths.append(relative)
    return paths


def _artifact_issue(kind: str, artifact: object, workflow_id: str = "", version: str = ""):
    issue = {"kind": str(kind), "artifact": str(artifact or "")}
    if workflow_id or version:
        issue["workflow_id"] = workflow_id
        issue["version"] = version
    return issue


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


def _expected_run_audit_counts(state: RunState) -> Counter:
    """Derive the bounded audit projection expected from one durable run state."""

    expected = Counter({"run_started": 1})
    events = state.get("events", [])
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type", ""))
            if _promote_runtime_event(event_type):
                expected[event_type] += 1
            elif event_type == "human_gate_resumed":
                expected["run_resumed"] += 1
            elif event_type == "human_gate_waiting":
                expected["run_waiting"] += 1
            elif event_type in {
                "run_cancel_requested",
                "run_cancelled",
                "run_interrupted",
            }:
                expected[event_type] += 1

    status = str(state.get("status", ""))
    if status == "cancel_requested":
        expected["run_cancel_requested"] = max(
            1, expected.get("run_cancel_requested", 0)
        )
    elif status in {"waiting", "completed", "failed", "interrupted"}:
        expected[f"run_{status}"] += 1
    elif status == "cancelled" and expected.get("run_cancelled", 0) == 0:
        expected["run_cancelled"] = 1
    return expected


def _last_run_event_timestamp(state: RunState, event_type: str) -> str:
    events = state.get("events", [])
    if not isinstance(events, list):
        return ""
    for event in reversed(events):
        if not isinstance(event, dict) or str(event.get("type", "")) != event_type:
            continue
        timestamp = event.get("timestamp", "")
        if timestamp:
            return str(timestamp)
    return ""


def _counter_differences(left: Counter, right: Counter) -> Dict[str, int]:
    """Return positive count differences without exposing event payloads."""

    return {
        event_type: count
        for event_type, count in (left - right).items()
        if count > 0
    }
