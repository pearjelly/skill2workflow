#!/usr/bin/env python3
"""Exercise durable recurring dispatch, restart recovery, and lease takeover."""

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
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.schedules import RecurringScheduleDispatcher, RecurringScheduleStore
from skill2workflow.service import SERVICE_SCHEMA_VERSION


AUTH_TOKEN = "recurring-scheduler-smoke-token-0123456789abcdef"
WORKFLOW_ID = "workflow_recurring_scheduler_smoke"
SCHEDULE_ID = "schedule_recurring_scheduler_smoke"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    work_dir = args.work_dir.resolve()
    _reset_work_dir(work_dir)
    state_dir = work_dir / "state"
    credential_dir = work_dir / "credentials"
    credential_dir.mkdir(parents=True)
    credential_dir.chmod(0o700)
    token_file = work_dir / "ingress.token"
    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
    token_file.chmod(0o600)

    first_port = _available_port()
    standby_port = _available_port()
    first_config = _write_config(
        work_dir / "active.json", state_dir, credential_dir, token_file, first_port
    )
    standby_config = _write_config(
        work_dir / "standby.json", state_dir, credential_dir, token_file, standby_port
    )

    LocalControlPlane(state_dir, storage="sqlite").publish_workflow(_workflow())
    starts_at = (
        datetime.now(timezone.utc) + timedelta(seconds=1)
    ).replace(microsecond=0).isoformat()
    RecurringScheduleStore(state_dir).add(
        {
            "schema_version": "skill2workflow-schedule-0.2.0",
            "schedule": {
                "id": SCHEDULE_ID,
                "workflow_id": WORKFLOW_ID,
                "version": "0.1.0",
                "starts_at": starts_at,
                "interval_seconds": 1,
                "missed_run_policy": "latest",
            },
            "trigger": {"input": {"evidence": "recurring-scheduler-smoke"}},
        }
    )

    graceful_exits = []
    active = _start_service(first_config)
    try:
        _wait_for_readiness(first_port, active, expected_status=200)
        first_dispatches = _wait_for_dispatches(state_dir, minimum=1)
    finally:
        graceful_exits.append(_stop_service(active))

    time.sleep(2.1)
    restarted = _start_service(first_config)
    standby = None
    try:
        _wait_for_readiness(first_port, restarted, expected_status=200)
        recovered_dispatches = _wait_for_dispatches(
            state_dir, minimum=len(first_dispatches) + 1
        )
        recovered_record = recovered_dispatches[-1]

        standby = _start_service(standby_config)
        _wait_for_health(standby_port, standby)
        standby_before = _readiness_status(standby_port)
        graceful_exits.append(_stop_service(restarted))
        _wait_for_readiness(standby_port, standby, expected_status=200)
        standby_after = _readiness_status(standby_port)
    finally:
        if restarted.poll() is None:
            graceful_exits.append(_stop_service(restarted))
        if standby is not None:
            graceful_exits.append(_stop_service(standby))

    uncertain = _stale_claim_evidence(work_dir / "stale-claim-state")
    final_dispatches = RecurringScheduleStore(state_dir).list_dispatches(SCHEDULE_ID)
    evidence = {
        "schema_version": "skill2workflow-recurring-scheduler-evidence-0.1.0",
        "status": "passed",
        "checks": {
            "recurring_dispatch": len(first_dispatches) >= 1,
            "restart_recovery": len(recovered_dispatches) > len(first_dispatches),
            "latest_missed_run_coalesced": int(recovered_record["coalesced_occurrences"]) >= 1,
            "single_owner_readiness": standby_before == 503,
            "standby_takeover": standby_after == 200,
            "stale_claim_uncertain": uncertain,
            "graceful_exit": bool(graceful_exits) and all(code == 0 for code in graceful_exits),
        },
        "completed_dispatches": sum(
            record["status"] == "completed" for record in final_dispatches
        ),
        "uncertain_dispatches": 1 if uncertain else 0,
    }
    if not all(evidence["checks"].values()):
        evidence["status"] = "failed"
    evidence_path = work_dir / "recurring-scheduler-smoke.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


def _stale_claim_evidence(state_dir: Path) -> bool:
    LocalControlPlane(state_dir, storage="sqlite").publish_workflow(_workflow())
    RecurringScheduleStore(state_dir).add(
        {
            "schema_version": "skill2workflow-schedule-0.2.0",
            "schedule": {
                "id": "schedule_stale_claim",
                "workflow_id": WORKFLOW_ID,
                "version": "0.1.0",
                "starts_at": "2026-01-01T00:00:00+00:00",
                "interval_seconds": 60,
                "missed_run_policy": "latest",
            },
            "trigger": {"input": {}},
        }
    )
    crashed = RecurringScheduleDispatcher(
        state_dir, owner_id="smoke-crashed-owner", lease_seconds=2
    )
    if not crashed.try_acquire(now_epoch=100):
        return False
    claims = crashed.claim_due("2026-01-01T00:00:00+00:00", now_epoch=101)
    replacement = RecurringScheduleDispatcher(
        state_dir, owner_id="smoke-replacement-owner", lease_seconds=2
    )
    if not replacement.try_acquire(now_epoch=103):
        return False
    recovered = replacement.recover_stale_claims(now_epoch=103)
    retry = replacement.dispatch_due("2026-01-01T00:00:00+00:00", now_epoch=103.5)
    records = RecurringScheduleStore(state_dir).list_dispatches("schedule_stale_claim")
    replacement.release()
    return bool(
        len(claims) == 1
        and recovered == 1
        and retry["count"] == 0
        and len(records) == 1
        and records[0]["status"] == "uncertain"
    )


def _reset_work_dir(path: Path) -> None:
    if path in {Path("/"), Path.home()}:
        raise ValueError("work directory must not be the filesystem root or home directory")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _write_config(
    path: Path,
    state_dir: Path,
    credential_dir: Path,
    token_file: Path,
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
        raise RuntimeError("scheduler service did not stop after SIGTERM") from error


def _wait_for_dispatches(state_dir: Path, minimum: int):
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        records = RecurringScheduleStore(state_dir).list_dispatches(SCHEDULE_ID)
        if len(records) >= minimum and records[-1]["status"] == "completed":
            return records
        time.sleep(0.05)
    raise RuntimeError("recurring dispatch timed out")


def _wait_for_health(port: int, process) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        _raise_if_stopped(process)
        try:
            status, payload = _request_json(port, "/healthz")
            if status == 200 and payload.get("status") == "ok":
                return
        except OSError:
            pass
        time.sleep(0.05)
    raise RuntimeError("service health timed out")


def _wait_for_readiness(port: int, process, expected_status: int) -> None:
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        _raise_if_stopped(process)
        try:
            if _readiness_status(port) == expected_status:
                return
        except OSError:
            pass
        time.sleep(0.05)
    raise RuntimeError(f"service readiness did not become HTTP {expected_status}")


def _readiness_status(port: int) -> int:
    return _request_json(port, "/readyz")[0]


def _request_json(port: int, path: str):
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        finally:
            error.close()


def _raise_if_stopped(process) -> None:
    if process.poll() is not None:
        stderr = process.stderr.read().strip() if process.stderr else ""
        raise RuntimeError(f"service stopped unexpectedly: {stderr}")


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": WORKFLOW_ID,
            "name": "Recurring scheduler smoke",
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
