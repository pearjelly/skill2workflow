"""Deterministic local sales renewal pilot using the Lark/Feishu task dry-run connector."""

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
from .pilot import DEFAULT_UI_URL
from .visualizer import workflow_to_litegraph
from .webhooks import handle_webhook_request


DEFAULT_WORK_DIR = Path(tempfile.gettempdir()) / "skill2workflow-lark-task-pilot"
LOCAL_SECRET = "local-lark-secret"


def run_lark_task_pilot(
    repo_root: Path,
    work_dir: Path = DEFAULT_WORK_DIR,
    reset: bool = True,
) -> Dict[str, object]:
    """Run the sales renewal risk pilot through a manual gate and Lark task dry-run."""
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)

    artifacts_dir = work_dir / "artifacts"
    state_dir = work_dir / "state"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    external_connector = load_external_connector(repo_root / "examples" / "connectors" / "lark_task_connector.py")
    default_connector_ids = [manifest["id"] for manifest in ConnectorRuntime().list_connectors()]
    runtime = ConnectorRuntime([external_connector])
    connector_ids = [manifest["id"] for manifest in runtime.list_connectors()]

    workflow = _lark_task_pilot_workflow()
    errors = validate_workflow(workflow)
    if errors:
        raise ValueError("; ".join(errors))

    control = LocalControlPlane(
        state_dir,
        credential_provider=StaticCredentialProvider({"lark_bot_access_token": LOCAL_SECRET}),
        connector_runtime=runtime,
    )
    control.publish_workflow(workflow)
    trigger_payload = {
        "source": "local-webhook",
        "idempotency_key": "sales-renewal-risk-001",
        "input": _pilot_trigger_input(),
    }
    trigger_response = handle_webhook_request(
        control,
        "POST",
        "/webhooks/workflow_lark_task_pilot/0.1.0",
        json.dumps(trigger_payload).encode("utf-8"),
    )
    run_id = str(trigger_response["run_id"])
    waiting_state = control.get_run(run_id)
    gate_summary = _gate_summary(waiting_state, approved=False)
    run_state = waiting_state
    if waiting_state.get("status") == "waiting":
        run_state = control.resume_published_run(run_id, approved=True)
        gate_summary = _gate_summary(run_state, approved=True)

    audit_events = control.list_audit_events(run_id=run_id)
    completed_events = [event for event in audit_events if event.get("type") == "connector_completed"]
    connector_summary = _connector_summary(completed_events[0] if completed_events else {})
    snapshot = build_control_snapshot(state_dir, connector_runtime=runtime)
    litegraph_overlay = workflow_to_litegraph(workflow, run_state=run_state, audit_events=audit_events)

    workflow_path = artifacts_dir / "workflow.json"
    trigger_path = artifacts_dir / "trigger-response.json"
    run_path = artifacts_dir / "run.json"
    audit_path = artifacts_dir / "audit.json"
    snapshot_path = artifacts_dir / "control-plane-snapshot.json"
    overlay_path = artifacts_dir / "workflow.overlay.litegraph.json"
    connectors_path = artifacts_dir / "connectors.json"

    _write_json(workflow_path, workflow)
    _write_json(trigger_path, trigger_response)
    _write_json(run_path, run_state)
    _write_json(audit_path, audit_events)
    _write_json(snapshot_path, snapshot)
    _write_json(overlay_path, litegraph_overlay)
    _write_json(connectors_path, runtime.list_connectors())

    return {
        "ok": True,
        "work_dir": str(work_dir),
        "state_dir": str(state_dir),
        "scenario": {
            "id": "sales_renewal_risk_followup",
            "control": "manual_gate_before_lark_task",
        },
        "workflow_id": "workflow_lark_task_pilot",
        "workflow_version": "0.1.0",
        "run_id": run_id,
        "run_status": run_state.get("status", ""),
        "default_connector_ids": default_connector_ids,
        "connector_ids": connector_ids,
        "trigger_response": trigger_response,
        "trigger_summary": _trigger_summary(trigger_payload),
        "gate_summary": gate_summary,
        "connector_summary": connector_summary,
        "snapshot_summary": snapshot.get("summary", {}),
        "artifacts": {
            "workflow": str(workflow_path),
            "trigger_response": str(trigger_path),
            "run": str(run_path),
            "audit": str(audit_path),
            "snapshot": str(snapshot_path),
            "litegraph_overlay": str(overlay_path),
            "connectors": str(connectors_path),
        },
        "commands": {
            "run_lark_task_pilot": f"python3 scripts/lark_task_pilot_smoke.py --work-dir {work_dir}",
            "serve_ui": "python3 -m http.server 4173",
            "ui_url": DEFAULT_UI_URL,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="lark_task_pilot_smoke",
        description="Generate and run the local sales renewal Lark/Feishu task pilot.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true", help="Keep existing Lark task pilot artifacts.")
    args = parser.parse_args(argv)

    result = run_lark_task_pilot(args.repo_root, args.work_dir, reset=not args.no_reset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _pilot_trigger_input() -> Dict[str, object]:
    return {
        "account_id": "acct_123",
        "account_name": "ACME Global",
        "renewal_risk": "High renewal risk because executive sponsor changed",
        "owner_open_id": "ou_lark_task_owner",
        "due_at": "2026-08-15T09:00:00Z",
    }


def _lark_task_pilot_workflow() -> Dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_lark_task_pilot",
            "name": "lark-task-sales-renewal-pilot",
            "description": "Local sales renewal risk pilot using the Lark/Feishu task dry-run connector.",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "title": "Receive renewal risk",
                "description": "Receive durable sales renewal risk trigger input.",
                "on_success": "review_renewal_risk",
            },
            {
                "id": "review_renewal_risk",
                "type": "human_gate",
                "title": "Review renewal risk",
                "description": "Manual control point before creating an owner follow-up task.",
                "action": {
                    "kind": "human_approval",
                    "prompt": "Approve the renewal risk follow-up task for the account owner.",
                },
                "connector": {"id": "manual", "kind": "manual"},
                "on_success": "create_lark_task",
                "on_failure": "failure",
            },
            {
                "id": "create_lark_task",
                "type": "tool_call",
                "title": "Create owner follow-up task",
                "description": "Validate a Lark/Feishu owner follow-up task request without calling the live API.",
                "action": {
                    "kind": "tool_call",
                    "instruction": "Create a dry-run Lark/Feishu task for the account owner.",
                },
                "retry": {"max_attempts": 0},
                "connector": {
                    "id": "lark_task",
                    "kind": "lark_task",
                    "operation": "create_task",
                    "mode": "dry_run",
                    "request": {
                        "body": {
                            "source": "skill2workflow-lark-task-pilot",
                            "scenario": "sales_renewal_risk_followup",
                        },
                        "input_mapping": [
                            {"from": "/input/account_name", "to": "/body/title", "required": True},
                            {"from": "/input/renewal_risk", "to": "/body/description", "required": True},
                            {"from": "/input/owner_open_id", "to": "/body/assignee_open_id", "required": True},
                            {"from": "/input/due_at", "to": "/body/due_at", "required": True},
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
            {"id": "end", "type": "end", "title": "Renewal follow-up captured"},
        ],
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review_renewal_risk", "label": "next"},
            {"id": "edge_review_task", "from": "review_renewal_risk", "to": "create_lark_task", "label": "next"},
            {"id": "edge_review_failure", "from": "review_renewal_risk", "to": "failure", "label": "failure"},
            {"id": "edge_task_end", "from": "create_lark_task", "to": "end", "label": "next"},
            {"id": "edge_task_failure", "from": "create_lark_task", "to": "failure", "label": "failure"},
        ],
        "state_schema": {},
        "guards": [],
        "checkpoints": [],
        "policies": {"default_retry": {"max_attempts": 0}, "default_timeout_ms": 300000},
    }


def _trigger_summary(trigger_payload: Dict[str, object]) -> Dict[str, object]:
    trigger_input = trigger_payload.get("input", {})
    input_keys = sorted(str(key) for key in trigger_input.keys()) if isinstance(trigger_input, dict) else []
    return {
        "source": str(trigger_payload.get("source", "")),
        "idempotency_key": str(trigger_payload.get("idempotency_key", "")),
        "input_keys": input_keys,
    }


def _gate_summary(run_state: Dict[str, object], approved: bool) -> Dict[str, object]:
    node_results = run_state.get("node_results", {})
    result = node_results.get("review_renewal_risk", {}) if isinstance(node_results, dict) else {}
    return {
        "node_id": "review_renewal_risk",
        "resumed": bool(result),
        "approved": bool(result.get("approved")) if isinstance(result, dict) else approved,
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
        raise ValueError("Lark task pilot work_dir must be outside the repository when reset is enabled")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("Lark task pilot work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
