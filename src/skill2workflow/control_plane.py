"""Minimal local enterprise control plane for Workflow DSL artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .compiler import validate_workflow
from .executor import LocalExecutor, RunState


Workflow = Dict[str, object]
WorkflowRecord = Dict[str, object]
AuditEvent = Dict[str, object]


DEFAULT_CONNECTORS: List[Dict[str, object]] = [
    {
        "id": "manual",
        "name": "Manual Human Gate",
        "kind": "human_gate",
        "status": "placeholder",
        "description": "Placeholder for human approval and manual review integrations.",
    },
    {
        "id": "http",
        "name": "HTTP Tool Call",
        "kind": "tool_call",
        "status": "placeholder",
        "description": "Placeholder for generic HTTP connector bindings.",
    },
    {
        "id": "lark",
        "name": "Lark / Feishu",
        "kind": "enterprise_surface",
        "status": "placeholder",
        "description": "Placeholder for enterprise IM, approval, task, and document connectors.",
    },
]


class LocalControlPlane:
    """Manage local workflow versions, published runs, and audit events."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.workflows_dir = self.state_dir / "workflows"
        self.index_path = self.workflows_dir / "index.json"
        self.audit_path = self.state_dir / "audit.log.jsonl"
        self.connectors_path = self.state_dir / "connectors.json"
        self.executor = LocalExecutor(self.state_dir)
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

    def run_published_workflow(self, workflow_id: str, version: str) -> RunState:
        record = self._workflow_record(workflow_id, version)
        if record.get("status") != "published":
            raise ValueError(f"workflow version is not published: {workflow_id}@{version}")

        started_at = _now()
        state = self.executor.run(self.get_workflow(workflow_id, version))
        self._append_audit(
            {
                "type": "run_started",
                "run_id": state["run_id"],
                "workflow_id": workflow_id,
                "workflow_version": version,
                "timestamp": started_at,
            }
        )
        self._append_audit(
            {
                "type": f"run_{state['status']}",
                "run_id": state["run_id"],
                "workflow_id": workflow_id,
                "workflow_version": version,
                "timestamp": _now(),
            }
        )
        return state

    def list_runs(self) -> List[RunState]:
        return self.executor.list_runs()

    def get_run(self, run_id: str) -> RunState:
        return self.executor.get_run(run_id)

    def list_audit_events(self) -> List[AuditEvent]:
        if not self.audit_path.exists():
            return []
        events = []
        for line in self.audit_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events

    def list_connectors(self) -> List[Dict[str, object]]:
        if self.connectors_path.exists():
            connectors = _load_json(self.connectors_path)
            if isinstance(connectors, list):
                return connectors
        return copy.deepcopy(DEFAULT_CONNECTORS)

    def _workflow_record(self, workflow_id: str, version: str) -> WorkflowRecord:
        index = self._load_index()
        key = _record_key(workflow_id, version)
        if key not in index:
            raise ValueError(f"workflow version not found: {workflow_id}@{version}")
        return index[key]

    def _artifact_path(self, workflow_id: str, version: str) -> Path:
        return self.workflows_dir / _safe_name(workflow_id) / f"{_safe_name(version)}.json"

    def _load_index(self) -> Dict[str, WorkflowRecord]:
        if not self.index_path.exists():
            return {}
        index = _load_json(self.index_path)
        if not isinstance(index, dict):
            raise ValueError("workflow index must be an object")
        return index

    def _save_index(self, index: Dict[str, WorkflowRecord]) -> None:
        self.index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_audit(self, event: AuditEvent) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


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
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
