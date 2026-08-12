#!/usr/bin/env python3
"""Exercise authenticated ingress and execution-time credential rotation."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.service import SERVICE_SCHEMA_VERSION


FIRST_INGRESS_TOKEN = "security-smoke-ingress-token-0123456789abcdef"
SECOND_INGRESS_TOKEN = "security-smoke-rotated-token-0123456789abcdef"
FIRST_CONNECTOR_TOKEN = "first-connector-token"
SECOND_CONNECTOR_TOKEN = "rotated-connector-token"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    state_dir = work_dir / "state"
    credential_dir = work_dir / "credentials"
    credential_dir.mkdir(exist_ok=True)
    credential_dir.chmod(0o700)
    ingress_file = work_dir / "ingress.token"
    ingress_file.write_text(FIRST_INGRESS_TOKEN, encoding="utf-8")
    ingress_file.chmod(0o600)
    connector_file = credential_dir / "demo_api_token"
    connector_file.write_text(FIRST_CONNECTOR_TOKEN, encoding="utf-8")
    connector_file.chmod(0o600)

    receiver = _Receiver()
    port = _available_port()
    config_path = work_dir / "service.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "127.0.0.1", "port": port},
                "runtime": {"state_dir": str(state_dir), "storage": "sqlite"},
                "auth": {
                    "provider": "bearer_token_file",
                    "token_file": str(ingress_file),
                },
                "credentials": {
                    "provider": "directory",
                    "directory": str(credential_dir),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    LocalControlPlane(state_dir, storage="sqlite").publish_workflow(_workflow(receiver.url))

    process = _start_service(config_path)
    try:
        _wait_until_ready(port, process)
        missing_status, _ = _request(port, token=None)
        first_status, _ = _request(port, token=FIRST_INGRESS_TOKEN, idempotency_key="first")
        connector_file.chmod(0o644)
        unsafe_status, unsafe_result = _request(
            port,
            token=FIRST_INGRESS_TOKEN,
            idempotency_key="unsafe-permissions",
        )
        connector_file.chmod(0o600)
        connector_file.write_text(SECOND_CONNECTOR_TOKEN, encoding="utf-8")
        ingress_file.write_text(SECOND_INGRESS_TOKEN, encoding="utf-8")
        old_status, _ = _request(port, token=FIRST_INGRESS_TOKEN, idempotency_key="old")
        second_status, _ = _request(port, token=SECOND_INGRESS_TOKEN, idempotency_key="second")
    finally:
        _stop_service(process)
        receiver.close()

    audit = LocalControlPlane(state_dir, storage="sqlite").list_audit_events()
    ingress_events = [event for event in audit if str(event.get("type", "")).startswith("ingress_")]
    serialized = json.dumps(ingress_events, ensure_ascii=False)
    secrets_absent = all(
        secret not in serialized
        for secret in (
            FIRST_INGRESS_TOKEN,
            SECOND_INGRESS_TOKEN,
            FIRST_CONNECTOR_TOKEN,
            SECOND_CONNECTOR_TOKEN,
        )
    )
    evidence = {
        "schema_version": "skill2workflow-security-boundary-evidence-0.1.0",
        "status": "passed",
        "checks": {
            "unauthenticated_denied": missing_status == 401,
            "ingress_token_rotation": first_status == 200 and old_status == 401 and second_status == 200,
            "execution_time_credential_rotation": receiver.authorization_headers
            == [f"Bearer {FIRST_CONNECTOR_TOKEN}", f"Bearer {SECOND_CONNECTOR_TOKEN}"],
            "unsafe_credential_file_blocked": unsafe_status == 200
            and unsafe_result.get("run_status") == "failed"
            and len(receiver.authorization_headers) == 2,
            "compact_audit_has_no_secrets": secrets_absent,
            "graceful_exit": process.returncode == 0,
        },
        "authenticated_events": sum(event["type"] == "ingress_authenticated" for event in ingress_events),
        "denied_events": sum(event["type"] == "ingress_authentication_denied" for event in ingress_events),
    }
    if not all(evidence["checks"].values()):
        evidence["status"] = "failed"
    evidence_path = work_dir / "security-boundary-smoke.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


def _start_service(config_path: Path):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(SRC) + (
        os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else ""
    )
    return subprocess.Popen(
        [sys.executable, "-m", "skill2workflow.cli", "service", "--config", str(config_path)],
        cwd=str(ROOT),
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def _stop_service(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        raise RuntimeError("service did not stop after SIGTERM")
    if process.stderr is not None:
        process.stderr.close()


def _wait_until_ready(port: int, process) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read().strip() if process.stderr else ""
            raise RuntimeError(f"service stopped before readiness: {stderr}")
        try:
            status, payload = _get_json(f"http://127.0.0.1:{port}/readyz")
            if status == 200 and payload.get("status") == "ready":
                return
        except OSError:
            pass
        time.sleep(0.05)
    raise RuntimeError("service readiness timed out")


def _request(port: int, token=None, idempotency_key=""):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhooks/workflow_security_boundary/0.1.0",
        data=json.dumps({"idempotency_key": idempotency_key}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    return _open_json(request)


def _get_json(url: str):
    return _open_json(urllib.request.Request(url, method="GET"))


def _open_json(request):
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        finally:
            error.close()


def _available_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _workflow(url: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_security_boundary",
            "name": "Security boundary",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "call"},
            {
                "id": "call",
                "type": "tool_call",
                "title": "Call",
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {"method": "GET", "url": url, "timeout_ms": 1000},
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
            {"id": "edge_start_call", "from": "start", "to": "call", "label": "next"},
            {"id": "edge_call_end", "from": "call", "to": "end", "label": "next"},
            {"id": "edge_call_failure", "from": "call", "to": "failure", "label": "failure"},
        ],
    }


class _Receiver:
    def __init__(self):
        self.authorization_headers = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                owner.authorization_headers.append(self.headers.get("Authorization", ""))
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                return

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}/credential"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
