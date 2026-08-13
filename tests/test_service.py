import json
import http.client
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.service import (
    SERVICE_SCHEMA_VERSION,
    FileBearerTokenAuthenticator,
    MAX_AUTH_TOKEN_BYTES,
    MAX_CONCURRENT_BUSINESS_REQUESTS,
    MAX_LIVE_CONTROL_SNAPSHOT_BYTES,
    MAX_AUDIT_CONSISTENCY_RESPONSE_BYTES,
    MAX_AUDIT_INTEGRITY_RESPONSE_BYTES,
    MAX_RUNTIME_INFO_RESPONSE_BYTES,
    RuntimeService,
    ServiceScheduleLoop,
    ServiceConfig,
    load_service_config,
    serve_runtime_service,
)
from skill2workflow.schedules import RecurringScheduleDispatcher, RecurringScheduleStore
from skill2workflow.service_client import (
    ServiceActionError,
    post_workflow_release,
    post_workflow_promotion,
    post_workflow_deprecation,
    fetch_workflow_inventory,
    fetch_operational_readiness,
    fetch_workflow_diff,
    post_workflow_trigger,
)
from skill2workflow.service_bootstrap import rotate_service_token


AUTH_TOKEN = "loop42-test-bearer-token-0123456789abcdef"


class ServiceConfigTests(TestCase):
    def test_load_service_config_accepts_explicit_loopback_sqlite_configuration(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "service.json"
            state_dir = root / "state"
            token_file = root / "ingress.token"
            credential_dir = root / "credentials"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": SERVICE_SCHEMA_VERSION,
                        "service": {"host": "127.0.0.1", "port": 8080},
                        "runtime": {"state_dir": str(state_dir), "storage": "sqlite"},
                        "auth": {
                            "provider": "bearer_token_file",
                            "token_file": str(token_file),
                        },
                        "credentials": {
                            "provider": "directory",
                            "directory": str(credential_dir),
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = load_service_config(config_path)

        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 8080)
        self.assertEqual(config.state_dir, state_dir)
        self.assertEqual(config.storage, "sqlite")
        self.assertEqual(config.auth_token_file, token_file)
        self.assertEqual(config.credential_dir, credential_dir)

    def test_load_service_config_rejects_unversioned_non_loopback_or_json_runtime(self):
        invalid_configs = [
            {
                "service": {"host": "127.0.0.1", "port": 8080},
                "runtime": {"state_dir": "/tmp/state", "storage": "sqlite"},
            },
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "0.0.0.0", "port": 8080},
                "runtime": {"state_dir": "/tmp/state", "storage": "sqlite"},
                "auth": {"provider": "bearer_token_file", "token_file": "/tmp/auth-token"},
                "credentials": {"provider": "directory", "directory": "/tmp/credentials"},
            },
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "127.0.0.1", "port": 8080},
                "runtime": {"state_dir": "/tmp/state", "storage": "json"},
                "auth": {"provider": "bearer_token_file", "token_file": "/tmp/auth-token"},
                "credentials": {"provider": "directory", "directory": "/tmp/credentials"},
            },
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "127.0.0.1", "port": 8080},
                "runtime": {"state_dir": "/tmp/state", "storage": "sqlite"},
                "auth": {"provider": "inline", "token": "must-not-be-accepted"},
                "credentials": {"provider": "directory", "directory": "/tmp/credentials"},
            },
        ]

        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "service.json"
            for payload in invalid_configs:
                with self.subTest(payload=payload):
                    config_path.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_service_config(config_path)


class RuntimeServiceTests(TestCase):
    def test_incomplete_request_body_times_out_with_bounded_error(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "skill2workflow.service.REQUEST_SOCKET_TIMEOUT_SECONDS",
                0.05,
            ):
                service = RuntimeService(_service_config(root))
                host, port = service.server_address
                thread = threading.Thread(
                    target=service._server.handle_request,
                    daemon=True,
                )
                thread.start()
                with socket.create_connection((host, port), timeout=2) as connection:
                    connection.sendall(
                        (
                            "POST /api/v1/retention-readiness HTTP/1.1\r\n"
                            f"Host: {host}\r\n"
                            f"Authorization: Bearer {AUTH_TOKEN}\r\n"
                            "Content-Length: 2\r\n"
                            "Connection: close\r\n"
                            "\r\n"
                        ).encode("ascii")
                    )
                    connection.settimeout(2)
                    response = connection.recv(4096)
                thread.join(timeout=2)
                service._server.server_close()

        self.assertIn(b"408 Request Timeout", response)
        self.assertIn(b'"error": "request timed out"', response)
        self.assertFalse(thread.is_alive())

    def test_audit_consistency_is_authenticated_bounded_and_read_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            run = control.run_published_workflow("workflow_service", "0.1.0")
            audit_count_before = len(control.list_audit_events())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/api/v1/audit-consistency"

            denied_status, denied = _get_json(url)
            accepted_status, report = _get_json(url, token=AUTH_TOKEN)
            body_connection = http.client.HTTPConnection(host, port, timeout=2)
            body_connection.request(
                "GET",
                "/api/v1/audit-consistency",
                body=b"{}",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            )
            body_response = body_connection.getresponse()
            body_payload = json.loads(body_response.read().decode("utf-8"))
            body_status = body_response.status
            body_connection.close()
            holder["service"].begin_shutdown()
            thread.join(timeout=3)
            audit_count_after = len(
                LocalControlPlane(state_dir, storage="sqlite").list_audit_events()
            )

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(report["schema_version"], "skill2workflow-run-audit-report-0.1.0")
        self.assertEqual(report["summary"]["run_count"], 1)
        self.assertEqual(report["summary"]["attention_runs"], 0)
        self.assertEqual(report["runs"][0]["run_id"], run["run_id"])
        self.assertEqual(body_status, 400)
        self.assertEqual(
            body_payload,
            {"error": "audit consistency request must not include a body"},
        )
        self.assertEqual(audit_count_after, audit_count_before)
        self.assertFalse(thread.is_alive())

    def test_audit_consistency_rejects_oversized_projection_without_disclosure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(_service_config(root))
            host, port = service.server_address
            thread = threading.Thread(target=service._server.handle_request, daemon=True)
            private_value = "private-audit-report-value-" + (
                "x" * MAX_AUDIT_CONSISTENCY_RESPONSE_BYTES
            )
            with patch.object(
                service.control_plane,
                "inspect_run_audit",
                return_value={"private": private_value},
            ):
                thread.start()
                status, payload = _get_json(
                    f"http://{host}:{port}/api/v1/audit-consistency",
                    token=AUTH_TOKEN,
                )
                thread.join(timeout=2)
            service._server.server_close()

        self.assertEqual(status, 503)
        self.assertEqual(payload, {"error": "audit consistency unavailable"})
        self.assertNotIn("private-audit-report-value", json.dumps(payload))
        self.assertFalse(thread.is_alive())

    def test_audit_consistency_is_available_before_readiness(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(_service_config(root))
            host, port = service.server_address
            thread = threading.Thread(target=service._server.handle_request, daemon=True)
            thread.start()
            status, report = _get_json(
                f"http://{host}:{port}/api/v1/audit-consistency",
                token=AUTH_TOKEN,
            )
            thread.join(timeout=2)
            service._server.server_close()

        self.assertEqual(status, 200)
        self.assertEqual(report["summary"]["run_count"], 0)
        self.assertEqual(service.status, "starting")
        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_list_is_authenticated_redacted_and_available_before_readiness(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(_service_config(root))
            service.scheduler.dispatcher.store.add(
                {
                    "schema_version": "skill2workflow-schedule-0.2.0",
                    "schedule": {
                        "id": "schedule_service_report",
                        "workflow_id": "workflow_service",
                        "version": "0.1.0",
                        "starts_at": "2026-08-11T00:00:00Z",
                        "interval_seconds": 60,
                        "missed_run_policy": "latest",
                        "enabled": True,
                    },
                    "trigger": {
                        "idempotency_key_prefix": "schedule_service_report",
                        "input": {"private": "private-schedule-input"},
                    },
                }
            )
            audit_count_before = len(
                LocalControlPlane(root / "state", storage="sqlite").list_audit_events()
            )
            host, port = service.server_address
            thread = threading.Thread(target=service._server.handle_request, daemon=True)
            thread.start()
            denied_status, denied = _get_json(
                f"http://{host}:{port}/api/v1/recurring-schedules"
            )
            thread.join(timeout=2)
            thread = threading.Thread(target=service._server.handle_request, daemon=True)
            thread.start()
            accepted_status, payload = _get_json(
                f"http://{host}:{port}/api/v1/recurring-schedules",
                token=AUTH_TOKEN,
            )
            thread.join(timeout=2)
            service._server.server_close()
            audit_count_after = len(
                LocalControlPlane(root / "state", storage="sqlite").list_audit_events()
            )

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(
            payload["schema_version"],
            "skill2workflow-recurring-schedule-list-0.1.0",
        )
        self.assertEqual(payload["summary"]["total"], 1)
        self.assertEqual(payload["schedules"][0]["schedule_id"], "schedule_service_report")
        self.assertNotIn("private-schedule-input", json.dumps(payload, ensure_ascii=False))
        self.assertEqual(service.status, "starting")
        self.assertEqual(audit_count_after, audit_count_before)
        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_action_is_authenticated_idempotent_and_audited(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            service = RuntimeService(config)
            service.scheduler.dispatcher.store.add(
                {
                    "schema_version": "skill2workflow-schedule-0.2.0",
                    "schedule": {
                        "id": "schedule_service_report",
                        "workflow_id": "workflow_service",
                        "version": "0.1.0",
                        "starts_at": "2026-08-11T00:00:00Z",
                        "interval_seconds": 60,
                        "missed_run_policy": "latest",
                        "enabled": True,
                    },
                    "trigger": {"input": {"private": "must-not-leak"}},
                }
            )
            ready = threading.Event()
            serve_thread = threading.Thread(
                target=service.serve,
                kwargs={"ready_callback": lambda _service: ready.set()},
                daemon=True,
            )
            serve_thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = service.server_address
            denied_status, denied = _post_json(
                f"http://{host}:{port}/api/v1/recurring-schedules/schedule_service_report/disable",
                {},
            )
            invalid_status, invalid = _post_json(
                f"http://{host}:{port}/api/v1/recurring-schedules/schedule_service_report/disable",
                {"unexpected": True},
                token=AUTH_TOKEN,
            )
            action_status, action = _post_json(
                f"http://{host}:{port}/api/v1/recurring-schedules/schedule_service_report/disable",
                {},
                token=AUTH_TOKEN,
            )
            repeat_status, repeated = _post_json(
                f"http://{host}:{port}/api/v1/recurring-schedules/schedule_service_report/disable",
                {},
                token=AUTH_TOKEN,
            )
            service.begin_shutdown()
            serve_thread.join(timeout=3)
            stored = service.scheduler.dispatcher.store.get("schedule_service_report")
            audit = LocalControlPlane(state_dir, storage="sqlite").list_audit_events()

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(invalid_status, 400)
        self.assertEqual(
            invalid,
            {"error": "recurring schedule action body must be an empty JSON object"},
        )
        self.assertEqual(action_status, 200)
        self.assertEqual(action["schema_version"], "skill2workflow-recurring-schedule-action-0.1.0")
        self.assertEqual(action["schedule_id"], "schedule_service_report")
        self.assertFalse(action["enabled"])
        self.assertEqual(action["status"], "disabled")
        self.assertTrue(action["changed"])
        self.assertEqual(repeat_status, 200)
        self.assertFalse(repeated["changed"])
        self.assertFalse(stored["schedule"]["enabled"])
        self.assertEqual(
            [event["type"] for event in audit if event.get("route") == "recurring_schedule_action"],
            [
                "ingress_authentication_denied",
                "ingress_authenticated",
                "ingress_authenticated",
                "ingress_authenticated",
            ],
        )
        mutations = [event for event in audit if event.get("type") == "recurring_schedule_updated"]
        self.assertEqual(len(mutations), 2)
        self.assertEqual([event["changed"] for event in mutations], [True, False])
        self.assertNotIn("must-not-leak", json.dumps(audit, ensure_ascii=False))
        self.assertFalse(serve_thread.is_alive())

    def test_recurring_schedule_dispatch_list_is_authenticated_bounded_and_redacted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            service = RuntimeService(config)
            store = service.scheduler.dispatcher.store
            record = {
                "dispatch_id": "dispatch_private_001",
                "schedule_id": "schedule_private_report",
                "scheduled_for": "2026-08-11T00:00:00+00:00",
                "status": "uncertain",
                "owner_id": "private-dispatch-owner",
                "claim_expires_at": 1234.0,
                "coalesced_occurrences": 1,
                "run_id": "run_dispatch_private_001",
                "trigger_id": "trigger_dispatch_private_001",
                "error_type": "ProviderPrivateError",
                "completed_at": "2026-08-11T00:01:00+00:00",
                "input": "private-dispatch-input",
            }
            with store._connection() as connection:
                connection.execute(
                    """
                    insert into schedule_dispatches (
                        dispatch_id, schedule_id, scheduled_for, status,
                        owner_id, claim_expires_at, record_json
                    ) values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["dispatch_id"], record["schedule_id"], record["scheduled_for"],
                        record["status"], record["owner_id"], record["claim_expires_at"],
                        json.dumps(record),
                    ),
                )
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda running: (holder.update({"service": running}), ready.set()),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            denied_status, denied = _get_json(
                f"http://{host}:{port}/api/v1/recurring-schedule-dispatches"
            )
            accepted_status, accepted = _get_json(
                f"http://{host}:{port}/api/v1/recurring-schedule-dispatches",
                token=AUTH_TOKEN,
            )
            targeted_status, targeted = _get_json(
                f"http://{host}:{port}/api/v1/recurring-schedules/schedule_private_report/dispatches",
                token=AUTH_TOKEN,
            )
            holder["service"].begin_shutdown()
            thread.join(timeout=3)

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(
            accepted["schema_version"],
            "skill2workflow-recurring-schedule-dispatch-list-0.1.0",
        )
        self.assertEqual(accepted["summary"]["status_counts"]["uncertain"], 1)
        self.assertEqual(targeted_status, 200)
        self.assertEqual(targeted["schedule_id"], "schedule_private_report")
        self.assertEqual(targeted["dispatches"][0]["status"], "uncertain")
        self.assertEqual(targeted["dispatches"][0]["error_type"], "ProviderPrivateError")
        serialized = json.dumps(accepted, ensure_ascii=False)
        self.assertNotIn("private-dispatch-owner", serialized)
        self.assertNotIn("private-dispatch-input", serialized)
        self.assertNotIn("claim_expires_at", serialized)
        self.assertFalse(thread.is_alive())

    def test_workflow_artifact_report_is_authenticated_bounded_and_value_free(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            service = RuntimeService(config)
            workflow = _workflow()
            workflow["workflow"]["name"] = "Private workflow title"
            service.control_plane.publish_workflow(workflow)
            (state_dir / "workflows" / "orphan.json").write_text("{}", encoding="utf-8")
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda running: (
                        holder.update({"service": running}), ready.set()
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            denied_status, denied = _get_json(
                f"http://{host}:{port}/api/v1/workflow-artifacts"
            )
            accepted_status, accepted = _get_json(
                f"http://{host}:{port}/api/v1/workflow-artifacts",
                token=AUTH_TOKEN,
            )
            holder["service"].begin_shutdown()
            thread.join(timeout=3)

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(
            accepted["schema_version"],
            "skill2workflow-workflow-artifact-report-0.1.0",
        )
        self.assertEqual(accepted["status"], "attention")
        self.assertEqual(accepted["summary"]["issue_count"], 1)
        self.assertEqual(len(accepted["issues"]), 1)
        self.assertNotIn("Private workflow title", json.dumps(accepted, ensure_ascii=False))
        self.assertFalse(thread.is_alive())

    def test_backup_readiness_is_authenticated_and_reports_active_lease(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda running: (
                        holder.update({"service": running}), ready.set()
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            denied_status, denied = _get_json(
                f"http://{host}:{port}/api/v1/backup-readiness"
            )
            accepted_status, accepted = _get_json(
                f"http://{host}:{port}/api/v1/backup-readiness",
                token=AUTH_TOKEN,
            )
            holder["service"].begin_shutdown()
            thread.join(timeout=3)

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(
            accepted["schema_version"],
            "skill2workflow-backup-readiness-0.1.0",
        )
        self.assertEqual(accepted["status"], "blocked")
        self.assertTrue(accepted["active_scheduler_lease"])
        self.assertFalse(accepted["backup_allowed"])
        self.assertEqual(accepted["blocking_reasons"], ["active_scheduler_lease"])
        self.assertFalse(thread.is_alive())

    def test_retention_readiness_is_authenticated_bounded_and_blocks_live_service(self):
        policy = {
            "schema_version": "skill2workflow-retention-policy-0.3.0",
            "retention": {
                "delete_before": "2026-01-01T00:00:00Z",
                "terminal_run_statuses": ["completed", "failed", "cancelled", "interrupted"],
                "terminal_dispatch_statuses": ["completed", "failed", "skipped", "uncertain"],
            },
        }
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda running: (
                        holder.update({"service": running}), ready.set()
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/api/v1/retention-readiness"
            try:
                denied_status, denied = _post_json(url, {"policy": policy})
                malformed_status, malformed = _post_json(
                    url,
                    {"policy": {"schema_version": "unsupported"}},
                    token=AUTH_TOKEN,
                )
                accepted_status, accepted = _post_json(
                    url,
                    {"policy": policy},
                    token=AUTH_TOKEN,
                )
            finally:
                holder["service"].begin_shutdown()
                thread.join(timeout=3)

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(malformed_status, 400)
        self.assertEqual(malformed, {"error": "retention readiness rejected"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(
            accepted["schema_version"],
            "skill2workflow-retention-readiness-0.1.0",
        )
        self.assertEqual(accepted["status"], "blocked")
        self.assertTrue(accepted["active_scheduler_lease"])
        self.assertFalse(accepted["plan_available"])
        self.assertEqual(accepted["blocking_reasons"], ["active_scheduler_lease"])
        self.assertTrue(all(value is None for value in accepted["eligible"].values()))
        self.assertFalse(thread.is_alive())

    def test_operational_readiness_is_authenticated_aggregate_and_redacted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda running: (
                        holder.update({"service": running}), ready.set()
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            base_url = f"http://{host}:{port}"
            try:
                denied_status, denied = _get_json(
                    f"{base_url}/api/v1/operational-readiness"
                )
                report = fetch_operational_readiness(
                    base_url,
                    config.auth_token_file,
                )
                body_status, body = _get_raw_get(
                    f"{base_url}/api/v1/operational-readiness",
                    token=AUTH_TOKEN,
                    body=b"{}",
                )
            finally:
                holder["service"].begin_shutdown()
                thread.join(timeout=3)

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["service"]["status"], "ready")
        self.assertTrue(report["service"]["ready"])
        self.assertEqual(report["checks"]["workflow_artifacts"], {
            "status": "clean",
            "issue_count": 0,
        })
        self.assertEqual(report["checks"]["audit_integrity"]["status"], "valid")
        self.assertEqual(report["checks"]["offline_backup"]["status"], "blocked")
        self.assertEqual(report["operator_notes"], ["offline_backup_requires_stop"])
        self.assertEqual(body_status, 400)
        self.assertEqual(body, {"error": "operational readiness request must not include a body"})
        self.assertFalse(thread.is_alive())

    def test_audit_integrity_is_authenticated_payload_free_and_read_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda running: (
                        holder.update({"service": running}), ready.set()
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            denied_status, denied = _get_json(
                f"http://{host}:{port}/api/v1/audit-integrity"
            )
            accepted_status, accepted = _get_json(
                f"http://{host}:{port}/api/v1/audit-integrity",
                token=AUTH_TOKEN,
            )
            body_connection = http.client.HTTPConnection(host, port, timeout=2)
            body_connection.request(
                "GET",
                "/api/v1/audit-integrity",
                body=b"{}",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            )
            body_response = body_connection.getresponse()
            body_payload = json.loads(body_response.read().decode("utf-8"))
            body_status = body_response.status
            body_connection.close()
            holder["service"].begin_shutdown()
            thread.join(timeout=3)

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(
            accepted["schema_version"],
            "skill2workflow-audit-integrity-0.1.0",
        )
        self.assertEqual(accepted["status"], "valid")
        self.assertEqual(accepted["algorithm"], "sha256-chain-v1")
        self.assertGreater(accepted["event_count"], 0)
        self.assertEqual(len(accepted["head_digest"]), 64)
        self.assertEqual(body_status, 400)
        self.assertEqual(
            body_payload,
            {"error": "audit integrity request must not include a body"},
        )
        self.assertFalse(thread.is_alive())

    def test_audit_integrity_rejects_oversized_projection_without_disclosure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(_service_config(root))
            host, port = service.server_address
            thread = threading.Thread(target=service._server.handle_request, daemon=True)
            private_value = "private-audit-integrity-value-" + (
                "x" * MAX_AUDIT_INTEGRITY_RESPONSE_BYTES
            )
            with patch.object(
                service.control_plane,
                "verify_audit_integrity",
                return_value={"private": private_value},
            ):
                thread.start()
                status, payload = _get_json(
                    f"http://{host}:{port}/api/v1/audit-integrity",
                    token=AUTH_TOKEN,
                )
                thread.join(timeout=2)
            service._server.server_close()

        self.assertEqual(status, 503)
        self.assertEqual(payload, {"error": "audit integrity unavailable"})
        self.assertNotIn("private-audit-integrity-value", json.dumps(payload))
        self.assertFalse(thread.is_alive())

    def test_runtime_info_is_authenticated_bounded_and_reports_compatibility(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _service_config(root)
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda running: (
                        holder.update({"service": running}), ready.set()
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            denied_status, denied = _get_json(
                f"http://{host}:{port}/api/v1/runtime-info"
            )
            accepted_status, accepted = _get_json(
                f"http://{host}:{port}/api/v1/runtime-info",
                token=AUTH_TOKEN,
            )
            body_connection = http.client.HTTPConnection(host, port, timeout=2)
            body_connection.request(
                "GET",
                "/api/v1/runtime-info",
                body=b"{}",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            )
            body_response = body_connection.getresponse()
            body_payload = json.loads(body_response.read().decode("utf-8"))
            body_status = body_response.status
            body_connection.close()
            holder["service"].begin_shutdown()
            thread.join(timeout=3)

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(
            accepted["schema_version"],
            "skill2workflow-runtime-info-0.1.0",
        )
        self.assertEqual(accepted["package_version"], "0.1.0")
        self.assertEqual(accepted["compatibility_line"], "0.1.x")
        self.assertEqual(accepted["service_schema_version"], SERVICE_SCHEMA_VERSION)
        self.assertEqual(accepted["workflow_dsl_schema_version"], "0.1.0")
        self.assertEqual(accepted["storage"], "sqlite")
        self.assertEqual(
            accepted["state_layout_version"],
            "skill2workflow-sqlite-layout-0.1.0",
        )
        self.assertEqual(accepted["service_status"], "ready")
        self.assertTrue(accepted["service_ready"])
        self.assertTrue(accepted["scheduler_lease_owned"])
        self.assertEqual(body_status, 400)
        self.assertEqual(
            body_payload,
            {"error": "runtime info request must not include a body"},
        )
        self.assertLess(len(json.dumps(accepted).encode("utf-8")), MAX_RUNTIME_INFO_RESPONSE_BYTES)
        self.assertFalse(thread.is_alive())

    def test_audit_consistency_can_target_one_run_beyond_the_global_window(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            run = control.run_published_workflow("workflow_service", "0.1.0")
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/api/v1/audit-consistency/{run['run_id']}"
            status, report = _get_json(url, token=AUTH_TOKEN)
            holder["service"].begin_shutdown()
            thread.join(timeout=3)

        self.assertEqual(status, 200)
        self.assertEqual(report["summary"]["run_count"], 1)
        self.assertEqual(report["summary"]["checked_runs"], 1)
        self.assertEqual(report["runs"][0]["run_id"], run["run_id"])
        self.assertFalse(report["summary"]["truncated"])
        self.assertFalse(thread.is_alive())
    def test_business_routes_fail_fast_when_admission_budget_is_exhausted_but_probes_remain_available(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(_service_config(root))
            host, port = service.server_address
            held = [
                service._request_admission.acquire(blocking=False)
                for _ in range(MAX_CONCURRENT_BUSINESS_REQUESTS)
            ]
            self.assertTrue(all(held))
            try:
                metrics_thread = threading.Thread(target=service._server.handle_request, daemon=True)
                metrics_thread.start()
                metrics_status, metrics_payload = _get_json(
                    f"http://{host}:{port}/metrics",
                    token=AUTH_TOKEN,
                )
                metrics_thread.join(timeout=2)

                health_thread = threading.Thread(target=service._server.handle_request, daemon=True)
                health_thread.start()
                health_status, health_payload = _get_json(f"http://{host}:{port}/healthz")
                health_thread.join(timeout=2)
            finally:
                for acquired in held:
                    if acquired:
                        service._request_admission.release()
                service._server.server_close()

        self.assertEqual(metrics_status, 429)
        self.assertEqual(metrics_payload, {"error": "service concurrency limit reached"})
        self.assertEqual(health_status, 200)
        self.assertEqual(health_payload, {"service": "skill2workflow", "status": "ok"})
        self.assertFalse(metrics_thread.is_alive())
        self.assertFalse(health_thread.is_alive())

    def test_live_control_snapshot_is_authenticated_bounded_and_read_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            control.run_published_workflow("workflow_service", "0.1.0")
            audit_count_before = len(control.list_audit_events())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/api/v1/control-snapshot"

            denied_status, denied = _get_json(url)
            accepted_status, snapshot = _get_json(url, token=AUTH_TOKEN)
            body_connection = http.client.HTTPConnection(host, port, timeout=2)
            body_connection.request(
                "GET",
                "/api/v1/control-snapshot",
                body=b"{}",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            )
            body_response = body_connection.getresponse()
            body_payload = json.loads(body_response.read().decode("utf-8"))
            body_status = body_response.status
            body_connection.close()
            holder["service"].begin_shutdown()
            thread.join(timeout=3)
            audit_count_after = len(
                LocalControlPlane(
                    state_dir, storage="sqlite"
                ).list_audit_events()
            )

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(
            snapshot["schema_version"],
            "skill2workflow-control-snapshot-0.1.0",
        )
        self.assertEqual(snapshot["summary"]["workflow_count"], 1)
        self.assertGreaterEqual(snapshot["summary"]["run_count"], 1)
        self.assertEqual(snapshot["window"]["max_items"], 100)
        self.assertEqual(body_status, 400)
        self.assertEqual(
            body_payload,
            {"error": "live control snapshot request must not include a body"},
        )
        self.assertEqual(audit_count_after, audit_count_before)
        self.assertFalse(thread.is_alive())

    def test_live_control_snapshot_is_available_before_readiness(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(_service_config(root))
            host, port = service.server_address
            thread = threading.Thread(target=service._server.handle_request, daemon=True)
            thread.start()

            status, snapshot = _get_json(
                f"http://{host}:{port}/api/v1/control-snapshot",
                token=AUTH_TOKEN,
            )
            thread.join(timeout=2)
            service._server.server_close()

        self.assertEqual(status, 200)
        self.assertEqual(snapshot["summary"]["workflow_count"], 0)
        self.assertEqual(service.status, "starting")
        self.assertFalse(thread.is_alive())

    def test_live_control_snapshot_rejects_oversized_output_without_disclosure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(_service_config(root))
            host, port = service.server_address
            thread = threading.Thread(target=service._server.handle_request, daemon=True)
            oversized_private_value = "private-value-" + (
                "x" * MAX_LIVE_CONTROL_SNAPSHOT_BYTES
            )
            with patch(
                "skill2workflow.service.build_control_snapshot_from_control",
                return_value={"value": oversized_private_value},
            ):
                thread.start()
                status, payload = _get_json(
                    f"http://{host}:{port}/api/v1/control-snapshot",
                    token=AUTH_TOKEN,
                )
                thread.join(timeout=2)
            service._server.server_close()

        self.assertEqual(status, 503)
        self.assertEqual(payload, {"error": "control snapshot unavailable"})
        self.assertNotIn("private-value", json.dumps(payload))
        self.assertFalse(thread.is_alive())

    def test_run_detail_is_authenticated_redacted_bounded_and_read_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            run = control.run_published_workflow("workflow_service", "0.1.0")
            state = control.get_run(run["run_id"])
            state["context"] = {"private_input": "private-input-value"}
            state["node_results"]["start"]["output"] = "private-output-value"
            state["events"].append(
                {
                    "type": "connector_failed",
                    "node_id": "start",
                    "timestamp": "2026-08-13T00:00:00+00:00",
                    "error": "private-error-value",
                    "response": "private-response-value",
                }
            )
            control.executor.store.save(state)
            audit_count_before = len(control.list_audit_events())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/runs/{run['run_id']}"

            denied_status, denied = _get_json(url)
            accepted_status, detail = _get_json(url, token=AUTH_TOKEN)
            missing_status, missing = _get_json(
                f"http://{host}:{port}/runs/run_missing_detail"
                , token=AUTH_TOKEN,
            )
            body_connection = http.client.HTTPConnection(host, port, timeout=2)
            body_connection.request(
                "GET",
                f"/runs/{run['run_id']}",
                body=b"{}",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            )
            body_response = body_connection.getresponse()
            body_payload = json.loads(body_response.read().decode("utf-8"))
            body_status = body_response.status
            body_connection.close()
            holder["service"].begin_shutdown()
            thread.join(timeout=3)
            audit_count_after = len(
                LocalControlPlane(state_dir, storage="sqlite").list_audit_events()
            )

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(detail["run"]["run_id"], run["run_id"])
        self.assertEqual(detail["schema_version"], "skill2workflow-run-detail-0.1.0")
        serialized = json.dumps(detail, ensure_ascii=False)
        for private_value in (
            "private-input-value",
            "private-output-value",
            "private-error-value",
            "private-response-value",
        ):
            self.assertNotIn(private_value, serialized)
        self.assertNotIn("context", serialized)
        self.assertNotIn("error", detail["events"][-1])
        self.assertIn("has_error", detail["events"][-1])
        self.assertEqual(missing_status, 404)
        self.assertEqual(missing, {"error": "run not found"})
        self.assertEqual(body_status, 400)
        self.assertEqual(body_payload, {"error": "run detail request must not include a body"})
        self.assertEqual(audit_count_after, audit_count_before)
        self.assertFalse(thread.is_alive())

    def test_run_detail_rejects_oversized_projection_without_disclosure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(_service_config(root))
            host, port = service.server_address
            thread = threading.Thread(target=service._server.handle_request, daemon=True)
            private_value = "private-run-detail-value-" + ("x" * 70000)
            with patch(
                "skill2workflow.service.build_run_detail_from_control",
                return_value={"private": private_value},
            ):
                thread.start()
                status, payload = _get_json(
                    f"http://{host}:{port}/runs/run_oversized_detail",
                    token=AUTH_TOKEN,
                )
                thread.join(timeout=2)
            service._server.server_close()

        self.assertEqual(status, 503)
        self.assertEqual(payload, {"error": "run detail unavailable"})
        self.assertNotIn("private-run-detail-value", json.dumps(payload))
        self.assertFalse(thread.is_alive())

    def test_run_list_is_authenticated_bounded_and_read_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            run = control.run_published_workflow("workflow_service", "0.1.0")
            state = control.get_run(run["run_id"])
            state["context"] = {"private_input": "private-list-input"}
            state["node_results"]["start"]["output"] = "private-list-output"
            control.executor.store.save(state)
            audit_count_before = len(control.list_audit_events())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/runs"

            denied_status, denied = _get_json(url)
            accepted_status, listing = _get_json(url, token=AUTH_TOKEN)
            body_connection = http.client.HTTPConnection(host, port, timeout=2)
            body_connection.request(
                "GET",
                "/runs",
                body=b"{}",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            )
            body_response = body_connection.getresponse()
            body_payload = json.loads(body_response.read().decode("utf-8"))
            body_status = body_response.status
            body_connection.close()
            holder["service"].begin_shutdown()
            thread.join(timeout=3)
            audit_count_after = len(
                LocalControlPlane(state_dir, storage="sqlite").list_audit_events()
            )

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(listing["schema_version"], "skill2workflow-run-list-0.1.0")
        self.assertEqual(listing["summary"]["total"], 1)
        self.assertEqual(len(listing["runs"]), 1)
        serialized = json.dumps(listing, ensure_ascii=False)
        self.assertNotIn("private-list-input", serialized)
        self.assertNotIn("private-list-output", serialized)
        self.assertNotIn("context", serialized)
        self.assertEqual(body_status, 400)
        self.assertEqual(body_payload, {"error": "run list request must not include a body"})
        self.assertEqual(audit_count_after, audit_count_before)
        self.assertFalse(thread.is_alive())

    def test_support_bundle_is_authenticated_redacted_bounded_and_read_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            run = control.run_published_workflow("workflow_service", "0.1.0")
            state = control.get_run(run["run_id"])
            state["context"] = {"private_input": "private-bundle-input"}
            state["node_results"]["start"]["output"] = "private-bundle-output"
            control.executor.store.save(state)
            audit_count_before = len(control.list_audit_events())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/api/v1/support-bundle"

            denied_status, denied = _get_json(url)
            accepted_status, bundle = _get_json(url, token=AUTH_TOKEN)
            body_connection = http.client.HTTPConnection(host, port, timeout=2)
            body_connection.request(
                "GET",
                "/api/v1/support-bundle",
                body=b"{}",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            )
            body_response = body_connection.getresponse()
            body_payload = json.loads(body_response.read().decode("utf-8"))
            body_status = body_response.status
            body_connection.close()
            holder["service"].begin_shutdown()
            thread.join(timeout=3)
            audit_count_after = len(
                LocalControlPlane(state_dir, storage="sqlite").list_audit_events()
            )

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(bundle["schema_version"], "skill2workflow-support-bundle-0.1.0")
        self.assertEqual(bundle["service"]["storage"], "sqlite")
        self.assertEqual(bundle["run_list"]["summary"]["total"], 1)
        self.assertEqual(bundle["observability"]["service_status"], "ready")
        serialized = json.dumps(bundle, ensure_ascii=False)
        self.assertNotIn("private-bundle-input", serialized)
        self.assertNotIn("private-bundle-output", serialized)
        self.assertNotIn(str(state_dir), serialized)
        self.assertEqual(body_status, 400)
        self.assertEqual(body_payload, {"error": "support bundle request must not include a body"})
        self.assertEqual(audit_count_after, audit_count_before)
        self.assertFalse(thread.is_alive())

    def test_support_bundle_rejects_oversized_projection_without_disclosure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(_service_config(root))
            host, port = service.server_address
            thread = threading.Thread(target=service._server.handle_request, daemon=True)
            private_value = "private-support-bundle-value-" + ("x" * 140000)
            with patch(
                "skill2workflow.service.build_support_bundle_from_control",
                return_value={"private": private_value},
            ):
                thread.start()
                status, payload = _get_json(
                    f"http://{host}:{port}/api/v1/support-bundle",
                    token=AUTH_TOKEN,
                )
                thread.join(timeout=2)
            service._server.server_close()

        self.assertEqual(status, 503)
        self.assertEqual(payload, {"error": "support bundle unavailable"})
        self.assertNotIn("private-support-bundle-value", json.dumps(payload))
        self.assertFalse(thread.is_alive())

    def test_auth_token_read_is_descriptor_bound_against_path_replacement(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            token_file = root / "ingress.token"
            replacement = root / "replacement.token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            replacement.write_text("r" * 48, encoding="utf-8")
            token_file.chmod(0o600)
            replacement.chmod(0o600)
            real_open = __import__("os").open
            replaced = False

            def replace_before_open(path, flags, *args):
                nonlocal replaced
                if Path(path) == token_file and not replaced:
                    replaced = True
                    replacement.replace(token_file)
                return real_open(path, flags, *args)

            with patch("skill2workflow.service.os.open", side_effect=replace_before_open):
                with self.assertRaisesRegex(ValueError, "changed while being read"):
                    FileBearerTokenAuthenticator(token_file)

    def test_auth_token_read_rejects_oversized_file_before_decoding(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "ingress.token"
            token_file.write_bytes(b"x" * (MAX_AUTH_TOKEN_BYTES + 1))
            token_file.chmod(0o600)

            with self.assertRaisesRegex(ValueError, "size limit"):
                FileBearerTokenAuthenticator(token_file)

    def test_metrics_route_requires_auth_and_exports_only_aggregate_text(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            LocalControlPlane(state_dir, storage="sqlite").publish_workflow(_workflow())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/metrics"

            denied_status, _, _ = _get_raw(url)
            accepted_status, content_type, first_metrics = _get_raw(
                url, token=AUTH_TOKEN
            )
            _, _, second_metrics = _get_raw(url, token=AUTH_TOKEN)
            holder["service"].begin_shutdown()
            thread.join(timeout=3)
            audit_count = len(
                LocalControlPlane(state_dir, storage="sqlite").list_audit_events()
            )

        self.assertEqual(denied_status, 401)
        self.assertEqual(accepted_status, 200)
        self.assertEqual(
            content_type,
            "text/plain; version=0.0.4; charset=utf-8",
        )
        self.assertIn("skill2workflow_service_ready 1", first_metrics)
        self.assertIn(
            'skill2workflow_http_requests_total{route="metrics",status_class="4xx"} 1',
            first_metrics,
        )
        self.assertIn(
            'skill2workflow_http_requests_total{route="metrics",status_class="2xx"} 1',
            second_metrics,
        )
        self.assertNotIn("workflow_id", first_metrics + second_metrics)
        self.assertNotIn("service continuity", first_metrics + second_metrics)
        self.assertNotIn(AUTH_TOKEN, first_metrics + second_metrics)
        self.assertEqual(audit_count, 1)
        self.assertFalse(thread.is_alive())

    def test_metrics_remain_authenticated_and_available_while_service_is_not_ready(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(_service_config(root))
            host, port = service.server_address
            thread = threading.Thread(target=service._server.handle_request, daemon=True)
            thread.start()

            status, _, metrics = _get_raw(
                f"http://{host}:{port}/metrics", token=AUTH_TOKEN
            )
            thread.join(timeout=2)
            service._server.server_close()

        self.assertEqual(status, 200)
        self.assertIn("skill2workflow_service_ready 0", metrics)
        self.assertIn("skill2workflow_scheduler_lease_owned 0", metrics)
        self.assertFalse(thread.is_alive())

    def test_unexpected_scheduler_failure_releases_lease_for_standby(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            scheduler = ServiceScheduleLoop(state_dir)

            def fail_dispatch(*_args, **_kwargs):
                raise RuntimeError("unexpected scheduler failure")

            scheduler.dispatcher.dispatch_due = fail_dispatch
            scheduler.start()
            replacement = RecurringScheduleDispatcher(
                state_dir,
                owner_id="replacement-owner",
                lease_seconds=10,
            )
            acquired = False
            try:
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    if scheduler._last_error:
                        acquired = replacement.try_acquire(now_epoch=time.time())
                        if acquired:
                            break
                    time.sleep(0.02)
            finally:
                scheduler.stop()
                if acquired:
                    replacement.release()

        self.assertEqual(scheduler._last_error, "RuntimeError")
        self.assertTrue(acquired)
        self.assertFalse(scheduler.is_ready())

    def test_heartbeat_storage_failure_is_fail_closed_without_killing_threads(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            scheduler = ServiceScheduleLoop(state_dir)
            scheduler.dispatcher.lease_seconds = 0.3
            scheduler.start()

            def fail_renew(*_args, **_kwargs):
                raise sqlite3.OperationalError("simulated heartbeat failure")

            scheduler.dispatcher.renew = fail_renew
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and not scheduler._last_error:
                time.sleep(0.02)
            heartbeat_alive = scheduler._heartbeat_thread.is_alive()
            dispatch_alive = scheduler._dispatch_thread.is_alive()
            scheduler.stop()

        self.assertEqual(scheduler._last_error, "OperationalError")
        self.assertTrue(heartbeat_alive)
        self.assertTrue(dispatch_alive)
        self.assertFalse(scheduler.is_ready())

    def test_service_dispatches_recurring_schedule_and_persists_record(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            LocalControlPlane(state_dir, storage="sqlite").publish_workflow(_workflow())
            starts_at = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
            RecurringScheduleStore(state_dir).add(
                {
                    "schema_version": "skill2workflow-schedule-0.2.0",
                    "schedule": {
                        "id": "schedule_service_tick",
                        "workflow_id": "workflow_service",
                        "version": "0.1.0",
                        "starts_at": starts_at,
                        "interval_seconds": 60,
                        "missed_run_policy": "latest",
                    },
                    "trigger": {"input": {}},
                }
            )
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))

            deadline = time.monotonic() + 5
            runs = []
            while time.monotonic() < deadline:
                runs = LocalControlPlane(state_dir, storage="sqlite").list_runs()
                if runs:
                    break
                time.sleep(0.05)
            holder["service"].begin_shutdown()
            thread.join(timeout=3)
            dispatches = RecurringScheduleStore(state_dir).list_dispatches()

        self.assertEqual(len(runs), 1)
        self.assertEqual(dispatches[0]["status"], "completed")
        self.assertEqual(dispatches[0]["run_id"], runs[0]["run_id"])

    def test_only_lease_owner_is_ready_and_standby_takes_over_after_shutdown(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            first_ready = threading.Event()
            second_ready = threading.Event()
            holders = {}
            first_thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holders.update({"first": service}),
                        first_ready.set(),
                    ),
                },
                daemon=True,
            )
            first_thread.start()
            self.assertTrue(first_ready.wait(timeout=2))
            second_thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holders.update({"second": service}),
                        second_ready.set(),
                    ),
                },
                daemon=True,
            )
            second_thread.start()
            self.assertTrue(second_ready.wait(timeout=2))

            ownership_deadline = time.monotonic() + max(
                holders["first"].scheduler.dispatcher.lease_seconds,
                holders["second"].scheduler.dispatcher.lease_seconds,
            ) + 3
            first_status = second_status = 503
            while time.monotonic() < ownership_deadline:
                first_status, _ = holders["first"].readiness()
                second_status, _ = holders["second"].readiness()
                if sorted((first_status, second_status)) == [200, 503]:
                    break
                time.sleep(0.05)
            if first_status == 200 and second_status == 503:
                active = holders["first"]
                active_thread = first_thread
                standby = holders["second"]
                standby_thread = second_thread
            elif first_status == 503 and second_status == 200:
                active = holders["second"]
                active_thread = second_thread
                standby = holders["first"]
                standby_thread = first_thread
            else:
                holders["first"].begin_shutdown()
                holders["second"].begin_shutdown()
                first_thread.join(timeout=3)
                second_thread.join(timeout=3)
                self.fail(
                    "exactly one service must own the scheduler lease before takeover"
                )
            active.begin_shutdown()
            active_thread.join(timeout=3)
            deadline = (
                time.monotonic()
                + standby.scheduler.dispatcher.lease_seconds
                + 3
            )
            takeover_status = 503
            while time.monotonic() < deadline:
                takeover_status, _ = standby.readiness()
                if takeover_status == 200:
                    break
                time.sleep(0.05)
            standby.begin_shutdown()
            standby_thread.join(timeout=3)

        self.assertEqual(sorted((first_status, second_status)), [200, 503])
        self.assertEqual(takeover_status, 200)
        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())

    def test_ready_callback_failure_still_closes_listener(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = RuntimeService(
                _service_config(root)
            )
            host, port = service.server_address

            with self.assertRaisesRegex(RuntimeError, "callback failed"):
                service.serve(
                    ready_callback=lambda _service: (_ for _ in ()).throw(
                        RuntimeError("callback failed")
                    )
                )

            replacement = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                replacement.bind((host, port))
            finally:
                replacement.close()

        self.assertEqual(service.status, "stopped")

    def test_service_exposes_health_readiness_and_graceful_draining(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            ready = threading.Event()
            address = {}
            service_holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": _service_config(root, state_dir=state_dir),
                    "ready_callback": lambda service: (
                        service_holder.update({"service": service}),
                        address.update({"value": service.server_address}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = address["value"]

            health_status, health = _get_json(f"http://{host}:{port}/healthz")
            ready_status, readiness = _get_json(f"http://{host}:{port}/readyz")
            service_holder["service"].begin_shutdown()
            thread.join(timeout=3)

        self.assertEqual(health_status, 200)
        self.assertEqual(health, {"service": "skill2workflow", "status": "ok"})
        self.assertEqual(ready_status, 200)
        self.assertEqual(readiness["status"], "ready")
        self.assertEqual(readiness["storage"], "sqlite")
        self.assertFalse(thread.is_alive())
        self.assertEqual(service_holder["service"].status, "stopped")

    def test_sqlite_workflow_and_run_state_continue_after_service_restart(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            first = _run_service_and_trigger(root, state_dir, "continuity-1")
            second = _run_service_and_trigger(root, state_dir, "continuity-2")
            reloaded = LocalControlPlane(state_dir, storage="sqlite")

            run_ids = {run["run_id"] for run in reloaded.list_runs()}
            audit_run_ids = {
                event.get("run_id")
                for event in reloaded.list_audit_events()
                if event.get("run_id")
            }

        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(run_ids, {first["run_id"], second["run_id"]})
        self.assertTrue(run_ids.issubset(audit_run_ids))

    def test_authenticated_webhook_idempotency_replays_conflicts_and_does_not_duplicate_runs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/webhooks/workflow_service/0.1.0"
            request_body = {
                "source": "partner",
                "idempotency_key": "partner-event-001",
                "input": {"customer_id": "private-customer-001"},
            }
            first_status, first = _post_json(url, request_body, token=AUTH_TOKEN)
            replay_status, replay = _post_json(
                url,
                {**request_body, "trigger_id": "trigger-retry"},
                token=AUTH_TOKEN,
            )
            conflict_status, conflict = _post_json(
                url,
                {**request_body, "input": {"customer_id": "private-customer-002"}},
                token=AUTH_TOKEN,
            )
            holder["service"].begin_shutdown()
            thread.join(timeout=3)
            reloaded = LocalControlPlane(state_dir, storage="sqlite")
            runs = reloaded.list_runs()
            audit = reloaded.list_audit_events()
            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection:
                ledger = connection.execute(
                    "select status, response_json from trigger_idempotency"
                ).fetchall()

        self.assertEqual(first_status, 200)
        self.assertEqual(replay_status, 200)
        self.assertEqual(replay, first)
        self.assertEqual(conflict_status, 409)
        self.assertEqual(
            conflict,
            {"error": "idempotency key conflicts with an existing request"},
        )
        self.assertEqual(len(runs), 1)
        self.assertEqual(
            [event["type"] for event in audit if event.get("type") == "run_started"],
            ["run_started"],
        )
        self.assertEqual(ledger[0][0], "completed")
        self.assertNotIn("private-customer-001", json.dumps(ledger))
        self.assertNotIn("private-customer-002", json.dumps(ledger))

    def test_service_trigger_client_round_trip_replays_and_rejects_key_conflict(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            service_url = f"http://{host}:{port}"
            try:
                first = post_workflow_trigger(
                    service_url,
                    config.auth_token_file,
                    "workflow_service",
                    "0.1.0",
                    idempotency_key="client-event-001",
                    trigger_input={"customer_id": "private-customer-001"},
                )
                replay = post_workflow_trigger(
                    service_url,
                    config.auth_token_file,
                    "workflow_service",
                    "0.1.0",
                    idempotency_key="client-event-001",
                    trigger_input={"customer_id": "private-customer-001"},
                )
                with self.assertRaises(ServiceActionError) as raised:
                    post_workflow_trigger(
                        service_url,
                        config.auth_token_file,
                        "workflow_service",
                        "0.1.0",
                        idempotency_key="client-event-001",
                        trigger_input={"customer_id": "private-customer-002"},
                    )
            finally:
                holder["service"].begin_shutdown()
                thread.join(timeout=3)
            runs = LocalControlPlane(state_dir, storage="sqlite").list_runs()

        self.assertEqual(first, replay)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(len(runs), 1)
        self.assertFalse(thread.is_alive())

    def test_remote_workflow_publication_is_authenticated_immutable_and_redacted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/api/v1/workflow-releases"
            workflow = _workflow()
            try:
                denied_status, denied = _post_json(
                    url,
                    {"workflow": workflow},
                )
                malformed_status, malformed = _post_json(
                    url,
                    {"workflow": []},
                    token=AUTH_TOKEN,
                )
                published = post_workflow_release(
                    f"http://{host}:{port}",
                    config.auth_token_file,
                    workflow,
                )
                replay = post_workflow_release(
                    f"http://{host}:{port}",
                    config.auth_token_file,
                    workflow,
                )
                changed = json.loads(json.dumps(workflow))
                changed["description"] = "changed after publication"
                with self.assertRaises(ServiceActionError) as raised:
                    post_workflow_release(
                        f"http://{host}:{port}",
                        config.auth_token_file,
                        changed,
                    )
            finally:
                holder["service"].begin_shutdown()
                thread.join(timeout=3)
            records = LocalControlPlane(state_dir, storage="sqlite").list_workflows()

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(malformed_status, 400)
        self.assertEqual(malformed, {"error": "workflow publication rejected"})
        self.assertEqual(published, replay)
        self.assertEqual(
            set(published),
            {"schema_version", "workflow_id", "version", "status", "checksum"},
        )
        self.assertEqual(published["status"], "published")
        self.assertEqual(len(published["checksum"]), 64)
        self.assertNotIn("artifact", published)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(len(records), 1)
        self.assertFalse(thread.is_alive())

    def test_remote_workflow_promotion_is_authenticated_cas_and_redacted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            base_url = f"http://{host}:{port}"
            url = f"{base_url}/api/v1/workflow-promotions"
            workflow_v1 = _workflow()
            workflow_v2 = json.loads(json.dumps(workflow_v1))
            workflow_v2["workflow"]["version"] = "0.2.0"
            try:
                denied_status, denied = _post_json(
                    url,
                    {
                        "workflow_id": "workflow_service",
                        "version": "0.1.0",
                        "alias": "production",
                        "expected_current_version": "",
                    },
                )
                malformed_status, malformed = _post_json(
                    url,
                    {"workflow_id": "workflow_service"},
                    token=AUTH_TOKEN,
                )
                post_workflow_release(base_url, config.auth_token_file, workflow_v1)
                post_workflow_release(base_url, config.auth_token_file, workflow_v2)
                first = post_workflow_promotion(
                    base_url,
                    config.auth_token_file,
                    "workflow_service",
                    "0.1.0",
                )
                second = post_workflow_promotion(
                    base_url,
                    config.auth_token_file,
                    "workflow_service",
                    "0.2.0",
                    expected_current_version="0.1.0",
                )
                replay = post_workflow_promotion(
                    base_url,
                    config.auth_token_file,
                    "workflow_service",
                    "0.2.0",
                    expected_current_version="0.2.0",
                )
                with self.assertRaises(ServiceActionError) as raised:
                    post_workflow_promotion(
                        base_url,
                        config.auth_token_file,
                        "workflow_service",
                        "0.1.0",
                        expected_current_version="0.1.0",
                    )
            finally:
                holder["service"].begin_shutdown()
                thread.join(timeout=3)
            records = LocalControlPlane(state_dir, storage="sqlite").list_workflows()
            audit = LocalControlPlane(state_dir, storage="sqlite").list_audit_events()

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(malformed_status, 400)
        self.assertEqual(malformed, {"error": "workflow promotion rejected"})
        self.assertEqual(first["status"], "promoted")
        self.assertEqual(second, replay)
        self.assertEqual(
            set(second),
            {"schema_version", "workflow_id", "version", "alias", "status", "checksum"},
        )
        self.assertNotIn("artifact", second)
        self.assertEqual(raised.exception.status_code, 409)
        promoted = {
            record["version"]: record
            for record in records
            if record.get("workflow_id") == "workflow_service"
        }
        self.assertNotIn("aliases", promoted["0.1.0"])
        self.assertEqual(promoted["0.2.0"]["aliases"], ["production"])
        self.assertEqual(
            sum(event.get("type") == "workflow_promoted" for event in audit),
            2,
        )
        self.assertFalse(thread.is_alive())

    def test_remote_workflow_diff_is_authenticated_value_free_and_read_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            first = _workflow()
            second = json.loads(json.dumps(first))
            second["workflow"]["version"] = "0.2.0"
            second["nodes"][0]["title"] = "Private customer review title"
            control.publish_workflow(first)
            control.publish_workflow(second)
            audit_count = len(control.list_audit_events())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            base_url = f"http://{host}:{port}"
            url = f"{base_url}/api/v1/workflow-diffs/workflow_service/0.1.0/0.2.0"
            try:
                denied_status, denied = _get_json(url)
                malformed_status, malformed = _get_raw_get(
                    url,
                    token=AUTH_TOKEN,
                    body=b"{}",
                )
                diff = fetch_workflow_diff(
                    base_url,
                    config.auth_token_file,
                    "workflow_service",
                    "0.1.0",
                    "0.2.0",
                )
            finally:
                holder["service"].begin_shutdown()
                thread.join(timeout=3)
            audit_after = len(LocalControlPlane(state_dir, storage="sqlite").list_audit_events())

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(malformed_status, 400)
        self.assertEqual(malformed, {"error": "workflow diff request must not include a body"})
        self.assertEqual(diff["schema_version"], "skill2workflow-workflow-diff-0.1.0")
        self.assertTrue(diff["changed"])
        self.assertEqual(diff["changes"]["nodes"]["changed"], ["start"])
        serialized = json.dumps(diff, ensure_ascii=False)
        self.assertNotIn("Private customer review title", serialized)
        self.assertNotIn("artifact", serialized)
        self.assertEqual(audit_after, audit_count)
        self.assertFalse(thread.is_alive())

    def test_remote_workflow_deprecation_is_authenticated_idempotent_and_redacted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            workflow = _workflow()
            control.publish_workflow(workflow)
            control.promote_workflow("workflow_service", "0.1.0")
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            base_url = f"http://{host}:{port}"
            url = f"{base_url}/api/v1/workflow-deprecations"
            try:
                denied_status, denied = _post_json(
                    url,
                    {"workflow_id": "workflow_service", "version": "0.1.0"},
                )
                malformed_status, malformed = _post_json(
                    url,
                    {"workflow_id": "workflow_service"},
                    token=AUTH_TOKEN,
                )
                first = post_workflow_deprecation(
                    base_url,
                    config.auth_token_file,
                    "workflow_service",
                    "0.1.0",
                )
                replay = post_workflow_deprecation(
                    base_url,
                    config.auth_token_file,
                    "workflow_service",
                    "0.1.0",
                )
            finally:
                holder["service"].begin_shutdown()
                thread.join(timeout=3)
            records = LocalControlPlane(state_dir, storage="sqlite").list_workflows()
            audit = LocalControlPlane(state_dir, storage="sqlite").list_audit_events()
            artifact_preserved = (state_dir / records[0]["artifact"]).is_file()

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(malformed_status, 400)
        self.assertEqual(malformed, {"error": "workflow deprecation rejected"})
        self.assertEqual(first, replay)
        self.assertEqual(
            set(first),
            {"schema_version", "workflow_id", "version", "status", "checksum"},
        )
        self.assertEqual(first["status"], "deprecated")
        self.assertNotIn("deprecated_at", first)
        self.assertNotIn("artifact", first)
        record = next(item for item in records if item.get("version") == "0.1.0")
        self.assertEqual(record["status"], "deprecated")
        self.assertNotIn("aliases", record)
        self.assertTrue(artifact_preserved)
        self.assertEqual(
            sum(event.get("type") == "workflow_deprecated" for event in audit),
            1,
        )
        self.assertFalse(thread.is_alive())

    def test_remote_workflow_inventory_is_authenticated_bounded_and_read_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            first = _workflow()
            second = json.loads(json.dumps(first))
            second["workflow"]["version"] = "0.2.0"
            control.publish_workflow(first)
            control.publish_workflow(second)
            control.promote_workflow("workflow_service", "0.1.0")
            control.deprecate_workflow("workflow_service", "0.1.0")
            audit_count = len(control.list_audit_events())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            base_url = f"http://{host}:{port}"
            url = f"{base_url}/api/v1/workflows"
            try:
                denied_status, denied = _get_json(url)
                malformed_status, malformed = _get_raw_get(
                    url,
                    token=AUTH_TOKEN,
                    body=b"{}",
                )
                inventory = fetch_workflow_inventory(
                    base_url,
                    config.auth_token_file,
                )
            finally:
                holder["service"].begin_shutdown()
                thread.join(timeout=3)
            audit_after = len(LocalControlPlane(state_dir, storage="sqlite").list_audit_events())

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(malformed_status, 400)
        self.assertEqual(malformed, {"error": "workflow inventory request must not include a body"})
        self.assertEqual(
            set(inventory),
            {"schema_version", "summary", "versions", "window"},
        )
        self.assertEqual(inventory["summary"]["total"], 2)
        self.assertEqual(
            inventory["summary"]["status_counts"],
            {"published": 1, "deprecated": 1, "other": 0},
        )
        self.assertEqual(inventory["window"]["returned"], 2)
        self.assertEqual(
            {version["version"] for version in inventory["versions"]},
            {"0.1.0", "0.2.0"},
        )
        deprecated = next(version for version in inventory["versions"] if version["version"] == "0.1.0")
        self.assertEqual(deprecated["status"], "deprecated")
        self.assertEqual(deprecated["aliases"], [])
        for version in inventory["versions"]:
            self.assertNotIn("artifact", version)
            self.assertNotIn("name", version)
        self.assertEqual(audit_after, audit_count)
        self.assertFalse(thread.is_alive())

    def test_business_routes_require_rotatable_bearer_auth_and_write_compact_audit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/webhooks/workflow_service/0.1.0"

            missing_status, _ = _post_json(url, {})
            invalid_status, _ = _post_json(url, {}, token="wrong-token-value-that-is-long-enough")
            accepted_status, accepted = _post_json(url, {}, token=AUTH_TOKEN)
            rotated_token = "rotated-loop42-bearer-token-0123456789abcdef"
            rotate_service_token(
                config.auth_token_file,
                token_factory=lambda: rotated_token,
            )
            old_status, _ = _post_json(url, {}, token=AUTH_TOKEN)
            new_status, _ = _post_json(
                url,
                {"idempotency_key": "after-rotation"},
                token=rotated_token,
            )
            config.credential_dir.rmdir()
            credential_provider_status, _ = _post_json(
                url,
                {"idempotency_key": "credential-provider-unavailable"},
                token=rotated_token,
            )
            config.credential_dir.mkdir()
            config.auth_token_file.unlink()
            unavailable_status, unavailable = _get_json(f"http://{host}:{port}/readyz")
            unavailable_business_status, _ = _post_json(url, {}, token=rotated_token)
            holder["service"].begin_shutdown()
            thread.join(timeout=3)

            audit = LocalControlPlane(state_dir, storage="sqlite").list_audit_events()

        self.assertEqual((missing_status, invalid_status), (401, 401))
        self.assertEqual(accepted_status, 200)
        self.assertEqual(accepted["run_status"], "completed")
        self.assertEqual((old_status, new_status), (401, 200))
        self.assertEqual(credential_provider_status, 503)
        self.assertEqual(unavailable_status, 503)
        self.assertEqual(unavailable_business_status, 503)
        self.assertEqual(unavailable["status"], "not_ready")
        ingress_events = [event for event in audit if str(event.get("type", "")).startswith("ingress_")]
        self.assertEqual(
            [event["type"] for event in ingress_events],
            [
                "ingress_authentication_denied",
                "ingress_authentication_denied",
                "ingress_authenticated",
                "ingress_authentication_denied",
                "ingress_authenticated",
            ],
        )
        serialized = json.dumps(ingress_events)
        self.assertNotIn(AUTH_TOKEN, serialized)
        self.assertNotIn(rotated_token, serialized)
        self.assertNotIn("wrong-token", serialized)

    def test_runtime_rejects_weak_or_overexposed_auth_token_file(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _service_config(root)
            config.auth_token_file.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "group or others"):
                RuntimeService(config)

            config.auth_token_file.write_text("short", encoding="utf-8")
            config.auth_token_file.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "at least 32"):
                RuntimeService(config)

    def test_runtime_rejects_symlink_token_and_non_private_runtime_directories(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _service_config(root)
            outside_token = root / "outside.token"
            outside_token.write_text(AUTH_TOKEN, encoding="utf-8")
            outside_token.chmod(0o600)
            config.auth_token_file.unlink()
            config.auth_token_file.symlink_to(outside_token)

            with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                RuntimeService(config)

            config.auth_token_file.unlink()
            config.auth_token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            config.auth_token_file.chmod(0o600)
            config.credential_dir.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "credential directory.*group or others"):
                RuntimeService(config)

            config.credential_dir.chmod(0o700)
            config.state_dir.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "state directory.*group or others"):
                RuntimeService(config)

    def test_authenticated_ingress_rejects_oversized_body_before_reading_it(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _service_config(root)
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            connection = http.client.HTTPConnection(host, port, timeout=2)
            connection.putrequest("POST", "/webhooks/workflow_service/0.1.0")
            connection.putheader("Authorization", f"Bearer {AUTH_TOKEN}")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", str(1024 * 1024 + 1))
            connection.endheaders()
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            connection.close()
            transfer_connection = http.client.HTTPConnection(host, port, timeout=2)
            transfer_connection.putrequest("POST", "/webhooks/workflow_service/0.1.0")
            transfer_connection.putheader("Authorization", f"Bearer {AUTH_TOKEN}")
            transfer_connection.putheader("Transfer-Encoding", "chunked")
            transfer_connection.endheaders()
            transfer_response = transfer_connection.getresponse()
            transfer_payload = json.loads(transfer_response.read().decode("utf-8"))
            transfer_connection.close()
            holder["service"].begin_shutdown()
            thread.join(timeout=3)

        self.assertEqual(response.status, 413)
        self.assertEqual(payload, {"error": "request body exceeds 1048576 bytes"})
        self.assertEqual(transfer_response.status, 400)
        self.assertEqual(transfer_payload, {"error": "transfer encoding is not supported"})

    def test_authenticated_resume_endpoint_requires_exact_decision_and_reuses_audit_path(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            config = _service_config(root, state_dir=state_dir)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_approval_workflow())
            waiting = control.run_published_workflow("workflow_service_approval", "0.1.0")
            rejected = control.run_published_workflow("workflow_service_approval", "0.1.0")
            ready = threading.Event()
            holder = {}
            thread = threading.Thread(
                target=serve_runtime_service,
                kwargs={
                    "config": config,
                    "ready_callback": lambda service: (
                        holder.update({"service": service}),
                        ready.set(),
                    ),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = holder["service"].server_address
            url = f"http://{host}:{port}/runs/{waiting['run_id']}/resume"
            rejected_url = f"http://{host}:{port}/runs/{rejected['run_id']}/resume"

            denied_status, denied = _post_json(url, {"approved": True})
            extra_status, extra = _post_json(
                url,
                {"approved": True, "reason": "must-not-be-accepted"},
                token=AUTH_TOKEN,
            )
            accepted_status, accepted = _post_json(
                url,
                {"approved": True},
                token=AUTH_TOKEN,
            )
            rejected_status, rejected_payload = _post_json(
                rejected_url,
                {"approved": False},
                token=AUTH_TOKEN,
            )
            repeated_status, repeated = _post_json(
                url,
                {"approved": True},
                token=AUTH_TOKEN,
            )
            holder["service"].begin_shutdown()
            thread.join(timeout=3)
            audit = LocalControlPlane(state_dir, storage="sqlite").list_audit_events()

        self.assertEqual(denied_status, 401)
        self.assertEqual(denied, {"error": "authentication required"})
        self.assertEqual(extra_status, 400)
        self.assertEqual(extra, {"error": "run resume body must contain approved boolean"})
        self.assertEqual(accepted_status, 200)
        self.assertEqual(
            accepted,
            {"run_id": waiting["run_id"], "status": "completed", "approved": True},
        )
        self.assertEqual(rejected_status, 200)
        self.assertEqual(
            rejected_payload,
            {"run_id": rejected["run_id"], "status": "failed", "approved": False},
        )
        self.assertEqual(repeated_status, 409)
        self.assertEqual(repeated, {"error": "run is not waiting"})
        resume_auth_events = [
            event for event in audit if event.get("route") == "run_resume"
        ]
        self.assertEqual(
            [event["type"] for event in resume_auth_events],
            [
                "ingress_authentication_denied",
                "ingress_authenticated",
                "ingress_authenticated",
                "ingress_authenticated",
                "ingress_authenticated",
            ],
        )
        self.assertEqual([event["type"] for event in audit].count("run_resumed"), 2)
        serialized = json.dumps(audit)
        self.assertNotIn("must-not-be-accepted", serialized)

    def test_real_process_smoke_proves_sigterm_and_restart_continuity(self):
        with TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/service_boundary_smoke.py",
                    "--work-dir",
                    str(Path(tmp) / "smoke"),
                ],
                cwd=str(Path(__file__).resolve().parents[1]),
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertTrue(evidence["checks"]["graceful_sigterm"])
        self.assertTrue(evidence["checks"]["sqlite_restart_continuity"])

    def test_connector_credentials_are_resolved_from_directory_for_each_execution(self):
        receiver = _CredentialReceiver()
        try:
            with TemporaryDirectory() as tmp:
                root = Path(tmp)
                state_dir = root / "state"
                config = _service_config(root, state_dir=state_dir)
                credential_file = config.credential_dir / "demo_api_token"
                credential_file.write_text("first-connector-secret", encoding="utf-8")
                credential_file.chmod(0o600)
                control = LocalControlPlane(state_dir, storage="sqlite")
                control.publish_workflow(_credential_workflow(receiver.url))
                ready = threading.Event()
                holder = {}
                thread = threading.Thread(
                    target=serve_runtime_service,
                    kwargs={
                        "config": config,
                        "ready_callback": lambda service: (
                            holder.update({"service": service}),
                            ready.set(),
                        ),
                    },
                    daemon=True,
                )
                thread.start()
                self.assertTrue(ready.wait(timeout=2))
                host, port = holder["service"].server_address
                url = f"http://{host}:{port}/webhooks/workflow_service_credential/0.1.0"

                first_status, _ = _post_json(url, {}, token=AUTH_TOKEN)
                credential_file.write_text("rotated-connector-secret", encoding="utf-8")
                second_status, _ = _post_json(
                    url,
                    {"idempotency_key": "credential-rotation"},
                    token=AUTH_TOKEN,
                )
                holder["service"].begin_shutdown()
                thread.join(timeout=3)
                persisted = json.dumps(
                    {
                        "runs": LocalControlPlane(state_dir, storage="sqlite").list_runs(),
                        "audit": LocalControlPlane(state_dir, storage="sqlite").list_audit_events(),
                    }
                )
        finally:
            receiver.close()

        self.assertEqual((first_status, second_status), (200, 200))
        self.assertEqual(
            receiver.authorization_headers,
            ["Bearer first-connector-secret", "Bearer rotated-connector-secret"],
        )
        self.assertNotIn("first-connector-secret", persisted)
        self.assertNotIn("rotated-connector-secret", persisted)

    def test_real_process_security_smoke_proves_auth_and_credential_rotation(self):
        with TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/security_boundary_smoke.py",
                    "--work-dir",
                    str(Path(tmp) / "smoke"),
                ],
                cwd=str(Path(__file__).resolve().parents[1]),
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertTrue(evidence["checks"]["unauthenticated_denied"])
        self.assertTrue(evidence["checks"]["ingress_token_rotation"])
        self.assertTrue(evidence["checks"]["execution_time_credential_rotation"])
        serialized = json.dumps(evidence)
        self.assertNotIn("first-connector-token", serialized)

    def test_real_process_recurring_scheduler_smoke_proves_recovery_and_takeover(self):
        with TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/recurring_scheduler_smoke.py",
                    "--work-dir",
                    str(Path(tmp) / "smoke"),
                ],
                cwd=str(Path(__file__).resolve().parents[1]),
                check=False,
                capture_output=True,
                text=True,
                timeout=25,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertTrue(evidence["checks"]["restart_recovery"])
        self.assertTrue(evidence["checks"]["latest_missed_run_coalesced"])
        self.assertTrue(evidence["checks"]["single_owner_readiness"])
        self.assertTrue(evidence["checks"]["standby_takeover"])
        self.assertTrue(evidence["checks"]["stale_claim_uncertain"])

    def test_real_process_live_control_snapshot_smoke_is_private_and_read_only(self):
        with TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/live_control_snapshot_smoke.py",
                    "--work-dir",
                    str(Path(tmp) / "smoke"),
                ],
                cwd=str(Path(__file__).resolve().parents[1]),
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertTrue(evidence["checks"]["unauthenticated_denied"])
        self.assertTrue(evidence["checks"]["authenticated_cli_fetch"])
        self.assertTrue(evidence["checks"]["bounded_contract"])
        self.assertTrue(evidence["checks"]["persisted_state_unchanged"])
        self.assertTrue(evidence["checks"]["owner_only_output"])
        self.assertTrue(evidence["checks"]["fixed_observability"])
        self.assertNotIn(AUTH_TOKEN, result.stdout)


def _run_service_and_trigger(root: Path, state_dir: Path, idempotency_key: str):
    ready = threading.Event()
    address = {}
    holder = {}
    thread = threading.Thread(
        target=serve_runtime_service,
        kwargs={
            "config": _service_config(root, state_dir=state_dir),
            "ready_callback": lambda service: (
                holder.update({"service": service}),
                address.update({"value": service.server_address}),
                ready.set(),
            ),
        },
        daemon=True,
    )
    thread.start()
    if not ready.wait(timeout=2):
        raise AssertionError("service did not become ready")
    host, port = address["value"]
    body = json.dumps(
        {"source": "self-hosted-service", "idempotency_key": idempotency_key}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://{host}:{port}/webhooks/workflow_service/0.1.0",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    request.add_header("Authorization", f"Bearer {AUTH_TOKEN}")
    with urllib.request.urlopen(request, timeout=2) as response:
        result = json.loads(response.read().decode("utf-8"))
    holder["service"].begin_shutdown()
    thread.join(timeout=3)
    if thread.is_alive():
        raise AssertionError("service did not stop gracefully")
    return result


def _get_json(url: str, token=None):
    request = urllib.request.Request(url)
    if token is not None:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        finally:
            error.close()


def _get_raw_get(url: str, token=None, body=b""):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        finally:
            error.close()


def _post_json(url: str, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        finally:
            error.close()


def _get_raw(url: str, token=None):
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return (
                response.status,
                response.headers.get("Content-Type", ""),
                response.read().decode("utf-8"),
            )
    except urllib.error.HTTPError as error:
        try:
            return (
                error.code,
                error.headers.get("Content-Type", ""),
                error.read().decode("utf-8"),
            )
        finally:
            error.close()


def _service_config(root: Path, state_dir=None):
    token_file = root / "ingress.token"
    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
    token_file.chmod(0o600)
    credential_dir = root / "credentials"
    credential_dir.mkdir(exist_ok=True)
    credential_dir.chmod(0o700)
    selected_state_dir = state_dir or root / "state"
    selected_state_dir.mkdir(parents=True, exist_ok=True)
    selected_state_dir.chmod(0o700)
    return ServiceConfig(
        "127.0.0.1",
        0,
        selected_state_dir,
        "sqlite",
        token_file,
        credential_dir,
    )


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_service",
            "name": "service continuity",
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


def _approval_workflow():
    workflow = _workflow()
    workflow["workflow"]["id"] = "workflow_service_approval"
    workflow["nodes"] = [
        {"id": "start", "type": "start", "title": "Start", "on_success": "review"},
        {
            "id": "review",
            "type": "human_gate",
            "title": "Review",
            "on_success": "end",
            "on_failure": "failure",
        },
        {"id": "failure", "type": "failure", "title": "Failure"},
        {"id": "end", "type": "end", "title": "End"},
    ]
    workflow["edges"] = [
        {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
        {"id": "edge_review_end", "from": "review", "to": "end", "label": "next"},
        {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "failure"},
    ]
    return workflow


def _credential_workflow(url: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_service_credential",
            "name": "service credential rotation",
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


class _CredentialReceiver:
    def __init__(self):
        self.authorization_headers = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                owner.authorization_headers.append(self.headers.get("Authorization", ""))
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
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
