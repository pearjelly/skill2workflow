"""Deterministic local Lark/Feishu task connector dry-run smoke helper."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict

from .compiler import validate_workflow
from .connectors import ConnectorRuntime
from .control_plane import LocalControlPlane
from .credentials import StaticCredentialProvider
from .dashboard import build_control_snapshot
from .external_connectors import load_external_connector


DEFAULT_WORK_DIR = Path(tempfile.gettempdir()) / "skill2workflow-lark-task-connector"
DEFAULT_UI_URL = "http://localhost:4173/web/control.html"
LOCAL_SECRET = "local-lark-secret"


def run_lark_task_connector_smoke(
    repo_root: Path,
    work_dir: Path = DEFAULT_WORK_DIR,
    reset: bool = True,
) -> Dict[str, object]:
    """Run a published workflow through the explicitly loaded Lark task connector fixture."""
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)

    artifacts_dir = work_dir / "artifacts"
    state_dir = work_dir / "state"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    fixture_path = repo_root / "examples" / "connectors" / "lark_task_connector.py"
    external_connector = load_external_connector(fixture_path)
    default_connector_ids = [manifest["id"] for manifest in ConnectorRuntime().list_connectors()]
    runtime = ConnectorRuntime([external_connector])
    connector_ids = [manifest["id"] for manifest in runtime.list_connectors()]

    workflow = _lark_task_connector_workflow()
    errors = validate_workflow(workflow)
    if errors:
        raise ValueError("; ".join(errors))

    control = LocalControlPlane(
        state_dir,
        credential_provider=StaticCredentialProvider({"lark_bot_access_token": LOCAL_SECRET}),
        connector_runtime=runtime,
    )
    control.publish_workflow(workflow)
    trigger_response = control.trigger_workflow(
        {
            "workflow_id": "workflow_lark_task_connector_smoke",
            "version": "0.1.0",
            "source": "local-lark-task-connector-smoke",
            "idempotency_key": "lark-task-001",
            "input": {
                "title": "Renewal risk follow-up",
                "description": "Customer ACME needs executive review",
                "assignee_open_id": "ou_lark_task_owner",
                "due_at": "2026-07-09T09:00:00Z",
            },
        }
    )
    run_id = str(trigger_response["run_id"])
    run_state = control.get_run(run_id)
    audit_events = control.list_audit_events(run_id=run_id)
    completed_events = [event for event in audit_events if event.get("type") == "connector_completed"]
    connector_summary = _connector_summary(completed_events[0] if completed_events else {})
    snapshot = build_control_snapshot(state_dir, connector_runtime=runtime)

    workflow_path = artifacts_dir / "workflow.json"
    run_path = artifacts_dir / "run.json"
    audit_path = artifacts_dir / "audit.json"
    snapshot_path = artifacts_dir / "control-plane-snapshot.json"
    connectors_path = artifacts_dir / "connectors.json"
    trigger_path = artifacts_dir / "trigger-response.json"

    _write_json(workflow_path, workflow)
    _write_json(run_path, run_state)
    _write_json(audit_path, audit_events)
    _write_json(snapshot_path, snapshot)
    _write_json(connectors_path, runtime.list_connectors())
    _write_json(trigger_path, trigger_response)

    return {
        "ok": True,
        "work_dir": str(work_dir),
        "state_dir": str(state_dir),
        "workflow_id": "workflow_lark_task_connector_smoke",
        "workflow_version": "0.1.0",
        "run_id": run_id,
        "run_status": run_state.get("status", ""),
        "default_connector_ids": default_connector_ids,
        "connector_ids": connector_ids,
        "connector_summary": connector_summary,
        "snapshot_summary": snapshot.get("summary", {}),
        "artifacts": {
            "workflow": str(workflow_path),
            "run": str(run_path),
            "audit": str(audit_path),
            "snapshot": str(snapshot_path),
            "connectors": str(connectors_path),
            "trigger_response": str(trigger_path),
        },
        "commands": {
            "run_lark_task_connector_smoke": f"python3 scripts/lark_task_connector_smoke.py --work-dir {work_dir}",
            "serve_ui": "python3 -m http.server 4173",
            "ui_url": DEFAULT_UI_URL,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="lark_task_connector_smoke",
        description="Generate and run the local Lark/Feishu task connector dry-run smoke.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true", help="Keep existing Lark task connector smoke artifacts.")
    args = parser.parse_args(argv)

    result = run_lark_task_connector_smoke(args.repo_root, args.work_dir, reset=not args.no_reset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _lark_task_connector_workflow() -> Dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_lark_task_connector_smoke",
            "name": "lark-task-connector-smoke",
            "description": "Local dry-run smoke for an explicitly loaded Lark/Feishu task connector fixture.",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "create_lark_task"},
            {
                "id": "create_lark_task",
                "type": "tool_call",
                "title": "Create Lark task dry-run",
                "description": "Validate a Lark/Feishu task create request without calling the live Lark API.",
                "connector": {
                    "id": "lark_task",
                    "kind": "lark_task",
                    "operation": "create_task",
                    "mode": "dry_run",
                    "request": {
                        "body": {"source": "lark-task-connector-smoke"},
                        "input_mapping": [
                            {"from": "/input/title", "to": "/body/title", "required": True},
                            {"from": "/input/description", "to": "/body/description", "required": False},
                            {"from": "/input/assignee_open_id", "to": "/body/assignee_open_id", "required": False},
                            {"from": "/input/due_at", "to": "/body/due_at", "required": False},
                        ],
                    },
                    "credentials": [
                        {
                            "target": "header",
                            "name": "Authorization",
                            "handle": "lark_bot_access_token",
                            "prefix": "Bearer ",
                        }
                    ],
                },
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_create_task", "from": "start", "to": "create_lark_task", "label": "next"},
            {"id": "edge_create_task_end", "from": "create_lark_task", "to": "end", "label": "next"},
            {"id": "edge_create_task_failure", "from": "create_lark_task", "to": "failure", "label": "failure"},
        ],
        "state_schema": {},
        "guards": [],
        "checkpoints": [],
        "policies": {"default_retry": {"max_attempts": 0}, "default_timeout_ms": 300000},
    }


def _connector_summary(event: Dict[str, object]) -> Dict[str, object]:
    metadata = event.get("connector_metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "connector_id": str(event.get("connector_id", "")),
        "connector_status": str(event.get("connector_status", "")),
        "credential_status": str(event.get("credential_status", "")),
        "credential_handles": [str(handle) for handle in event.get("credential_handles", [])]
        if isinstance(event.get("credential_handles"), list)
        else [],
        "input_mapping_status": str(event.get("input_mapping_status", "")),
        "input_mapping_keys": [str(key) for key in event.get("input_mapping_keys", [])]
        if isinstance(event.get("input_mapping_keys"), list)
        else [],
        "operation": str(metadata.get("operation", "")),
        "mode": str(metadata.get("mode", "")),
        "task_title_present": bool(metadata.get("task_title_present")),
        "task_description_present": bool(metadata.get("task_description_present")),
        "assignee_present": bool(metadata.get("assignee_present")),
        "due_at_present": bool(metadata.get("due_at_present")),
    }


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("Lark task connector smoke work_dir must be outside the repository when reset is enabled")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("Lark task connector smoke work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
