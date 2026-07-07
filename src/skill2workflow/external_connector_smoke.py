"""Deterministic local external connector prototype smoke helper."""

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


DEFAULT_WORK_DIR = Path(tempfile.gettempdir()) / "skill2workflow-external-connector"
DEFAULT_UI_URL = "http://localhost:4173/web/control.html"
LOCAL_SECRET = "local-secret-value"


def run_external_connector_smoke(
    repo_root: Path,
    work_dir: Path = DEFAULT_WORK_DIR,
    reset: bool = True,
) -> Dict[str, object]:
    """Run a published workflow through an explicitly loaded external connector fixture."""
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)

    artifacts_dir = work_dir / "artifacts"
    state_dir = work_dir / "state"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    fixture_path = repo_root / "examples" / "connectors" / "local_echo_connector.py"
    external_connector = load_external_connector(fixture_path)
    default_connector_ids = [manifest["id"] for manifest in ConnectorRuntime().list_connectors()]
    runtime = ConnectorRuntime([external_connector])
    connector_ids = [manifest["id"] for manifest in runtime.list_connectors()]

    workflow = _external_connector_workflow()
    errors = validate_workflow(workflow)
    if errors:
        raise ValueError("; ".join(errors))

    control = LocalControlPlane(
        state_dir,
        credential_provider=StaticCredentialProvider({"demo_api_token": LOCAL_SECRET}),
        connector_runtime=runtime,
    )
    control.publish_workflow(workflow)
    trigger_response = control.trigger_workflow(
        {
            "workflow_id": "workflow_external_connector_smoke",
            "version": "0.1.0",
            "source": "local-external-connector-smoke",
            "idempotency_key": "local-echo-001",
            "input": {
                "customer_id": "customer_123",
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
        "workflow_id": "workflow_external_connector_smoke",
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
            "run_external_connector_smoke": f"python3 scripts/external_connector_smoke.py --work-dir {work_dir}",
            "serve_ui": "python3 -m http.server 4173",
            "ui_url": DEFAULT_UI_URL,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="external_connector_smoke",
        description="Generate and run the local external connector prototype smoke.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true", help="Keep existing external connector smoke artifacts.")
    args = parser.parse_args(argv)

    result = run_external_connector_smoke(args.repo_root, args.work_dir, reset=not args.no_reset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _external_connector_workflow() -> Dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_external_connector_smoke",
            "name": "external-connector-smoke",
            "description": "Local smoke for an explicitly loaded external connector fixture.",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "call_echo"},
            {
                "id": "call_echo",
                "type": "tool_call",
                "title": "Call local echo connector",
                "description": "Invoke the explicitly loaded local echo external connector fixture.",
                "connector": {
                    "id": "local_echo",
                    "kind": "local_echo",
                    "request": {
                        "body": {"source": "external-connector-smoke"},
                        "input_mapping": [
                            {"from": "/input/customer_id", "to": "/body/customer_id", "required": True}
                        ],
                    },
                    "credentials": [
                        {
                            "target": "header",
                            "name": "Authorization",
                            "handle": "demo_api_token",
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
            {"id": "edge_start_call", "from": "start", "to": "call_echo", "label": "next"},
            {"id": "edge_call_end", "from": "call_echo", "to": "end", "label": "next"},
            {"id": "edge_call_failure", "from": "call_echo", "to": "failure", "label": "failure"},
        ],
        "state_schema": {},
        "guards": [],
        "checkpoints": [],
        "policies": {"default_retry": {"max_attempts": 0}, "default_timeout_ms": 300000},
    }


def _connector_summary(event: Dict[str, object]) -> Dict[str, object]:
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
    }


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("external connector smoke work_dir must be outside the repository when reset is enabled")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("external connector smoke work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
