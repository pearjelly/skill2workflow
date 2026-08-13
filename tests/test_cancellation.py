import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.executor import LocalExecutor
from skill2workflow.service import RuntimeService, ServiceConfig


AUTH_TOKEN = "loop48-cancellation-bearer-token-0123456789abcdef"


class CancellationTests(TestCase):
    def test_real_process_smoke_proves_concurrent_and_durable_cancellation(self):
        with TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/cancellation_smoke.py",
                    "--work-dir",
                    str(Path(tmp) / "smoke"),
                ],
                cwd=str(Path(__file__).resolve().parents[1]),
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertTrue(evidence["checks"]["concurrent_request_persisted"])
        self.assertTrue(evidence["checks"]["external_attempt_recorded"])
        self.assertTrue(evidence["checks"]["successor_suppressed"])
        self.assertTrue(evidence["checks"]["waiting_cancel_immediate"])
        self.assertTrue(evidence["checks"]["compact_audit"])

    def test_waiting_run_cancellation_is_terminal_idempotent_and_not_resumable(self):
        for storage in ("json", "sqlite"):
            with self.subTest(storage=storage), TemporaryDirectory() as tmp:
                executor = LocalExecutor(Path(tmp), storage=storage)
                waiting = executor.run(_waiting_workflow())

                first = executor.cancel(waiting["run_id"])
                second = executor.cancel(waiting["run_id"])

                self.assertEqual(first["status"], "cancelled")
                self.assertEqual(second["status"], "cancelled")
                self.assertEqual(
                    [event["type"] for event in second["events"]].count("run_cancel_requested"),
                    1,
                )
                self.assertEqual(
                    [event["type"] for event in second["events"]].count("run_cancelled"),
                    1,
                )
                with self.assertRaisesRegex(ValueError, "not waiting"):
                    executor.resume(waiting["run_id"])

    def test_completed_and_failed_runs_reject_cancellation(self):
        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp), storage="sqlite")
            completed = executor.run(_completed_workflow())

            with self.assertRaisesRegex(ValueError, "already completed"):
                executor.cancel(completed["run_id"])

    def test_stale_active_save_cannot_overwrite_a_waiting_cancellation(self):
        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp), storage="sqlite")
            waiting = executor.run(_waiting_workflow())
            stale = executor.get_run(waiting["run_id"])

            executor.cancel(waiting["run_id"])
            stale["status"] = "running"
            stale["current_node"] = "end"
            executor.store.save(stale)
            persisted = executor.get_run(waiting["run_id"])

        self.assertEqual(stale["status"], "cancelled")
        self.assertEqual(persisted["status"], "cancelled")

    def test_running_connector_finishes_but_successor_never_starts_after_cancel(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            runtime = _BlockingRuntime()
            executor = LocalExecutor(
                state_dir,
                storage="sqlite",
                connector_runtime=runtime,
            )
            result = {}
            thread = threading.Thread(
                target=lambda: result.update(executor.run(_connector_workflow())),
                daemon=True,
            )
            thread.start()
            self.assertTrue(runtime.started.wait(timeout=2))

            requested = LocalExecutor(state_dir, storage="sqlite").cancel(
                runtime.run_id
            )
            runtime.release.set()
            thread.join(timeout=3)

            self.assertEqual(requested["status"], "cancel_requested")
            self.assertEqual(result["status"], "cancelled")
            self.assertIn("call", result["node_results"])
            self.assertNotIn("end", result["node_results"])
            self.assertFalse(thread.is_alive())

    def test_cancellation_requested_by_failed_attempt_prevents_retry(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            runtime = _CancelOnFirstAttemptRuntime(state_dir)
            executor = LocalExecutor(
                state_dir,
                storage="sqlite",
                connector_runtime=runtime,
            )

            result = executor.run(_connector_workflow(retries=3))

            self.assertEqual(result["status"], "cancelled")
            self.assertEqual(runtime.attempts, 1)
            self.assertNotIn("node_retrying", [event["type"] for event in result["events"]])

    def test_control_plane_writes_compact_cancellation_audit_once(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_waiting_workflow())
            waiting = control.run_published_workflow("workflow_cancel", "0.1.0")

            first = control.cancel_published_run(waiting["run_id"])
            second = control.cancel_published_run(waiting["run_id"])
            events = control.list_audit_events(run_id=waiting["run_id"])

            self.assertEqual(first["status"], "cancelled")
            self.assertEqual(second["status"], "cancelled")
            self.assertEqual(
                [event["type"] for event in events].count("run_cancel_requested"),
                1,
            )
            self.assertEqual(
                [event["type"] for event in events].count("run_cancelled"),
                1,
            )
            self.assertNotIn("reason", json.dumps(events))

    def test_control_plane_retries_cancellation_to_reconcile_audit_after_state_commit(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_waiting_workflow())
            waiting = control.run_published_workflow("workflow_cancel", "0.1.0")

            with patch(
                "skill2workflow.storage._append_audit_connection",
                side_effect=RuntimeError("audit append failed"),
            ):
                with self.assertRaisesRegex(RuntimeError, "audit append failed"):
                    control.cancel_published_run(waiting["run_id"])

            retried = control.cancel_published_run(waiting["run_id"])
            events = control.list_audit_events(run_id=waiting["run_id"])
            report = control.inspect_run_audit(run_id=waiting["run_id"])

        self.assertEqual(retried["status"], "cancelled")
        self.assertEqual(
            [event["type"] for event in events],
            ["run_started", "run_waiting", "run_cancel_requested", "run_cancelled"],
        )
        self.assertEqual(report["status"], "clean")

    def test_authenticated_service_route_cancels_waiting_run(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            token_file = root / "auth.token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            credential_dir = root / "credentials"
            credential_dir.mkdir()
            credential_dir.chmod(0o700)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_waiting_workflow())
            control.publish_workflow(_completed_workflow())
            waiting = control.run_published_workflow("workflow_cancel", "0.1.0")
            completed = control.run_published_workflow("workflow_completed", "0.1.0")
            service = RuntimeService(
                ServiceConfig(
                    host="127.0.0.1",
                    port=0,
                    state_dir=state_dir,
                    storage="sqlite",
                    auth_token_file=token_file,
                    credential_dir=credential_dir,
                )
            )
            thread = threading.Thread(target=service.serve, daemon=True)
            thread.start()
            host, port = service.server_address
            url = f"http://{host}:{port}/runs/{waiting['run_id']}/cancel"
            try:
                denied_status, _ = _post(url)
                bad_body_status, _ = _post(
                    url, token=AUTH_TOKEN, payload={"reason": "must not persist"}
                )
                accepted_status, accepted = _post(url, token=AUTH_TOKEN)
                missing_status, _ = _post(
                    f"http://{host}:{port}/runs/run_missing123/cancel",
                    token=AUTH_TOKEN,
                )
                terminal_status, _ = _post(
                    f"http://{host}:{port}/runs/{completed['run_id']}/cancel",
                    token=AUTH_TOKEN,
                )
            finally:
                service.begin_shutdown()
                thread.join(timeout=3)

            self.assertEqual(denied_status, 401)
            self.assertEqual(bad_body_status, 400)
            self.assertEqual(accepted_status, 200)
            self.assertEqual(missing_status, 404)
            self.assertEqual(terminal_status, 409)
            self.assertEqual(accepted["status"], "cancelled")
            self.assertEqual(accepted["run_id"], waiting["run_id"])

    def test_authenticated_cancel_retry_repairs_audit_after_service_503(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            token_file = root / "auth.token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            credential_dir = root / "credentials"
            credential_dir.mkdir()
            credential_dir.chmod(0o700)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_waiting_workflow())
            waiting = control.run_published_workflow("workflow_cancel", "0.1.0")
            service = RuntimeService(
                ServiceConfig(
                    host="127.0.0.1",
                    port=0,
                    state_dir=state_dir,
                    storage="sqlite",
                    auth_token_file=token_file,
                    credential_dir=credential_dir,
                )
            )
            thread = threading.Thread(target=service.serve, daemon=True)
            thread.start()
            host, port = service.server_address
            url = f"http://{host}:{port}/runs/{waiting['run_id']}/cancel"
            try:
                with patch.object(
                    service.control_plane,
                    "_append_missing_audit_events",
                    side_effect=RuntimeError("audit append failed"),
                ):
                    failed_status, failed = _post(url, token=AUTH_TOKEN)
                retried_status, retried = _post(url, token=AUTH_TOKEN)
            finally:
                service.begin_shutdown()
                thread.join(timeout=3)

            report = LocalControlPlane(state_dir, storage="sqlite").inspect_run_audit(
                run_id=waiting["run_id"]
            )

        self.assertEqual(failed_status, 503)
        self.assertEqual(failed, {"error": "service unavailable"})
        self.assertEqual(retried_status, 200)
        self.assertEqual(retried["status"], "cancelled")
        self.assertEqual(report["status"], "clean")
        self.assertFalse(thread.is_alive())


class _BlockingRuntime:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.run_id = ""

    def execute_connector(self, _node, credential_provider=None, context=None):
        self.run_id = str(context["_execution"]["run_id"])
        self.started.set()
        if not self.release.wait(timeout=3):
            raise AssertionError("test connector was not released")
        return {"status": "completed", "output": {}, "audit": {}}


class _CancelOnFirstAttemptRuntime:
    def __init__(self, state_dir):
        self.state_dir = state_dir
        self.attempts = 0

    def execute_connector(self, _node, credential_provider=None, context=None):
        self.attempts += 1
        LocalExecutor(self.state_dir, storage="sqlite").cancel(
            str(context["_execution"]["run_id"])
        )
        return {"status": "failed", "error": "synthetic failure", "output": {}}


def _post(url, token="", payload=None):
    body = {} if payload is None else payload
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        finally:
            error.close()


def _waiting_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_cancel",
            "name": "Cancellation",
            "version": "0.1.0",
            "status": "published",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "on_success": "review"},
            {
                "id": "review",
                "type": "human_gate",
                "connector": {"id": "manual", "kind": "manual"},
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure"},
            {"id": "end", "type": "end"},
        ],
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
            {"id": "edge_review_end", "from": "review", "to": "end", "label": "approved"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "rejected"},
        ],
    }


def _completed_workflow():
    workflow = _waiting_workflow()
    workflow["workflow"]["id"] = "workflow_completed"
    workflow["nodes"] = [
        {"id": "start", "type": "start", "on_success": "end"},
        {"id": "end", "type": "end"},
    ]
    workflow["edges"] = [
        {"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}
    ]
    return workflow


def _connector_workflow(retries=0):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_connector_cancel",
            "name": "Connector cancellation",
            "version": "0.1.0",
            "status": "published",
            "policies": {"default_retry": {"max_attempts": retries}},
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "on_success": "call"},
            {
                "id": "call",
                "type": "tool_call",
                "connector": {"id": "synthetic", "kind": "synthetic"},
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure"},
            {"id": "end", "type": "end"},
        ],
        "edges": [
            {"id": "edge_start_call", "from": "start", "to": "call", "label": "next"},
            {"id": "edge_call_end", "from": "call", "to": "end", "label": "success"},
            {"id": "edge_call_failure", "from": "call", "to": "failure", "label": "failure"},
        ],
    }
