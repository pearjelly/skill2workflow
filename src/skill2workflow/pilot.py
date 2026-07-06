"""Runnable local pilot playbook smoke helper."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict
from urllib.parse import urlsplit

from .compiler import validate_workflow
from .control_plane import LocalControlPlane
from .credentials import StaticCredentialProvider
from .dashboard import build_control_snapshot
from .visualizer import workflow_to_litegraph
from .webhooks import handle_webhook_request


DEFAULT_WORK_DIR = Path(tempfile.gettempdir()) / "skill2workflow-pilot"
DEFAULT_UI_URL = "http://localhost:4173/web/control.html"
PILOT_SECRET = "local-secret-value"


def run_pilot_playbook(repo_root: Path, work_dir: Path = DEFAULT_WORK_DIR, reset: bool = True) -> Dict[str, object]:
    """Generate and run a deterministic local pilot scenario."""
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)

    artifacts_dir = work_dir / "artifacts"
    state_dir = work_dir / "state"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    workflow_path = artifacts_dir / "workflow.json"
    receiver = _PilotConnectorReceiver(port=_existing_connector_port(workflow_path) if not reset else 0)
    receiver.start()
    try:
        workflow = _pilot_workflow(receiver.url)
        errors = validate_workflow(workflow)
        if errors:
            raise ValueError("; ".join(errors))

        credential_provider = StaticCredentialProvider({"pilot_api_token": PILOT_SECRET})
        control = LocalControlPlane(state_dir, credential_provider=credential_provider)
        control.publish_workflow(workflow)

        trigger_payload = {
            "source": "local-webhook",
            "idempotency_key": "ticket-123-escalation",
            "input": {
                "customer_id": "customer_123",
                "priority": "high",
                "ticket_id": "ticket_123",
            },
        }
        trigger_response = handle_webhook_request(
            control,
            "POST",
            "/webhooks/workflow_customer_support_pilot/0.1.0",
            json.dumps(trigger_payload).encode("utf-8"),
        )
        run_id = str(trigger_response["run_id"])
        run_state = control.get_run(run_id)
        if run_state.get("status") == "waiting":
            run_state = control.resume_published_run(run_id, approved=True)

        snapshot = build_control_snapshot(state_dir)
        audit_events = control.list_audit_events(run_id=run_id)
        litegraph_overlay = workflow_to_litegraph(workflow, run_state=run_state, audit_events=audit_events)

        trigger_path = artifacts_dir / "trigger-response.json"
        run_path = artifacts_dir / "run.json"
        snapshot_path = artifacts_dir / "control-plane-snapshot.json"
        overlay_path = artifacts_dir / "workflow.overlay.litegraph.json"

        _write_json(workflow_path, workflow)
        _write_json(trigger_path, trigger_response)
        _write_json(run_path, run_state)
        _write_json(snapshot_path, snapshot)
        _write_json(overlay_path, litegraph_overlay)

        connector_request = receiver.last_request()
        return {
            "ok": True,
            "work_dir": str(work_dir),
            "state_dir": str(state_dir),
            "workflow_id": "workflow_customer_support_pilot",
            "workflow_version": "0.1.0",
            "run_id": run_id,
            "run_status": run_state.get("status", ""),
            "trigger_response": trigger_response,
            "snapshot_summary": snapshot.get("summary", {}),
            "connector_request": _connector_request_summary(connector_request),
            "artifacts": {
                "workflow": str(workflow_path),
                "trigger_response": str(trigger_path),
                "run": str(run_path),
                "snapshot": str(snapshot_path),
                "litegraph_overlay": str(overlay_path),
            },
            "commands": {
                "run_pilot": f"python3 scripts/pilot_playbook_smoke.py --work-dir {work_dir}",
                "serve_ui": "python3 -m http.server 4173",
                "ui_url": DEFAULT_UI_URL,
            },
        }
    finally:
        receiver.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="pilot_playbook_smoke",
        description="Generate and run the local pilot playbook scenario.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true", help="Keep existing pilot work directory contents.")
    args = parser.parse_args(argv)

    result = run_pilot_playbook(args.repo_root, args.work_dir, reset=not args.no_reset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _pilot_workflow(connector_url: str) -> Dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_customer_support_pilot",
            "name": "customer-support-pilot",
            "description": "Local pilot scenario for customer support escalation.",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "title": "Receive escalation",
                "description": "Start the local customer support pilot workflow.",
                "on_success": "intake_review",
            },
            {
                "id": "intake_review",
                "type": "human_gate",
                "title": "Review escalation",
                "description": "Manual review before notifying the local support API.",
                "action": {
                    "kind": "human_approval",
                    "prompt": "Approve the support escalation for the local pilot.",
                },
                "connector": {"id": "manual", "kind": "manual"},
                "on_success": "call_support_api",
                "on_failure": "failure",
            },
            {
                "id": "call_support_api",
                "type": "tool_call",
                "title": "Notify support API",
                "description": "Call the local HTTP receiver with a credential handle.",
                "action": {
                    "kind": "tool_call",
                    "instruction": "Notify the local support API that the escalation was approved.",
                },
                "retry": {"max_attempts": 0},
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {
                        "method": "POST",
                        "url": connector_url,
                        "headers": {"Content-Type": "application/json"},
                        "body": {
                            "source": "skill2workflow-pilot",
                            "event": "support_escalation_approved",
                        },
                        "timeout_ms": 2000,
                    },
                    "credentials": [
                        {
                            "target": "header",
                            "name": "Authorization",
                            "handle": "pilot_api_token",
                            "prefix": "Bearer ",
                        }
                    ],
                },
                "on_success": "end",
                "on_failure": "failure",
            },
            {
                "id": "failure",
                "type": "failure",
                "title": "Failure",
                "description": "Terminal failure for rejected or failed pilot runs.",
            },
            {
                "id": "end",
                "type": "end",
                "title": "Escalation recorded",
                "description": "The local pilot completed successfully.",
            },
        ],
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "intake_review", "label": "next"},
            {"id": "edge_review_api", "from": "intake_review", "to": "call_support_api", "label": "next"},
            {"id": "edge_review_failure", "from": "intake_review", "to": "failure", "label": "failure"},
            {"id": "edge_api_end", "from": "call_support_api", "to": "end", "label": "next"},
            {"id": "edge_api_failure", "from": "call_support_api", "to": "failure", "label": "failure"},
        ],
        "state_schema": {},
        "guards": [],
        "checkpoints": [],
        "policies": {
            "default_retry": {"max_attempts": 0},
            "default_timeout_ms": 300000,
        },
    }


def _connector_request_summary(request: Dict[str, object]) -> Dict[str, object]:
    headers = request.get("headers", {}) if isinstance(request, dict) else {}
    authorization = headers.get("Authorization") if isinstance(headers, dict) else ""
    return {
        "received": bool(request),
        "method": request.get("method", "") if isinstance(request, dict) else "",
        "path": request.get("path", "") if isinstance(request, dict) else "",
        "authorization_present": bool(authorization),
        "credential_header_matched": authorization == f"Bearer {PILOT_SECRET}",
        "body_keys": sorted((request.get("body") or {}).keys()) if isinstance(request.get("body"), dict) else [],
    }


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("pilot work_dir must be outside the repository when reset is enabled")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("pilot work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _existing_connector_port(workflow_path: Path) -> int:
    if not workflow_path.exists():
        return 0
    try:
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    for node in workflow.get("nodes", []):
        if not isinstance(node, dict) or node.get("id") != "call_support_api":
            continue
        connector = node.get("connector", {})
        request = connector.get("request", {}) if isinstance(connector, dict) else {}
        url = str(request.get("url") or "") if isinstance(request, dict) else ""
        parsed = urlsplit(url)
        return int(parsed.port or 0)
    return 0


class _PilotConnectorReceiver:
    def __init__(self, port: int = 0):
        self._server = HTTPServer(("127.0.0.1", int(port)), _PilotConnectorHandler)
        self._server.requests = []
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/support/escalations"

    def start(self) -> None:
        self._thread.start()

    def last_request(self) -> Dict[str, object]:
        requests = getattr(self._server, "requests", [])
        return requests[-1] if requests else {}

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class _PilotConnectorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        body_bytes = self.rfile.read(content_length)
        body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        self.server.requests.append(
            {
                "method": "POST",
                "path": self.path,
                "headers": dict(self.headers.items()),
                "body": body,
            }
        )
        payload = json.dumps({"ok": True, "received": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return
