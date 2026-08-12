#!/usr/bin/env python3
"""Prove stopped, copy-on-write retention and retained-service cutover."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.schedules import RecurringScheduleStore
from skill2workflow.service import SERVICE_SCHEMA_VERSION


AUTH_TOKEN = "retention-smoke-ingress-token-0123456789abcdef"
PRIVATE_OLD_VALUE = "private-old-retention-payload-49382"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    source = work_dir / "source-state"
    retained = work_dir / "retained-state"
    blocked_output = work_dir / "blocked-output"
    policy_path = work_dir / "retention-policy.json"
    token_file = work_dir / "ingress.token"
    credential_dir = work_dir / "credentials"
    credential_dir.mkdir(exist_ok=True)
    credential_dir.chmod(0o700)
    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
    token_file.chmod(0o600)
    policy_path.write_text(json.dumps(_policy(), indent=2), encoding="utf-8")
    _populate(source)

    first_port = _available_port()
    first_config = work_dir / "source-service.json"
    _write_config(first_config, source, token_file, credential_dir, first_port)
    source_process = _start_service(first_config)
    try:
        _wait_until_ready(first_port, source_process)
        blocked = _retention_cli(source, blocked_output, policy_path)
    finally:
        _stop_service(source_process)
    with sqlite3.connect(source / "scheduler.sqlite3") as connection:
        connection.execute(
            "update schedule_dispatches set status = 'claimed', record_json = '{}' "
            "where dispatch_id = 'dispatch-old-claimed'"
        )
    source_before = _database_bytes(source)
    applied = _retention_cli(source, retained, policy_path)
    applied_summary = json.loads(applied.stdout) if applied.returncode == 0 else {}
    source_preserved = source_before == _database_bytes(source)
    removed, protected = _inspect_retained(retained)
    retained_bytes = b"".join(_database_bytes(retained).values())

    second_port = _available_port()
    second_config = work_dir / "retained-service.json"
    _write_config(second_config, retained, token_file, credential_dir, second_port)
    retained_process = _start_service(second_config)
    try:
        _wait_until_ready(second_port, retained_process)
        trigger_status = _trigger(second_port)
    finally:
        _stop_service(retained_process)

    serialized_operation = applied.stdout + applied.stderr + blocked.stdout + blocked.stderr
    evidence = {
        "schema_version": "skill2workflow-retention-evidence-0.1.0",
        "status": "passed",
        "checks": {
            "active_service_blocked": (
                blocked.returncode == 1
                and "active scheduler lease" in blocked.stderr
                and not blocked_output.exists()
            ),
            "source_preserved": source_preserved,
            "terminal_data_removed": (
                applied.returncode == 0
                and applied_summary.get("deleted_terminal_runs") == 1
                and applied_summary.get("deleted_terminal_dispatches") == 1
                and removed
                and PRIVATE_OLD_VALUE.encode("utf-8") not in retained_bytes
            ),
            "protected_state_preserved": protected,
            "retained_service_ready": retained_process.returncode == 0,
            "retained_service_trigger": trigger_status == 200,
            "private_values_absent": (
                PRIVATE_OLD_VALUE not in serialized_operation
                and AUTH_TOKEN not in serialized_operation
            ),
        },
        "deleted_terminal_runs": int(
            applied_summary.get("deleted_terminal_runs", 0)
        ),
        "preserved_protected_records": int(
            applied_summary.get("preserved_nonterminal_runs", 0)
        )
        + int(applied_summary.get("preserved_claimed_dispatches", 0)),
    }
    if not all(evidence["checks"].values()):
        evidence["status"] = "failed"
    (work_dir / "retention-smoke.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


def _populate(state_dir: Path) -> None:
    control = LocalControlPlane(state_dir, storage="sqlite")
    control.publish_workflow(_workflow("workflow_retention_smoke", gate=False))
    control.publish_workflow(_workflow("workflow_retention_waiting", gate=True))
    old = control.trigger_workflow(
        {
            "workflow_id": "workflow_retention_smoke",
            "version": "0.1.0",
            "idempotency_key": "retention-old",
            "input": {"private": PRIVATE_OLD_VALUE},
        }
    )
    waiting = control.trigger_workflow(
        {
            "workflow_id": "workflow_retention_waiting",
            "version": "0.1.0",
            "idempotency_key": "retention-waiting",
            "input": {"protected": "waiting-value"},
        }
    )
    RecurringScheduleStore(state_dir)
    with sqlite3.connect(state_dir / "runs.sqlite3") as connection:
        connection.execute(
            "update runs set updated_at = ? where run_id in (?, ?)",
            ("2025-01-01 00:00:00", old["run_id"], waiting["run_id"]),
        )
    with sqlite3.connect(state_dir / "scheduler.sqlite3") as connection:
        connection.execute(
            "insert into schedule_dispatches values (?, ?, ?, ?, ?, ?, ?)",
            (
                "dispatch-old-terminal",
                "schedule-old-terminal",
                "2025-01-01T00:00:00+00:00",
                "completed",
                "owner",
                0,
                json.dumps({"private": PRIVATE_OLD_VALUE}),
            ),
        )
        connection.execute(
            "insert into schedule_dispatches values (?, ?, ?, ?, ?, ?, ?)",
            (
                "dispatch-old-claimed",
                "schedule-old-claimed",
                "2025-01-01T00:00:00+00:00",
                "claimed",
                "owner",
                0,
                "{}",
            ),
        )


def _retention_cli(state_dir: Path, output_dir: Path, policy_path: Path):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(SRC) + (
        os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else ""
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "skill2workflow.cli",
            "state-retention-apply",
            str(policy_path),
            "--state-dir",
            str(state_dir),
            "--output-dir",
            str(output_dir),
        ],
        cwd=str(ROOT),
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


def _inspect_retained(state_dir: Path):
    with sqlite3.connect(state_dir / "runs.sqlite3") as connection:
        statuses = [str(row[0]) for row in connection.execute("select status from runs")]
    with sqlite3.connect(state_dir / "scheduler.sqlite3") as connection:
        dispatch_statuses = [
            str(row[0])
            for row in connection.execute("select status from schedule_dispatches")
        ]
    return (
        statuses == ["waiting"] and dispatch_statuses == ["claimed"],
        "waiting" in statuses and "claimed" in dispatch_statuses,
    )


def _write_config(path, state_dir, token_file, credential_dir, port):
    path.write_text(
        json.dumps(
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "127.0.0.1", "port": port},
                "runtime": {"state_dir": str(state_dir), "storage": "sqlite"},
                "auth": {"provider": "bearer_token_file", "token_file": str(token_file)},
                "credentials": {"provider": "directory", "directory": str(credential_dir)},
            },
            indent=2,
        ),
        encoding="utf-8",
    )


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


def _wait_until_ready(port: int, process) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("service stopped before readiness")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz", timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.05)
    raise RuntimeError("service readiness timed out")


def _trigger(port: int) -> int:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhooks/workflow_retention_smoke/0.1.0",
        data=json.dumps({"idempotency_key": "retained-cutover"}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            response.read()
            return response.status
    except urllib.error.HTTPError as error:
        try:
            error.read()
            return error.code
        finally:
            error.close()


def _stop_service(process) -> None:
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        raise RuntimeError("service did not stop after SIGTERM")


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _database_bytes(state_dir: Path):
    return {
        name: (state_dir / name).read_bytes()
        for name in ("control.sqlite3", "runs.sqlite3", "scheduler.sqlite3")
    }


def _policy():
    return {
        "schema_version": "skill2workflow-retention-policy-0.1.0",
        "retention": {
            "delete_before": "2026-01-01T00:00:00Z",
            "terminal_run_statuses": ["completed", "failed"],
            "terminal_dispatch_statuses": [
                "completed",
                "failed",
                "skipped",
                "uncertain",
            ],
        },
    }


def _workflow(workflow_id: str, gate: bool):
    middle = (
        {"id": "gate", "type": "human_gate", "title": "Gate", "on_success": "end", "on_failure": "end"}
        if gate
        else {"id": "step", "type": "action", "title": "Step", "on_success": "end"}
    )
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": workflow_id,
            "name": "Retention smoke",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": middle["id"]},
            middle,
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge-start-middle", "from": "start", "to": middle["id"], "label": "next"},
            {"id": "edge-middle-end", "from": middle["id"], "to": "end", "label": "next"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
