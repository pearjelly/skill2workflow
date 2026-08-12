#!/usr/bin/env python3
"""Exercise legacy preflight, copy-on-write upgrade, rollback, and service startup."""

from __future__ import annotations

import argparse
import hashlib
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

from skill2workflow.backup import verify_state_backup
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.migration import inspect_state_upgrade, upgrade_state
from skill2workflow.schedules import RecurringScheduleStore
from skill2workflow.service import SERVICE_SCHEMA_VERSION
from skill2workflow.state_layout import STATE_LAYOUT_MARKER


AUTH_TOKEN = "state-upgrade-smoke-token-0123456789abcdef"
WORKFLOW_ID = "workflow_state_upgrade_smoke"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    work_dir = args.work_dir.resolve()
    _reset(work_dir)
    source = work_dir / "legacy-state"
    upgraded = work_dir / "upgraded-state"
    backup = work_dir / "pre-upgrade-backup"
    control = LocalControlPlane(source, storage="sqlite")
    control.publish_workflow(_workflow())
    control.trigger_workflow(_trigger("before-upgrade"))
    RecurringScheduleStore(source)
    (source / STATE_LAYOUT_MARKER).unlink()
    (source / "scheduler.sqlite3").unlink()
    before = _state_digest(source)

    plan = inspect_state_upgrade(source)
    result = upgrade_state(source, upgraded, backup)
    verified = verify_state_backup(backup)
    source_unchanged = (
        _state_digest(source) == before and not (source / STATE_LAYOUT_MARKER).exists()
    )

    token_file = work_dir / "ingress.token"
    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
    token_file.chmod(0o600)
    credentials = work_dir / "credentials"
    credentials.mkdir()
    credentials.chmod(0o700)
    port = _available_port()
    config = _write_config(
        work_dir / "service.json", upgraded, token_file, credentials, port
    )
    service = _start_service(config)
    service_ready = False
    service_trigger = False
    try:
        _wait_ready(port, service)
        service_ready = True
        status, payload = _post_trigger(port)
        service_trigger = status == 200 and payload.get("run_status") == "completed"
    finally:
        graceful_exit = _stop_service(service) == 0

    future = work_dir / "future-state"
    shutil.copytree(upgraded, future)
    marker_path = future / STATE_LAYOUT_MARKER
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["state_layout_version"] = "skill2workflow-sqlite-layout-99.0.0"
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    try:
        LocalControlPlane(future, storage="sqlite")
        future_rejected = False
    except ValueError:
        future_rejected = True

    evidence = {
        "schema_version": "skill2workflow-state-upgrade-evidence-0.1.0",
        "status": "passed",
        "checks": {
            "preflight_detected_legacy": plan["status"] == "upgrade_required",
            "preupgrade_backup_verified": verified["status"] == "valid",
            "legacy_scheduler_synthesized": result["scheduler_database_synthesized"],
            "source_unchanged": source_unchanged,
            "copy_on_write_upgrade": result["status"] == "upgraded",
            "upgraded_service_ready": service_ready,
            "upgraded_service_trigger": service_trigger,
            "future_layout_rejected": future_rejected,
            "graceful_exit": graceful_exit,
        },
        "migrated_database_count": result["database_count"],
        "migrated_workflow_artifact_count": result["workflow_artifact_count"],
    }
    if not all(evidence["checks"].values()):
        evidence["status"] = "failed"
    (work_dir / "state-upgrade-smoke.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


def _reset(path: Path) -> None:
    if path in {Path("/"), Path.home()}:
        raise ValueError("work directory must not be the filesystem root or home directory")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _state_digest(state_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        path
        for path in state_dir.rglob("*")
        if path.is_file() and path.name != STATE_LAYOUT_MARKER
    ):
        digest.update(path.relative_to(state_dir).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_config(path, state_dir, token_file, credential_dir, port):
    path.write_text(
        json.dumps(
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "127.0.0.1", "port": port},
                "runtime": {"state_dir": str(state_dir), "storage": "sqlite"},
                "auth": {"provider": "bearer_token_file", "token_file": str(token_file)},
                "credentials": {"provider": "directory", "directory": str(credential_dir)},
            }
        ),
        encoding="utf-8",
    )
    return path


def _start_service(config_path):
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


def _wait_ready(port: int, process) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read().strip() if process.stderr else ""
            raise RuntimeError(f"upgraded service stopped before readiness: {stderr}")
        try:
            status, payload = _open_json(
                urllib.request.Request(f"http://127.0.0.1:{port}/readyz", method="GET")
            )
            if status == 200 and payload.get("status") == "ready":
                return
        except OSError:
            pass
        time.sleep(0.05)
    raise RuntimeError("upgraded service readiness timed out")


def _post_trigger(port: int):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhooks/{WORKFLOW_ID}/0.1.0",
        data=json.dumps({"idempotency_key": "after-upgrade"}).encode("utf-8"),
        headers={"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    return _open_json(request)


def _open_json(request):
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        finally:
            error.close()


def _stop_service(process) -> int:
    if process.poll() is None:
        process.terminate()
    try:
        return process.wait(timeout=5)
    except subprocess.TimeoutExpired as error:
        process.kill()
        process.wait(timeout=5)
        raise RuntimeError("upgraded service did not stop after SIGTERM") from error


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _trigger(key: str):
    return {
        "workflow_id": WORKFLOW_ID,
        "version": "0.1.0",
        "source": "state-upgrade-smoke",
        "idempotency_key": key,
        "input": {},
    }


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": WORKFLOW_ID,
            "name": "State upgrade smoke",
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
