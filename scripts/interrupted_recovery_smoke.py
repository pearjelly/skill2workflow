#!/usr/bin/env python3
"""Prove crash takeover without replaying an external side effect."""

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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.service import SERVICE_SCHEMA_VERSION


AUTH_TOKEN = "interrupted-recovery-smoke-token-0123456789"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    arguments = parser.parse_args(argv)

    work_dir = arguments.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    state_dir = work_dir / "state"
    token_file = work_dir / "ingress.token"
    credential_dir = work_dir / "credentials"
    config_path = work_dir / "service.json"
    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
    token_file.chmod(0o600)
    credential_dir.mkdir(exist_ok=True)
    credential_dir.chmod(0o700)
    provider = _Provider()
    provider.start()
    service_port = _available_port()
    config_path.write_text(
        json.dumps(
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "127.0.0.1", "port": service_port},
                "runtime": {"state_dir": str(state_dir), "storage": "sqlite"},
                "auth": {
                    "provider": "bearer_token_file",
                    "token_file": str(token_file),
                },
                "credentials": {
                    "provider": "directory",
                    "directory": str(credential_dir),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    control = LocalControlPlane(state_dir, storage="sqlite")
    control.publish_workflow(_crash_workflow(provider.url))
    control.publish_workflow(_waiting_workflow())
    waiting = control.run_published_workflow("workflow_crash_waiting", "0.1.0")
    active = _start_service(config_path)
    replacement = None
    trigger = {}
    trigger_thread = None
    try:
        _wait_until_ready(service_port, active, timeout=5)

        def invoke():
            try:
                trigger["response"] = _request_json(
                    f"http://127.0.0.1:{service_port}/webhooks/workflow_crash_recovery/0.1.0",
                    method="POST",
                    payload={
                        "source": "interrupted-recovery-smoke",
                        "idempotency_key": "crash-001",
                    },
                    timeout=30,
                )
            except Exception as error:
                trigger["error_type"] = type(error).__name__

        trigger_thread = threading.Thread(target=invoke, daemon=True)
        trigger_thread.start()
        if not provider.committed.wait(timeout=5):
            raise RuntimeError("provider did not receive the first request")
        run_id = _active_run_id(state_dir)
        active.kill()
        active.wait(timeout=5)
        provider.release.set()
        trigger_thread.join(timeout=5)

        replacement = _start_service(config_path)
        _wait_until_ready(service_port, replacement, timeout=15)
        recovered = LocalControlPlane(state_dir, storage="sqlite")
        run = recovered.get_run(run_id)
        waiting_after = recovered.get_run(waiting["run_id"])
        audits = recovered.list_audit_events(
            run_id=run_id, event_type="run_interrupted"
        )
        metrics = _request_text(
            f"http://127.0.0.1:{service_port}/metrics", token=AUTH_TOKEN
        )
        with _run_database(state_dir) as database:
            ticket = database.execute(
                "select status from run_executions where run_id = ?", (run_id,)
            ).fetchone()

        checks = {
            "provider_side_effect_committed_once": provider.primary_calls == 1,
            "successor_not_called": provider.successor_calls == 0,
            "run_marked_interrupted": run["status"] == "interrupted",
            "interruption_recorded_once": (
                [event.get("type") for event in run.get("events", [])].count(
                    "run_interrupted"
                )
                == 1
                and len(audits) == 1
            ),
            "execution_ticket_fenced": ticket == ("interrupted",),
            "waiting_run_preserved": waiting_after["status"] == "waiting",
            "no_automatic_retry": provider.primary_calls == 1,
            "aggregate_metric_exported": (
                'skill2workflow_runs{status="interrupted"} 1' in metrics
            ),
            "standby_became_ready": True,
        }
        evidence = {
            "schema_version": "skill2workflow-interrupted-recovery-evidence-0.1.0",
            "status": "passed" if all(checks.values()) else "failed",
            "checks": checks,
            "provider_attempts": provider.primary_calls,
            "successor_attempts": provider.successor_calls,
        }
    finally:
        provider.release.set()
        provider.stop()
        for process in (active, replacement):
            if process is None:
                continue
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if process.stderr is not None:
                process.stderr.close()

    evidence_path = work_dir / "interrupted-recovery-smoke.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


def _start_service(config_path: Path):
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = str(SRC) + (
        os.pathsep + existing if existing else ""
    )
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "skill2workflow.cli",
            "service",
            "--config",
            str(config_path),
        ],
        cwd=str(ROOT),
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_until_ready(port: int, process: subprocess.Popen, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            detail = process.stderr.read().strip() if process.stderr else ""
            raise RuntimeError(f"service stopped before readiness: {detail}")
        try:
            payload = _request_json(f"http://127.0.0.1:{port}/readyz", timeout=1)
            if payload.get("status") == "ready":
                return
        except urllib.error.HTTPError as error:
            error.close()
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.05)
    raise RuntimeError("service readiness timed out")


def _active_run_id(state_dir: Path) -> str:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        runs = LocalControlPlane(state_dir, storage="sqlite").list_runs()
        active = [run for run in runs if run["status"] == "running"]
        if len(active) == 1:
            return str(active[0]["run_id"])
        time.sleep(0.02)
    raise RuntimeError("active run was not persisted")


def _request_json(url: str, method="GET", payload=None, timeout=2):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    if data is not None:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_text(url: str, token: str) -> str:
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        return response.read().decode("utf-8")


def _run_database(state_dir: Path):
    import sqlite3

    return sqlite3.connect(state_dir / "runs.sqlite3")


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _Provider:
    def __init__(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                if self.path == "/primary":
                    owner.primary_calls += 1
                    owner.committed.set()
                    owner.release.wait(timeout=30)
                elif self.path == "/successor":
                    owner.successor_calls += 1
                body = b'{"status":"ok"}'
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, format, *args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.committed = threading.Event()
        self.release = threading.Event()
        self.primary_calls = 0
        self.successor_calls = 0

    @property
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def _crash_workflow(provider_url: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_crash_recovery",
            "name": "Crash recovery",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "primary",
        "nodes": [
            {
                "id": "primary",
                "type": "tool_call",
                "title": "Primary side effect",
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {
                        "method": "POST",
                        "url": provider_url + "/primary",
                        "body": {"operation": "primary"},
                        "timeout_ms": 30000,
                    },
                },
                "on_success": "successor",
                "on_failure": "failure",
            },
            {
                "id": "successor",
                "type": "tool_call",
                "title": "Successor",
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {
                        "method": "POST",
                        "url": provider_url + "/successor",
                        "body": {"operation": "successor"},
                        "timeout_ms": 2000,
                    },
                },
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "end", "type": "end", "title": "Done"},
            {"id": "failure", "type": "failure", "title": "Failed"},
        ],
        "edges": [
            {"id": "edge_primary_successor", "from": "primary", "to": "successor", "label": "next"},
            {"id": "edge_primary_failure", "from": "primary", "to": "failure", "label": "failure"},
            {"id": "edge_successor_end", "from": "successor", "to": "end", "label": "next"},
            {"id": "edge_successor_failure", "from": "successor", "to": "failure", "label": "failure"},
        ],
    }


def _waiting_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_crash_waiting",
            "name": "Preserved waiting run",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "review",
        "nodes": [
            {
                "id": "review",
                "type": "human_gate",
                "title": "Review",
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "end", "type": "end", "title": "Done"},
            {"id": "failure", "type": "failure", "title": "Failed"},
        ],
        "edges": [
            {"id": "edge_review_end", "from": "review", "to": "end", "label": "next"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "failure"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
