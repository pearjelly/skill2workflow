"""Deterministic local pilot scenario pack."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List

from .compiler import validate_workflow
from .control_plane import LocalControlPlane
from .credentials import StaticCredentialProvider
from .dashboard import build_control_snapshot
from .pilot import DEFAULT_UI_URL, PILOT_SECRET, run_pilot_playbook
from .visualizer import workflow_to_litegraph
from .webhooks import handle_webhook_request


DEFAULT_PACK_WORK_DIR = Path(tempfile.gettempdir()) / "skill2workflow-pilot-pack"


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    workflow_id: str
    workflow_name: str
    description: str
    review_title: str
    review_prompt: str
    tool_title: str
    tool_instruction: str
    event_name: str
    endpoint_path: str
    trigger_input: Dict[str, object]
    input_mapping: List[Dict[str, object]]


SCENARIOS = [
    ScenarioDefinition(
        scenario_id="sales_renewal",
        workflow_id="workflow_sales_renewal_pilot",
        workflow_name="sales-renewal-pilot",
        description="Local pilot scenario for sales renewal follow-up.",
        review_title="Review renewal follow-up",
        review_prompt="Approve the renewal follow-up for the local pilot.",
        tool_title="Notify renewal API",
        tool_instruction="Notify the local renewal API that the account follow-up was approved.",
        event_name="sales_renewal_followup_approved",
        endpoint_path="/sales/renewals",
        trigger_input={
            "account_id": "acct_123",
            "owner_id": "owner_456",
            "renewal_date": "2026-08-15",
        },
        input_mapping=[
            {"from": "/input/account_id", "to": "/body/account_id", "required": True},
            {"from": "/input/owner_id", "to": "/body/owner_id", "required": True},
            {"from": "/input/renewal_date", "to": "/body/renewal_date", "required": True},
        ],
    ),
    ScenarioDefinition(
        scenario_id="risk_exception",
        workflow_id="workflow_risk_exception_pilot",
        workflow_name="risk-exception-pilot",
        description="Local pilot scenario for risk exception review.",
        review_title="Review risk exception",
        review_prompt="Approve the risk exception disposition for the local pilot.",
        tool_title="Notify risk API",
        tool_instruction="Notify the local risk API that the exception disposition was approved.",
        event_name="risk_exception_approved",
        endpoint_path="/risk/exceptions",
        trigger_input={
            "case_id": "risk_case_789",
            "severity": "medium",
            "analyst_id": "analyst_123",
        },
        input_mapping=[
            {"from": "/input/case_id", "to": "/body/case_id", "required": True},
            {"from": "/input/severity", "to": "/body/severity", "required": True},
            {"from": "/input/analyst_id", "to": "/body/analyst_id", "required": True},
        ],
    ),
]


def run_pilot_scenario_pack(
    repo_root: Path,
    work_dir: Path = DEFAULT_PACK_WORK_DIR,
    reset: bool = True,
) -> Dict[str, object]:
    """Run multiple deterministic local pilot scenarios and write pack artifacts."""
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)

    artifacts_dir = work_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    customer_support = run_pilot_playbook(
        repo_root=repo_root,
        work_dir=work_dir / "customer_support",
        reset=reset,
    )
    scenarios = [_scenario_result_from_customer_support(customer_support)]
    for definition in SCENARIOS:
        scenarios.append(_run_http_scenario(definition, work_dir, reset=reset))

    result = {
        "ok": all(bool(item.get("ok")) for item in scenarios),
        "work_dir": str(work_dir),
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "artifacts": {
            "index": str(artifacts_dir / "scenario-pack.json"),
        },
        "commands": {
            "run_pilot_scenario_pack": f"python3 scripts/pilot_scenario_pack_smoke.py --work-dir {work_dir}",
            "serve_ui": "python3 -m http.server 4173",
            "ui_url": DEFAULT_UI_URL,
        },
    }
    _write_json(artifacts_dir / "scenario-pack.json", result)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="pilot_scenario_pack_smoke",
        description="Generate and run multiple local pilot scenarios.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_PACK_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true", help="Keep existing pilot scenario pack artifacts.")
    args = parser.parse_args(argv)

    result = run_pilot_scenario_pack(args.repo_root, args.work_dir, reset=not args.no_reset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _run_http_scenario(definition: ScenarioDefinition, pack_work_dir: Path, reset: bool) -> Dict[str, object]:
    scenario_dir = pack_work_dir / definition.scenario_id
    artifacts_dir = scenario_dir / "artifacts"
    state_dir = scenario_dir / "state"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = artifacts_dir / "workflow.json"

    receiver = _ScenarioConnectorReceiver(
        definition.endpoint_path,
        port=_existing_connector_port(workflow_path, node_id="call_api") if not reset else 0,
    )
    receiver.start()
    try:
        workflow = _scenario_workflow(definition, receiver.url)
        errors = validate_workflow(workflow)
        if errors:
            raise ValueError("; ".join(errors))

        control = LocalControlPlane(
            state_dir,
            credential_provider=StaticCredentialProvider({"pilot_api_token": PILOT_SECRET}),
        )
        control.publish_workflow(workflow)
        trigger_payload = {
            "source": "local-webhook",
            "idempotency_key": f"{definition.scenario_id}-001",
            "input": definition.trigger_input,
        }
        trigger_response = handle_webhook_request(
            control,
            "POST",
            f"/webhooks/{definition.workflow_id}/0.1.0",
            json.dumps(trigger_payload).encode("utf-8"),
        )
        run_id = str(trigger_response["run_id"])
        run_state = control.get_run(run_id)
        if run_state.get("status") == "waiting":
            run_state = control.resume_published_run(run_id, approved=True)

        audit_events = control.list_audit_events(run_id=run_id)
        snapshot = build_control_snapshot(state_dir)
        litegraph_overlay = workflow_to_litegraph(workflow, run_state=run_state, audit_events=audit_events)

        paths = {
            "workflow": workflow_path,
            "trigger_response": artifacts_dir / "trigger-response.json",
            "run": artifacts_dir / "run.json",
            "snapshot": artifacts_dir / "control-plane-snapshot.json",
            "litegraph_overlay": artifacts_dir / "workflow.overlay.litegraph.json",
        }
        _write_json(paths["workflow"], workflow)
        _write_json(paths["trigger_response"], trigger_response)
        _write_json(paths["run"], run_state)
        _write_json(paths["snapshot"], snapshot)
        _write_json(paths["litegraph_overlay"], litegraph_overlay)

        return {
            "ok": True,
            "id": definition.scenario_id,
            "workflow_id": definition.workflow_id,
            "workflow_version": "0.1.0",
            "run_id": run_id,
            "run_status": run_state.get("status", ""),
            "trigger_response": trigger_response,
            "snapshot_summary": snapshot.get("summary", {}),
            "connector_request": _connector_request_summary(
                receiver.last_request(),
                expected_body=definition.trigger_input,
            ),
            "artifacts": {key: str(path) for key, path in paths.items()},
        }
    finally:
        receiver.close()


def _scenario_workflow(definition: ScenarioDefinition, connector_url: str) -> Dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": definition.workflow_id,
            "name": definition.workflow_name,
            "description": definition.description,
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "title": "Receive pilot event",
                "description": definition.description,
                "on_success": "review",
            },
            {
                "id": "review",
                "type": "human_gate",
                "title": definition.review_title,
                "description": "Manual approval gate for the local pilot scenario.",
                "action": {"kind": "human_approval", "prompt": definition.review_prompt},
                "connector": {"id": "manual", "kind": "manual"},
                "on_success": "call_api",
                "on_failure": "failure",
            },
            {
                "id": "call_api",
                "type": "tool_call",
                "title": definition.tool_title,
                "description": "Call the local HTTP receiver with mapped trigger input.",
                "action": {"kind": "tool_call", "instruction": definition.tool_instruction},
                "retry": {"max_attempts": 0},
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {
                        "method": "POST",
                        "url": connector_url,
                        "headers": {"Content-Type": "application/json"},
                        "body": {
                            "source": "skill2workflow-pilot-pack",
                            "event": definition.event_name,
                        },
                        "input_mapping": definition.input_mapping,
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
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "Pilot scenario completed"},
        ],
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
            {"id": "edge_review_api", "from": "review", "to": "call_api", "label": "next"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "failure"},
            {"id": "edge_api_end", "from": "call_api", "to": "end", "label": "next"},
            {"id": "edge_api_failure", "from": "call_api", "to": "failure", "label": "failure"},
        ],
        "state_schema": {},
        "guards": [],
        "checkpoints": [],
        "policies": {"default_retry": {"max_attempts": 0}, "default_timeout_ms": 300000},
    }


def _scenario_result_from_customer_support(result: Dict[str, object]) -> Dict[str, object]:
    compact = dict(result)
    compact["id"] = "customer_support"
    return compact


def _connector_request_summary(
    request: Dict[str, object],
    expected_body: Dict[str, object],
) -> Dict[str, object]:
    headers = request.get("headers", {}) if isinstance(request, dict) else {}
    authorization = headers.get("Authorization") if isinstance(headers, dict) else ""
    body = request.get("body", {}) if isinstance(request, dict) else {}
    body = body if isinstance(body, dict) else {}
    expected_keys = sorted(str(key) for key in expected_body.keys())
    return {
        "received": bool(request),
        "method": request.get("method", "") if isinstance(request, dict) else "",
        "path": request.get("path", "") if isinstance(request, dict) else "",
        "authorization_present": bool(authorization),
        "credential_header_matched": authorization == f"Bearer {PILOT_SECRET}",
        "body_keys": sorted(str(key) for key in body.keys()),
        "mapped_input_keys": expected_keys,
        "mapped_body_matched": all(body.get(key) == value for key, value in expected_body.items()),
    }


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("pilot scenario pack work_dir must be outside the repository when reset is enabled")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("pilot scenario pack work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _existing_connector_port(workflow_path: Path, node_id: str) -> int:
    if not workflow_path.exists():
        return 0
    try:
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    for node in workflow.get("nodes", []):
        if not isinstance(node, dict) or node.get("id") != node_id:
            continue
        connector = node.get("connector", {})
        request = connector.get("request", {}) if isinstance(connector, dict) else {}
        url = str(request.get("url") or "") if isinstance(request, dict) else ""
        try:
            return int(url.rsplit(":", 1)[1].split("/", 1)[0])
        except (IndexError, ValueError):
            return 0
    return 0


class _ScenarioConnectorReceiver:
    def __init__(self, path: str, port: int = 0):
        self._path = path
        self._server = HTTPServer(("127.0.0.1", int(port)), _ScenarioConnectorHandler)
        self._server.requests = []
        self._server.expected_path = path
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}{self._path}"

    def start(self) -> None:
        self._thread.start()

    def last_request(self) -> Dict[str, object]:
        requests = getattr(self._server, "requests", [])
        return requests[-1] if requests else {}

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class _ScenarioConnectorHandler(BaseHTTPRequestHandler):
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
