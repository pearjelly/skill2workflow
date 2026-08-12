#!/usr/bin/env python3
"""Exercise verified backup, point-in-time restore, and restored service startup."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
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

from skill2workflow.backup import (
    create_state_backup,
    restore_state_backup,
    verify_state_backup,
)
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.schedules import RecurringScheduleDispatcher, RecurringScheduleStore
from skill2workflow.service import SERVICE_SCHEMA_VERSION


AUTH_TOKEN = "backup-restore-smoke-token-0123456789abcdef"
CONNECTOR_SECRET = "backup-restore-connector-secret"
WORKFLOW_ID = "workflow_backup_restore_smoke"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    work_dir = args.work_dir.resolve()
    _reset_work_dir(work_dir)
    state_dir = work_dir / "state"
    backup_dir = work_dir / "backup"
    restored_dir = work_dir / "restored"
    blocked_backup = work_dir / "blocked-backup"
    control = LocalControlPlane(state_dir, storage="sqlite")
    control.publish_workflow(_workflow())
    control.trigger_workflow(_trigger("before-backup"))
    RecurringScheduleStore(state_dir).add(_future_schedule())

    active = RecurringScheduleDispatcher(
        state_dir,
        owner_id="backup-smoke-active-owner",
        lease_seconds=30,
    )
    active.try_acquire(now_epoch=time.time())
    active_lease_blocked = False
    try:
        try:
            create_state_backup(state_dir, blocked_backup)
        except ValueError:
            active_lease_blocked = not blocked_backup.exists()
    finally:
        active.release()

    create_state_backup(state_dir, backup_dir)
    verified = verify_state_backup(backup_dir)
    control.trigger_workflow(_trigger("after-backup"))
    restore_state_backup(backup_dir, restored_dir)
    restored_control = LocalControlPlane(restored_dir, storage="sqlite")
    source_run_count = len(control.list_runs())
    restored_run_count = len(restored_control.list_runs())

    token_file = work_dir / "ingress.token"
    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
    token_file.chmod(0o600)
    credential_dir = work_dir / "credentials"
    credential_dir.mkdir()
    credential_dir.chmod(0o700)
    (credential_dir / "unused-secret").write_text(CONNECTOR_SECRET, encoding="utf-8")
    (credential_dir / "unused-secret").chmod(0o600)
    port = _available_port()
    config_path = _write_config(
        work_dir / "service.json",
        restored_dir,
        token_file,
        credential_dir,
        port,
    )
    service = _start_service(config_path)
    restored_service_ready = False
    restored_service_trigger = False
    try:
        _wait_until_ready(port, service)
        restored_service_ready = True
        status, payload = _post_trigger(port)
        restored_service_trigger = status == 200 and payload.get("run_status") == "completed"
    finally:
        graceful_exit = _stop_service(service) == 0

    tampered_dir = work_dir / "tampered-backup"
    shutil.copytree(backup_dir, tampered_dir)
    with (tampered_dir / "runs.sqlite3").open("ab") as handle:
        handle.write(b"tampered")
    try:
        verify_state_backup(tampered_dir)
        tampering_rejected = False
    except ValueError:
        tampering_rejected = True

    backup_bytes = b"".join(
        path.read_bytes() for path in backup_dir.rglob("*") if path.is_file()
    )
    credentials_excluded = (
        AUTH_TOKEN.encode("utf-8") not in backup_bytes
        and CONNECTOR_SECRET.encode("utf-8") not in backup_bytes
    )
    evidence = {
        "schema_version": "skill2workflow-backup-restore-evidence-0.1.0",
        "status": "passed",
        "checks": {
            "active_lease_blocked": active_lease_blocked,
            "verified_before_restore": verified["status"] == "valid",
            "point_in_time_snapshot": source_run_count == 2 and restored_run_count == 1,
            "restored_service_ready": restored_service_ready,
            "restored_service_trigger": restored_service_trigger,
            "tampering_rejected": tampering_rejected,
            "credentials_excluded": credentials_excluded,
            "graceful_exit": graceful_exit,
        },
        "restored_database_count": verified["database_count"],
        "restored_workflow_artifact_count": verified["workflow_artifact_count"],
    }
    if not all(evidence["checks"].values()):
        evidence["status"] = "failed"
    (work_dir / "backup-restore-smoke.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


def _reset_work_dir(path: Path) -> None:
    if path in {Path("/"), Path.home()}:
        raise ValueError("work directory must not be the filesystem root or home directory")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _write_config(
    path: Path,
    state_dir: Path,
    token_file: Path,
    credential_dir: Path,
    port: int,
) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "127.0.0.1", "port": port},
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
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _start_service(config_path: Path):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(SRC) + (
        os.pathsep + environment["PYTHONPATH"]
        if environment.get("PYTHONPATH")
        else ""
    )
    return subprocess.Popen(
        [sys.executable, "-m", "skill2workflow.cli", "service", "--config", str(config_path)],
        cwd=str(ROOT),
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def _stop_service(process) -> int:
    if process.poll() is None:
        process.terminate()
    try:
        return process.wait(timeout=5)
    except subprocess.TimeoutExpired as error:
        process.kill()
        process.wait(timeout=5)
        raise RuntimeError("restored service did not stop after SIGTERM") from error


def _wait_until_ready(port: int, process) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read().strip() if process.stderr else ""
            raise RuntimeError(f"restored service stopped before readiness: {stderr}")
        try:
            status, payload = _request_json(port, "/readyz")
            if status == 200 and payload.get("status") == "ready":
                return
        except OSError:
            pass
        time.sleep(0.05)
    raise RuntimeError("restored service readiness timed out")


def _post_trigger(port: int):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhooks/{WORKFLOW_ID}/0.1.0",
        data=json.dumps({"idempotency_key": "restored-service"}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    return _open_json(request)


def _request_json(port: int, path: str):
    return _open_json(
        urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="GET")
    )


def _open_json(request):
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        finally:
            error.close()


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _trigger(key: str):
    return {
        "workflow_id": WORKFLOW_ID,
        "version": "0.1.0",
        "source": "backup-restore-smoke",
        "idempotency_key": key,
        "input": {},
    }


def _future_schedule():
    return {
        "schema_version": "skill2workflow-schedule-0.2.0",
        "schedule": {
            "id": "schedule_backup_restore_smoke",
            "workflow_id": WORKFLOW_ID,
            "version": "0.1.0",
            "starts_at": "2099-01-01T00:00:00+00:00",
            "interval_seconds": 3600,
            "missed_run_policy": "latest",
        },
        "trigger": {"input": {}},
    }


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": WORKFLOW_ID,
            "name": "Backup restore smoke",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
