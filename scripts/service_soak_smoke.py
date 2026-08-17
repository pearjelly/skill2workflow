#!/usr/bin/env python3
"""Exercise repeated service cutovers, trigger replay, and SQLite continuity."""

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
from typing import Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.service import SERVICE_SCHEMA_VERSION


SOAK_EVIDENCE_SCHEMA_VERSION = "skill2workflow-service-soak-evidence-0.1.0"
AUTH_TOKEN = "service-soak-smoke-token-0123456789abcdef"
DEFAULT_CYCLES = 3
DEFAULT_TRIGGERS_PER_CYCLE = 6
MAX_CYCLES = 8
MAX_TRIGGERS_PER_CYCLE = 32
MAX_TOTAL_TRIGGERS = 128
WORKFLOW_ID = "workflow_service_soak"
WORK_DIR_MARKER = ".skill2workflow-service-soak"


def run_soak(
    work_dir: Path,
    *,
    cycles: int = DEFAULT_CYCLES,
    triggers_per_cycle: int = DEFAULT_TRIGGERS_PER_CYCLE,
) -> Dict[str, object]:
    """Run a bounded, local-only service cutover drill and return redacted evidence."""

    _validate_options(cycles, triggers_per_cycle)
    work_dir = Path(work_dir).resolve()
    _reset_work_dir(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / WORK_DIR_MARKER).write_text(
        "skill2workflow service soak work directory\n", encoding="utf-8"
    )
    (work_dir / WORK_DIR_MARKER).chmod(0o644)

    state_dir = work_dir / "state"
    config_path = work_dir / "service.json"
    token_file = work_dir / "ingress.token"
    credential_dir = work_dir / "credentials"
    evidence_path = work_dir / "service-soak-smoke.json"
    port = _available_port()
    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
    token_file.chmod(0o600)
    credential_dir.mkdir(mode=0o700)
    credential_dir.chmod(0o700)
    config_path.write_text(
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
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    LocalControlPlane(state_dir, storage="sqlite").publish_workflow(_workflow())
    graceful_shutdowns = 0
    replay_checks = 0
    conflict_checks = 0
    health_checks = 0
    readiness_checks = 0
    no_stderr = True

    for cycle in range(1, cycles + 1):
        process = _start_service(config_path)
        try:
            _wait_until_ready(port, process)
            if _request_json(f"http://127.0.0.1:{port}/healthz")[1].get("status") != "ok":
                raise RuntimeError("service health check failed")
            health_checks += 1
            if _request_json(f"http://127.0.0.1:{port}/readyz")[1].get("status") != "ready":
                raise RuntimeError("service readiness check failed")
            readiness_checks += 1

            cycle_responses = []
            for sequence in range(1, triggers_per_cycle + 1):
                key = f"soak-cycle-{cycle:02d}-event-{sequence:03d}"
                status, response = _trigger(port, key)
                if status != 200 or response.get("run_status") != "completed":
                    raise RuntimeError("service soak trigger did not complete")
                cycle_responses.append((key, response))

            replay_key, replay_expected = cycle_responses[0]
            replay_status, replay_response = _trigger(port, replay_key)
            if replay_status != 200 or replay_response != replay_expected:
                raise RuntimeError("service soak idempotency replay changed the response")
            replay_checks += 1

            conflict_status, conflict_response = _trigger(
                port,
                replay_key,
                input_value={"cycle": cycle, "sequence": 1, "changed": True},
            )
            if conflict_status != 409 or conflict_response != {
                "error": "idempotency key conflicts with an existing request"
            }:
                raise RuntimeError("service soak idempotency conflict was not rejected")
            conflict_checks += 1
        finally:
            exit_code, stderr = _stop_service(process)
            graceful_shutdowns += int(exit_code == 0)
            no_stderr = no_stderr and not stderr.strip()
            if exit_code != 0:
                raise RuntimeError("service soak process did not exit cleanly")

        reloaded = LocalControlPlane(state_dir, storage="sqlite")
        runs = reloaded.list_runs()
        expected = cycle * triggers_per_cycle
        if len(runs) != expected or any(run.get("status") != "completed" for run in runs):
            raise RuntimeError("service soak state continuity check failed")

    final_control = LocalControlPlane(state_dir, storage="sqlite")
    final_runs = final_control.list_runs()
    total_triggers = cycles * triggers_per_cycle
    if len(final_runs) != total_triggers:
        raise RuntimeError("service soak final run count is inconsistent")

    # Re-open one short-lived service for read-only final diagnostics, then cut
    # it over cleanly once more. The checks therefore exercise both durable
    # continuity and the live authenticated diagnostic boundary.
    integrity_status = 0
    integrity: Dict[str, object] = {}
    consistency_status = 0
    consistency: Dict[str, object] = {}
    process = _start_service(config_path)
    try:
        _wait_until_ready(port, process)
        integrity_status, integrity = _request_json(
            f"http://127.0.0.1:{port}/api/v1/audit-integrity",
            token=AUTH_TOKEN,
        )
        consistency_status, consistency = _request_json(
            f"http://127.0.0.1:{port}/api/v1/audit-consistency",
            token=AUTH_TOKEN,
        )
    finally:
        exit_code, stderr = _stop_service(process)
        graceful_shutdowns += int(exit_code == 0)
        no_stderr = no_stderr and not stderr.strip()
        if exit_code != 0:
            raise RuntimeError("service soak final cutover did not exit cleanly")

    checks = {
        "health_checks": health_checks == cycles,
        "readiness_checks": readiness_checks == cycles,
        "graceful_sigterm": graceful_shutdowns == cycles + 1,
        "sqlite_state_continuity": len(final_runs) == total_triggers,
        "all_runs_completed": all(run.get("status") == "completed" for run in final_runs),
        "idempotency_replay": replay_checks == cycles,
        "idempotency_conflict": conflict_checks == cycles,
        "audit_integrity": integrity_status == 200 and integrity.get("status") == "valid",
        "audit_consistency": consistency_status == 200 and consistency.get("status") == "clean",
        "no_stderr": no_stderr,
    }
    evidence = {
        "schema_version": SOAK_EVIDENCE_SCHEMA_VERSION,
        "status": "passed" if all(checks.values()) else "failed",
        "cycles": cycles,
        "triggers_per_cycle": triggers_per_cycle,
        "total_triggers": total_triggers,
        "restarts": cycles + 1,
        "persisted_run_count": len(final_runs),
        "checks": checks,
    }
    _write_evidence(evidence_path, evidence)
    return evidence


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    parser.add_argument("--triggers-per-cycle", type=int, default=DEFAULT_TRIGGERS_PER_CYCLE)
    args = parser.parse_args(argv)
    try:
        evidence = run_soak(
            args.work_dir,
            cycles=args.cycles,
            triggers_per_cycle=args.triggers_per_cycle,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if evidence["status"] == "passed" else 1


def _validate_options(cycles: int, triggers_per_cycle: int) -> None:
    for label, value, maximum in (
        ("cycles", cycles, MAX_CYCLES),
        ("triggers_per_cycle", triggers_per_cycle, MAX_TRIGGERS_PER_CYCLE),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValueError(f"{label} must be an integer from 1 through {maximum}")
    if cycles * triggers_per_cycle > MAX_TOTAL_TRIGGERS:
        raise ValueError(
            "cycles multiplied by triggers_per_cycle must not exceed "
            f"{MAX_TOTAL_TRIGGERS}"
        )


def _reset_work_dir(work_dir: Path) -> None:
    if work_dir == ROOT or ROOT in work_dir.parents:
        raise ValueError("service soak work_dir must be outside the repository")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("service soak work_dir cannot be a filesystem root")
    if not work_dir.exists():
        return
    if work_dir.is_symlink() or not work_dir.is_dir():
        raise ValueError("service soak work_dir must be a dedicated directory")
    marker = work_dir / WORK_DIR_MARKER
    try:
        marker_value = marker.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError("service soak work_dir must contain its safety marker") from error
    if marker_value != "skill2workflow service soak work directory\n":
        raise ValueError("service soak work_dir must contain its safety marker")
    shutil.rmtree(work_dir)


def _start_service(config_path: Path):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(SRC) + (
        os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else ""
    )
    return subprocess.Popen(
        [sys.executable, "-m", "skill2workflow.cli", "service", "--config", str(config_path)],
        cwd=str(ROOT),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _stop_service(process) -> Tuple[int, str]:
    if process.poll() is None:
        process.terminate()
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
        raise RuntimeError("service soak process did not stop after SIGTERM")
    del stdout
    return int(process.returncode), stderr or ""


def _wait_until_ready(port: int, process) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read().strip() if process.stderr else ""
            raise RuntimeError(f"service stopped before readiness: {stderr}")
        try:
            status, payload = _request_json(f"http://127.0.0.1:{port}/readyz")
            if status == 200 and payload.get("status") == "ready":
                return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.05)
    raise RuntimeError("service readiness timed out")


def _trigger(port: int, idempotency_key: str, *, input_value=None):
    payload = {
        "source": "service-soak-smoke",
        "idempotency_key": idempotency_key,
        "input": input_value or {"purpose": "bounded-soak"},
    }
    return _request_json(
        f"http://127.0.0.1:{port}/webhooks/{WORKFLOW_ID}/0.1.0",
        method="POST",
        payload=payload,
        token=AUTH_TOKEN,
    )


def _request_json(url: str, method: str = "GET", payload=None, token: Optional[str] = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
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


def _write_evidence(path: Path, evidence: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o644)


def _workflow() -> Dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": WORKFLOW_ID,
            "name": "Service soak continuity",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }


if __name__ == "__main__":
    raise SystemExit(main())
