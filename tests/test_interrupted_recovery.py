import json
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.request
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.schedules import RecurringScheduleStore
from skill2workflow.service import RuntimeService, ServiceScheduleLoop
from skill2workflow.storage import SqliteRunStore
from skill2workflow.telemetry import RuntimeTelemetry


class _BlockingConnectorRuntime:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def execute_connector(self, node, credential_provider=None, context=None):
        self.calls += 1
        self.started.set()
        if not self.release.wait(timeout=5):
            raise RuntimeError("test connector timed out")
        return {
            "status": "completed",
            "connector": {"id": "blocking", "kind": "local"},
            "output": {},
        }


class _RecordingConnectorRuntime:
    def __init__(self):
        self.calls = []

    def execute_connector(self, node, credential_provider=None, context=None):
        self.calls.append(str(node.get("id", "")))
        return {
            "status": "completed",
            "connector": {"id": "recording", "kind": "local"},
            "output": {},
        }


class InterruptedRunRecoveryTests(TestCase):
    def test_real_process_crash_smoke_proves_takeover_without_replay(self):
        with TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/interrupted_recovery_smoke.py",
                    "--work-dir",
                    str(Path(tmp) / "smoke"),
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertTrue(all(evidence["checks"].values()))
        self.assertEqual(evidence["provider_attempts"], 1)
        self.assertEqual(evidence["successor_attempts"], 0)

    def test_takeover_marks_foreign_active_run_interrupted_and_fences_old_writer(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            runtime = _BlockingConnectorRuntime()
            active = LocalControlPlane(
                state_dir,
                storage="sqlite",
                connector_runtime=runtime,
                execution_owner="service-owner-a",
            )
            active.publish_workflow(_tool_workflow())
            outcome = {}

            def execute():
                try:
                    outcome["state"] = active.run_published_workflow(
                        "workflow_interrupted", "0.1.0"
                    )
                except Exception as error:  # the old writer must be fenced
                    outcome["error"] = error

            worker = threading.Thread(target=execute, daemon=True)
            worker.start()
            self.assertTrue(runtime.started.wait(timeout=2))
            run_id = active.list_runs()[0]["run_id"]

            takeover = LocalControlPlane(
                state_dir,
                storage="sqlite",
                execution_owner="service-owner-b",
            )
            self.assertEqual(takeover.recover_interrupted_runs(), 1)
            self.assertEqual(takeover.recover_interrupted_runs(), 0)
            interrupted = takeover.get_run(run_id)
            with self.assertRaisesRegex(ValueError, "already interrupted"):
                takeover.cancel_published_run(run_id)

            runtime.release.set()
            worker.join(timeout=2)
            durable = takeover.get_run(run_id)
            interruption_audit = takeover.list_audit_events(
                run_id=run_id, event_type="run_interrupted"
            )

        self.assertEqual(interrupted["status"], "interrupted")
        self.assertEqual(durable["status"], "interrupted")
        self.assertEqual(
            [event["type"] for event in durable["events"]].count("run_interrupted"),
            1,
        )
        self.assertIn(
            "connector_started", [event["type"] for event in durable["events"]]
        )
        self.assertEqual(len(interruption_audit), 1)
        self.assertNotIn("owner_id", interruption_audit[0])
        self.assertIn("execution ownership was fenced", str(outcome["error"]))
        self.assertEqual(runtime.calls, 1)

    def test_interrupted_takeover_accepts_a_bounded_write_batch(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            store = SqliteRunStore(state_dir)
            for index in range(2):
                store.start_execution(
                    {
                        "run_id": f"run_batch_{index}",
                        "workflow_id": "workflow_batch",
                        "workflow_version": "0.1.0",
                        "status": "running",
                        "current_node": "start",
                        "context": {},
                        "node_results": {},
                        "events": [],
                        "workflow": {},
                    },
                    "service-owner-a",
                    f"execution_batch_{index}",
                )
            takeover = LocalControlPlane(
                state_dir,
                storage="sqlite",
                execution_owner="service-owner-b",
            )

            first, first_processed = takeover.executor.recover_interrupted_runs_batch(1)
            second, second_processed = takeover.executor.recover_interrupted_runs_batch(1)
            empty, empty_processed = takeover.executor.recover_interrupted_runs_batch(1)
            states = [takeover.get_run(f"run_batch_{index}") for index in range(2)]

        self.assertEqual(len(first), 1)
        self.assertEqual(first_processed, 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(second_processed, 1)
        self.assertEqual(empty, [])
        self.assertEqual(empty_processed, 0)
        self.assertEqual([state["status"] for state in states], ["interrupted", "interrupted"])

    def test_interrupted_audit_reconciliation_accepts_a_bounded_cursor_batch(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            store = SqliteRunStore(state_dir)
            for index in range(2):
                store.save(
                    {
                        "run_id": f"run_reconcile_{index}",
                        "workflow_id": "workflow_reconcile",
                        "workflow_version": "0.1.0",
                        "status": "interrupted",
                        "current_node": "start",
                        "context": {},
                        "node_results": {},
                        "events": [
                            {
                                "type": "run_interrupted",
                                "node_id": "start",
                                "timestamp": f"2026-08-14T00:00:0{index}Z",
                            }
                        ],
                        "workflow": {},
                    }
                )
            control = LocalControlPlane(state_dir, storage="sqlite")

            first = control.reconcile_interrupted_run_audits_batch(1)
            second = control.reconcile_interrupted_run_audits_batch(
                1, after_run_id=first[2]
            )
            empty = control.reconcile_interrupted_run_audits_batch(
                1, after_run_id=second[2]
            )
            events = control.list_audit_events(event_type="run_interrupted")

        self.assertEqual(first, (1, 1, "run_reconcile_0"))
        self.assertEqual(second, (1, 1, "run_reconcile_1"))
        self.assertEqual(empty, (0, 0, "run_reconcile_1"))
        self.assertEqual(len(events), 2)

    def test_recovery_reconciliation_does_not_enumerate_full_runs_or_audit(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            runtime = _BlockingConnectorRuntime()
            active = LocalControlPlane(
                state_dir,
                storage="sqlite",
                connector_runtime=runtime,
                execution_owner="service-owner-a",
            )
            active.publish_workflow(_tool_workflow())
            outcome = {}

            def execute():
                try:
                    active.run_published_workflow(
                        "workflow_interrupted", "0.1.0"
                    )
                except Exception as error:
                    outcome["error"] = error

            worker = threading.Thread(
                target=execute,
                daemon=True,
            )
            worker.start()
            self.assertTrue(runtime.started.wait(timeout=2))
            takeover = LocalControlPlane(
                state_dir,
                storage="sqlite",
                execution_owner="service-owner-b",
            )
            original_audit = takeover.list_audit_events
            original_runs = takeover.executor.list_runs
            takeover.list_audit_events = lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("recovery loaded the full audit history")
            )
            takeover.executor.list_runs = lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("recovery loaded the full run table")
            )
            try:
                self.assertEqual(takeover.recover_interrupted_runs(), 1)
            finally:
                takeover.list_audit_events = original_audit
                takeover.executor.list_runs = original_runs
                runtime.release.set()
                worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertIn("execution ownership was fenced", str(outcome["error"]))

    def test_fenced_old_owner_cannot_start_the_next_connector(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            runtime = _RecordingConnectorRuntime()
            active = LocalControlPlane(
                state_dir,
                storage="sqlite",
                connector_runtime=runtime,
                execution_owner="service-owner-a",
            )
            active.publish_workflow(_two_connector_workflow())
            successor_persisted = threading.Event()
            release_old_owner = threading.Event()
            outcome = {}
            original_save = active.executor._save

            def pause_after_successor_persisted(state):
                original_save(state)
                if (
                    state.get("status") == "running"
                    and state.get("current_node") == "second"
                ):
                    successor_persisted.set()
                    release_old_owner.wait(timeout=5)

            active.executor._save = pause_after_successor_persisted

            def execute():
                try:
                    active.run_published_workflow(
                        "workflow_two_connectors", "0.1.0"
                    )
                except Exception as error:
                    outcome["error"] = error

            worker = threading.Thread(target=execute, daemon=True)
            worker.start()
            self.assertTrue(successor_persisted.wait(timeout=2))
            takeover = LocalControlPlane(
                state_dir,
                storage="sqlite",
                execution_owner="service-owner-b",
            )
            self.assertEqual(takeover.recover_interrupted_runs(), 1)
            release_old_owner.set()
            worker.join(timeout=2)
            durable = takeover.list_runs()[0]

        self.assertEqual(runtime.calls, ["first"])
        self.assertEqual(durable["status"], "interrupted")
        self.assertIn("execution ownership was fenced", str(outcome["error"]))

    def test_waiting_current_owner_and_ownerless_runs_are_not_recovered(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            active = LocalControlPlane(
                state_dir,
                storage="sqlite",
                execution_owner="service-owner-a",
            )
            active.publish_workflow(_waiting_workflow())
            waiting = active.run_published_workflow("workflow_waiting", "0.1.0")
            same_owner = LocalControlPlane(
                state_dir,
                storage="sqlite",
                execution_owner="service-owner-a",
            )
            takeover = LocalControlPlane(
                state_dir,
                storage="sqlite",
                execution_owner="service-owner-b",
            )

            self.assertEqual(same_owner.recover_interrupted_runs(), 0)
            self.assertEqual(takeover.recover_interrupted_runs(), 0)
            self.assertEqual(takeover.get_run(waiting["run_id"])["status"], "waiting")

            runtime = _BlockingConnectorRuntime()
            local = LocalControlPlane(
                state_dir,
                storage="sqlite",
                connector_runtime=runtime,
            )
            local.publish_workflow(_tool_workflow("workflow_ownerless"))
            worker = threading.Thread(
                target=lambda: local.run_published_workflow(
                    "workflow_ownerless", "0.1.0"
                ),
                daemon=True,
            )
            worker.start()
            self.assertTrue(runtime.started.wait(timeout=2))
            self.assertEqual(takeover.recover_interrupted_runs(), 0)
            runtime.release.set()
            worker.join(timeout=2)

        self.assertFalse(worker.is_alive())

    def test_takeover_repairs_missing_control_audit_after_mid_recovery_crash(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            runtime = _BlockingConnectorRuntime()
            active = LocalControlPlane(
                state_dir,
                storage="sqlite",
                connector_runtime=runtime,
                execution_owner="service-owner-a",
            )
            active.publish_workflow(_tool_workflow())
            outcome = {}

            def execute():
                try:
                    active.run_published_workflow(
                        "workflow_interrupted", "0.1.0"
                    )
                except Exception as error:
                    outcome["error"] = error

            worker = threading.Thread(target=execute, daemon=True)
            worker.start()
            self.assertTrue(runtime.started.wait(timeout=2))
            run_id = active.list_runs()[0]["run_id"]
            takeover = LocalControlPlane(
                state_dir,
                storage="sqlite",
                execution_owner="service-owner-b",
            )

            recovered = takeover.executor.recover_interrupted_runs()
            self.assertEqual(len(recovered), 1)
            self.assertEqual(
                takeover.list_audit_events(
                    run_id=run_id, event_type="run_interrupted"
                ),
                [],
            )
            self.assertEqual(takeover.recover_interrupted_runs(), 0)
            audit = takeover.list_audit_events(
                run_id=run_id, event_type="run_interrupted"
            )
            runtime.release.set()
            worker.join(timeout=2)

        self.assertEqual(len(audit), 1)
        self.assertIn("execution ownership was fenced", str(outcome["error"]))

    def test_service_and_scheduler_share_one_execution_owner(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _service_config(root)
            service = RuntimeService(config)
            try:
                owner = service.scheduler.dispatcher.owner_id
                self.assertEqual(service.control_plane.executor.execution_owner, owner)
                self.assertEqual(
                    service.scheduler.dispatcher.control_plane.executor.execution_owner,
                    owner,
                )
                self.assertFalse(service._server.daemon_threads)
                self.assertTrue(service._server.block_on_close)
            finally:
                service._server.server_close()

    def test_graceful_drain_keeps_lease_until_inflight_request_finishes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _service_config(root)
            first = RuntimeService(config)
            runtime = _BlockingConnectorRuntime()
            first.control_plane.executor.connector_runtime = runtime
            first.control_plane.publish_workflow(_tool_workflow())
            first_ready = threading.Event()
            first_thread = threading.Thread(
                target=first.serve,
                kwargs={"ready_callback": lambda _service: first_ready.set()},
                daemon=True,
            )
            first_thread.start()
            self.assertTrue(first_ready.wait(timeout=2))
            host, port = first.server_address
            request_outcome = {}

            def trigger():
                request = urllib.request.Request(
                    f"http://{host}:{port}/webhooks/workflow_interrupted/0.1.0",
                    data=json.dumps(
                        {
                            "source": "graceful-drain-test",
                            "idempotency_key": "drain-001",
                        }
                    ).encode("utf-8"),
                    headers={
                        "Authorization": "Bearer " + "t" * 32,
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(request, timeout=5) as response:
                        request_outcome["status"] = response.status
                except Exception as error:
                    request_outcome["error"] = error

            request_thread = threading.Thread(target=trigger, daemon=True)
            request_thread.start()
            self.assertTrue(runtime.started.wait(timeout=2))
            first.begin_shutdown()

            second = RuntimeService(config)
            second_ready = threading.Event()
            second_thread = threading.Thread(
                target=second.serve,
                kwargs={"ready_callback": lambda _service: second_ready.set()},
                daemon=True,
            )
            second_thread.start()
            self.assertTrue(second_ready.wait(timeout=2))
            time.sleep(0.3)
            self.assertTrue(first_thread.is_alive())
            self.assertEqual(second.readiness()[0], 503)

            runtime.release.set()
            request_thread.join(timeout=2)
            first_thread.join(timeout=3)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and second.readiness()[0] != 200:
                time.sleep(0.05)
            run = second.control_plane.list_runs()[0]
            interruption_audit = second.control_plane.list_audit_events(
                run_id=run["run_id"], event_type="run_interrupted"
            )
            second.begin_shutdown()
            second_thread.join(timeout=3)

        self.assertEqual(request_outcome.get("status"), 200)
        self.assertEqual(run["status"], "completed")
        self.assertEqual(interruption_audit, [])
        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())

    def test_interrupted_status_is_exported_as_fixed_metric(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            runtime = _BlockingConnectorRuntime()
            active = LocalControlPlane(
                state_dir,
                storage="sqlite",
                connector_runtime=runtime,
                execution_owner="service-owner-a",
            )
            active.publish_workflow(_tool_workflow())
            outcome = {}

            def execute():
                try:
                    active.run_published_workflow(
                        "workflow_interrupted", "0.1.0"
                    )
                except Exception as error:
                    outcome["error"] = error

            worker = threading.Thread(
                target=execute,
                daemon=True,
            )
            worker.start()
            self.assertTrue(runtime.started.wait(timeout=2))
            takeover = LocalControlPlane(
                state_dir,
                storage="sqlite",
                execution_owner="service-owner-b",
            )
            self.assertEqual(takeover.recover_interrupted_runs(), 1)
            RecurringScheduleStore(state_dir)
            rendered = RuntimeTelemetry(state_dir).render(
                service_status="ready",
                ready=True,
                scheduler_lease_owned=True,
            )
            runtime.release.set()
            worker.join(timeout=2)

        self.assertIn('skill2workflow_runs{status="interrupted"} 1', rendered)
        self.assertIn("execution ownership was fenced", str(outcome["error"]))

    def test_scheduler_runs_recovery_only_after_it_acquires_the_lease(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            first = ServiceScheduleLoop(state_dir)
            second = ServiceScheduleLoop(state_dir)
            recovered = threading.Event()
            calls = []
            original = second.dispatcher.control_plane.recover_interrupted_runs_batch

            def record_recovery(*, max_items):
                calls.append("recovered")
                recovered.set()
                return original(max_items=max_items)

            second.dispatcher.control_plane.recover_interrupted_runs_batch = record_recovery
            first.start()
            second.start()
            try:
                time.sleep(0.25)
                self.assertEqual(calls, [])
                first.stop()
                self.assertTrue(recovered.wait(timeout=2))
            finally:
                if first._heartbeat_thread and first._heartbeat_thread.is_alive():
                    first.stop()
                second.stop()

    def test_backup_preserves_and_strictly_validates_execution_ledger(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            control = LocalControlPlane(
                state_dir,
                storage="sqlite",
                execution_owner="service-owner-a",
            )
            control.publish_workflow(_waiting_workflow())
            waiting = control.run_published_workflow("workflow_waiting", "0.1.0")
            RecurringScheduleStore(state_dir)
            backup = root / "backup"
            restored = root / "restored"

            create_state_backup(state_dir, backup)
            verify_state_backup(backup)
            restore_state_backup(backup, restored)
            with closing(sqlite3.connect(restored / "runs.sqlite3")) as connection, connection:
                row = connection.execute(
                    "select status from run_executions where run_id = ?",
                    (waiting["run_id"],),
                ).fetchone()

            with closing(sqlite3.connect(state_dir / "runs.sqlite3")) as connection, connection:
                connection.execute("drop table run_executions")
                connection.execute("create table run_executions (run_id text)")
                connection.commit()
            with self.assertRaisesRegex(ValueError, "incompatible layout"):
                inspect_state_backup_readiness(state_dir, require_stopped=False)

            with closing(sqlite3.connect(state_dir / "runs.sqlite3")) as connection, connection:
                connection.execute("drop table run_executions")
                connection.execute(
                    """
                    create table run_executions (
                        run_id text, owner_id text, execution_id text,
                        status text, claimed_at text, updated_at text
                    )
                    """
                )
                connection.execute(
                    "insert into run_executions values (?, ?, ?, ?, ?, ?)",
                    (
                        "missing-run",
                        "",
                        "",
                        "invalid",
                        "",
                        "",
                    ),
                )
                connection.commit()
            with self.assertRaisesRegex(ValueError, "execution ledger"):
                inspect_state_backup_readiness(state_dir, require_stopped=False)

        self.assertEqual(row, ("released",))


def _tool_workflow(workflow_id="workflow_interrupted"):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": workflow_id,
            "name": "Interrupted recovery",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "call",
        "nodes": [
            {
                "id": "call",
                "type": "tool_call",
                "title": "Call connector",
                "connector": {"id": "blocking", "kind": "local"},
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "end", "type": "end", "title": "Done"},
            {"id": "failure", "type": "failure", "title": "Failed"},
        ],
        "edges": [
            {"id": "edge_call_end", "from": "call", "to": "end", "label": "next"},
            {
                "id": "edge_call_failure",
                "from": "call",
                "to": "failure",
                "label": "failure",
            },
        ],
    }


def _two_connector_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_two_connectors",
            "name": "Two connector fencing",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "first",
        "nodes": [
            {
                "id": "first",
                "type": "tool_call",
                "connector": {"id": "recording", "kind": "local"},
                "on_success": "second",
                "on_failure": "failure",
            },
            {
                "id": "second",
                "type": "tool_call",
                "connector": {"id": "recording", "kind": "local"},
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "end", "type": "end"},
            {"id": "failure", "type": "failure"},
        ],
        "edges": [
            {"id": "edge_first_second", "from": "first", "to": "second", "label": "next"},
            {"id": "edge_first_failure", "from": "first", "to": "failure", "label": "failure"},
            {"id": "edge_second_end", "from": "second", "to": "end", "label": "next"},
            {"id": "edge_second_failure", "from": "second", "to": "failure", "label": "failure"},
        ],
    }


def _waiting_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_waiting",
            "name": "Waiting recovery",
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
            {
                "id": "edge_review_failure",
                "from": "review",
                "to": "failure",
                "label": "failure",
            },
        ],
    }


def _service_config(root: Path):
    from skill2workflow.service import ServiceConfig

    token = root / "auth-token"
    token.write_text("t" * 32, encoding="utf-8")
    token.chmod(0o600)
    credentials = root / "credentials"
    credentials.mkdir()
    credentials.chmod(0o700)
    state = root / "state"
    state.mkdir()
    state.chmod(0o700)
    return ServiceConfig(
        host="127.0.0.1",
        port=0,
        state_dir=state,
        storage="sqlite",
        auth_token_file=token,
        credential_dir=credentials,
    )
from skill2workflow.backup import (
    create_state_backup,
    inspect_state_backup_readiness,
    restore_state_backup,
    verify_state_backup,
)
