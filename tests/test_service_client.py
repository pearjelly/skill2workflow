import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.service_client import (
    MAX_SERVICE_ACTION_RESPONSE_BYTES,
    MAX_SUPPORT_BUNDLE_RESPONSE_BYTES,
    MAX_AUDIT_CONSISTENCY_RESPONSE_BYTES,
    MAX_RECURRING_SCHEDULE_LIST_RESPONSE_BYTES,
    MAX_RECURRING_SCHEDULE_DISPATCH_LIST_RESPONSE_BYTES,
    MAX_RECURRING_SCHEDULE_DISPATCH_PAGE_RESPONSE_BYTES,
    MAX_RECURRING_SCHEDULE_DISPATCH_REVIEW_RESPONSE_BYTES,
    MAX_WORKFLOW_ARTIFACT_REPORT_RESPONSE_BYTES,
    MAX_BACKUP_READINESS_RESPONSE_BYTES,
    MAX_REMOTE_BACKUP_INVENTORY_RESPONSE_BYTES,
    MAX_REMOTE_BACKUP_INVENTORY_PAGE_RESPONSE_BYTES,
    MAX_REMOTE_BACKUP_RETENTION_PLAN_RESPONSE_BYTES,
    MAX_RETENTION_READINESS_RESPONSE_BYTES,
    MAX_OPERATIONAL_READINESS_RESPONSE_BYTES,
    SERVICE_PROBE_SCHEMA_VERSION,
    SERVICE_WAIT_MAX_POLL_INTERVAL_SECONDS,
    SERVICE_WAIT_MAX_TIMEOUT_SECONDS,
    MAX_AUDIT_INTEGRITY_RESPONSE_BYTES,
    MAX_RUNTIME_INFO_RESPONSE_BYTES,
    MAX_REMOTE_TRIGGER_REQUEST_BYTES,
    MAX_REMOTE_WORKFLOW_RELEASE_REQUEST_BYTES,
    ServiceActionError,
    post_recurring_schedule_state,
    post_recurring_schedule_create,
    put_recurring_schedule_update,
    patch_recurring_schedule,
    delete_recurring_schedule,
    post_run_cancel,
    post_run_resume,
    fetch_run_detail,
    fetch_run_list,
    fetch_run_page,
    fetch_audit_events,
    fetch_recurring_schedule_list,
    fetch_recurring_schedule_dispatches,
    fetch_recurring_schedule_dispatch_page,
    fetch_recurring_schedule_dispatch_review,
    post_recurring_schedule_dispatch_review,
    fetch_workflow_artifact_report,
    fetch_workflow_inventory,
    fetch_backup_readiness,
    fetch_backup_inventory,
    fetch_backup_inventory_page,
    fetch_backup_retention_plan,
    fetch_retention_readiness,
    fetch_operational_readiness,
    fetch_service_probe,
    wait_for_service_ready,
    fetch_audit_integrity,
    fetch_runtime_info,
    fetch_support_bundle,
    fetch_audit_consistency,
    post_workflow_trigger,
    post_workflow_release,
    post_workflow_promotion,
    post_workflow_deprecation,
    fetch_workflow_diff,
)


AUTH_TOKEN = "service-client-test-token-0123456789abcdef"
RUN_ID = "run_service_client_001"


class ServiceClientTests(TestCase):
    def test_recurring_schedule_delete_uses_authenticated_delete_and_validates_contract(self):
        observed = {}

        class Handler(BaseHTTPRequestHandler):
            def do_DELETE(self):
                observed["path"] = self.path
                observed["method"] = self.command
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                )
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-recurring-schedule-delete-0.1.0",
                        "schedule_id": "schedule_hourly_report",
                        "deleted": True,
                    },
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = delete_recurring_schedule(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "schedule_hourly_report",
                expected_next_run_at="2026-08-11T00:00:00+00:00",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertTrue(result["deleted"])
        self.assertEqual(observed["method"], "DELETE")
        self.assertEqual(
            observed["path"],
            "/api/v1/recurring-schedules/schedule_hourly_report",
        )
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertEqual(
            observed["body"],
            {
                "expected_next_run_at": "2026-08-11T00:00:00+00:00",
                "confirm": True,
            },
        )
        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_delete_rejects_missing_precondition_before_network(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaises(ValueError):
                delete_recurring_schedule(
                    "https://service.example",
                    token_file,
                    "schedule_hourly_report",
                    expected_next_run_at="",
                )

    def test_recurring_schedule_update_uses_authenticated_put_and_validates_redacted_contract(self):
        observed = {}
        definition = _recurring_definition()
        definition["schedule"].update(
            {
                "workflow_id": "workflow_recurring_v2",
                "version": "2.0.0",
                "interval_seconds": 120,
            }
        )
        definition["trigger"]["input"] = {"report": "updated"}

        class Handler(BaseHTTPRequestHandler):
            def do_PUT(self):
                observed["path"] = self.path
                observed["method"] = self.command
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                )
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-recurring-schedule-update-0.1.0",
                        "schedule_id": "schedule_hourly_report",
                        "workflow_id": "workflow_recurring_v2",
                        "workflow_version": "2.0.0",
                        "status": "active",
                        "enabled": True,
                        "starts_at": "2026-08-11T00:00:00+00:00",
                        "next_run_at": "2026-08-11T00:01:00+00:00",
                        "interval_seconds": 120,
                        "missed_run_policy": "latest",
                        "changed": True,
                    },
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = put_recurring_schedule_update(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "schedule_hourly_report",
                definition,
                expected_next_run_at="2026-08-11T00:00:00+00:00",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertTrue(result["changed"])
        self.assertEqual(observed["method"], "PUT")
        self.assertEqual(observed["path"], "/api/v1/recurring-schedules/schedule_hourly_report")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertEqual(
            observed["body"],
            {
                "schedule": definition,
                "expected_next_run_at": "2026-08-11T00:00:00+00:00",
            },
        )
        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_update_rejects_missing_precondition_before_network(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaises(ValueError):
                put_recurring_schedule_update(
                    "https://service.example",
                    token_file,
                    "schedule_hourly_report",
                    _recurring_definition(),
                    expected_next_run_at="",
                )

    def test_recurring_schedule_patch_uses_authenticated_patch_and_rejects_trigger_input(self):
        observed = {}
        patch_fields = {"workflow_id": "workflow_recurring_v2", "version": "2.0.0", "interval_seconds": 120}

        class Handler(BaseHTTPRequestHandler):
            def do_PATCH(self):
                observed["path"] = self.path
                observed["method"] = self.command
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                )
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-recurring-schedule-patch-0.1.0",
                        "schedule_id": "schedule_hourly_report",
                        "workflow_id": "workflow_recurring_v2",
                        "workflow_version": "2.0.0",
                        "status": "active",
                        "enabled": True,
                        "starts_at": "2026-08-11T00:00:00+00:00",
                        "next_run_at": "2026-08-11T00:01:00+00:00",
                        "interval_seconds": 120,
                        "missed_run_policy": "latest",
                        "changed": True,
                    },
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = patch_recurring_schedule(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "schedule_hourly_report",
                patch_fields,
                expected_next_run_at="2026-08-11T00:00:00+00:00",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertTrue(result["changed"])
        self.assertEqual(observed["method"], "PATCH")
        self.assertEqual(observed["path"], "/api/v1/recurring-schedules/schedule_hourly_report")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertEqual(
            observed["body"],
            {
                "schedule": patch_fields,
                "expected_next_run_at": "2026-08-11T00:00:00+00:00",
            },
        )
        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_patch_rejects_trigger_and_empty_patch_before_network(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaises(ValueError):
                patch_recurring_schedule(
                    "https://service.example",
                    token_file,
                    "schedule_hourly_report",
                    {"trigger": {"input": {"private": "no"}}},
                    expected_next_run_at="2026-08-11T00:00:00+00:00",
                )
            with self.assertRaises(ValueError):
                patch_recurring_schedule(
                    "https://service.example",
                    token_file,
                    "schedule_hourly_report",
                    {},
                    expected_next_run_at="2026-08-11T00:00:00+00:00",
                )

    def test_recurring_schedule_create_uses_authenticated_post_and_redacted_contract(self):
        observed = {}
        definition = _recurring_definition()

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                )
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-recurring-schedule-create-0.1.0",
                        "schedule_id": "schedule_hourly_report",
                        "workflow_id": "workflow_recurring",
                        "workflow_version": "1.0.0",
                        "status": "active",
                        "enabled": True,
                        "starts_at": "2026-08-11T00:00:00+00:00",
                        "next_run_at": "2026-08-11T00:00:00+00:00",
                        "interval_seconds": 60,
                        "missed_run_policy": "latest",
                        "created": True,
                    },
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = post_recurring_schedule_create(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                definition,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertTrue(result["created"])
        self.assertEqual(observed["path"], "/api/v1/recurring-schedules")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertEqual(observed["body"], {"schedule": definition})
        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_create_rejects_invalid_definition_before_network(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaises(ValueError):
                post_recurring_schedule_create(
                    "https://service.example",
                    token_file,
                    {"schedule": "not-a-definition"},
                )

    def test_recurring_schedule_create_accepts_replay_with_advanced_progress(self):
        definition = _recurring_definition()

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-recurring-schedule-create-0.1.0",
                        "schedule_id": "schedule_hourly_report",
                        "workflow_id": "workflow_recurring",
                        "workflow_version": "1.0.0",
                        "status": "active",
                        "enabled": True,
                        "starts_at": "2026-08-11T00:00:00+00:00",
                        "next_run_at": "2026-08-11T01:00:00+00:00",
                        "interval_seconds": 60,
                        "missed_run_policy": "latest",
                        "created": False,
                    },
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = post_recurring_schedule_create(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                definition,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(result["created"])
        self.assertEqual(result["next_run_at"], "2026-08-11T01:00:00+00:00")
        self.assertFalse(thread.is_alive())

    def test_audit_event_page_uses_authenticated_get_and_validates_contract(self):
        observed = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append({"path": self.path, "authorization": self.headers.get("Authorization")})
                _send_json(
                    self,
                    200,
                    _audit_event_page_fixture(),
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            page = fetch_audit_events(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                max_items=10,
                cursor="cursor-token",
                workflow_id="workflow",
                workflow_version="0.1.0",
                run_id=RUN_ID,
                event_type="connector_failed",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(page["schema_version"], "skill2workflow-audit-event-list-0.1.0")
        self.assertEqual(observed[0]["authorization"], f"Bearer {AUTH_TOKEN}")
        for value in ("max_items=10", "cursor=cursor-token", "workflow_id=workflow", "event_type=connector_failed"):
            self.assertIn(value, observed[0]["path"])
        self.assertFalse(thread.is_alive())

    def test_audit_event_page_rejects_unsafe_filter_before_network_access(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaises(ValueError):
                fetch_audit_events("https://service.example", token_file, event_type="bad\nvalue")
    def test_run_page_uses_authenticated_get_with_filters_and_cursor(self):
        observed = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append({"path": self.path, "authorization": self.headers.get("Authorization")})
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-run-list-0.2.0",
                        "summary": {
                            "total": 1,
                            "status_counts": {
                                "created": 0, "running": 0, "waiting": 0,
                                "completed": 0, "failed": 1, "cancelled": 0,
                                "interrupted": 0, "other": 0,
                            },
                        },
                        "filters": {"status": "failed", "workflow_id": "workflow"},
                        "runs": [],
                        "window": {
                            "max_items": 10, "total": 1, "returned": 0,
                            "has_more": True, "next_cursor": "cursor-token",
                        },
                    },
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            page = fetch_run_page(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                status="failed",
                workflow_id="workflow",
                cursor="cursor-token",
                max_items=10,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(page["schema_version"], "skill2workflow-run-list-0.2.0")
        self.assertEqual(observed[0]["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertIn("status=failed", observed[0]["path"])
        self.assertIn("workflow_id=workflow", observed[0]["path"])
        self.assertIn("cursor=cursor-token", observed[0]["path"])
        self.assertFalse(thread.is_alive())

    def test_service_probe_returns_fixed_ready_contract_without_credentials(self):
        observed = []
        responses = {
            "/healthz": (200, {"service": "skill2workflow", "status": "ok"}),
            "/readyz": (
                200,
                {"service": "skill2workflow", "status": "ready", "storage": "sqlite"},
            ),
        }

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {"path": self.path, "authorization": self.headers.get("Authorization")}
                )
                status_code, payload = responses[self.path]
                _send_json(self, status_code, payload)

            def log_message(self, *_args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(
            target=lambda: [server.handle_request() for _ in range(2)], daemon=True
        )
        thread.start()
        report = fetch_service_probe(f"http://127.0.0.1:{server.server_port}")
        thread.join(timeout=2)
        server.server_close()

        self.assertEqual(
            report,
            {
                "schema_version": SERVICE_PROBE_SCHEMA_VERSION,
                "status": "ready",
                "health": {"status": "ok", "http_status": 200},
                "readiness": {"status": "ready", "http_status": 200},
            },
        )
        self.assertEqual([item["path"] for item in observed], ["/healthz", "/readyz"])
        self.assertTrue(all(item["authorization"] is None for item in observed))
        self.assertFalse(thread.is_alive())

    def test_service_probe_distinguishes_not_ready_from_unavailable(self):
        responses = {
            "/healthz": (200, {"service": "skill2workflow", "status": "ok"}),
            "/readyz": (503, {"service": "skill2workflow", "status": "not_ready"}),
        }

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                status_code, payload = responses[self.path]
                _send_json(self, status_code, payload)

            def log_message(self, *_args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(
            target=lambda: [server.handle_request() for _ in range(2)], daemon=True
        )
        thread.start()
        report = fetch_service_probe(f"http://127.0.0.1:{server.server_port}")
        thread.join(timeout=2)
        server.server_close()

        self.assertEqual(report["status"], "not_ready")
        self.assertEqual(report["health"], {"status": "ok", "http_status": 200})
        self.assertEqual(
            report["readiness"], {"status": "not_ready", "http_status": 503}
        )

    def test_service_probe_rejects_redirects_and_does_not_disclose_body(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", "https://example.invalid/secret")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *_args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(
            target=lambda: [server.handle_request() for _ in range(2)], daemon=True
        )
        thread.start()
        report = fetch_service_probe(f"http://127.0.0.1:{server.server_port}")
        thread.join(timeout=2)
        server.server_close()

        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["health"], {"status": "unavailable", "http_status": 302})
        self.assertEqual(
            report["readiness"], {"status": "unavailable", "http_status": 302}
        )
        self.assertNotIn("example.invalid", json.dumps(report))

    def test_service_probe_rejects_unsafe_origin_before_network(self):
        with self.assertRaisesRegex(ValueError, "unambiguous HTTPS"):
            fetch_service_probe("http://service.example")

    def test_service_wait_polls_until_ready_with_bounded_sleep(self):
        not_ready = {
            "schema_version": SERVICE_PROBE_SCHEMA_VERSION,
            "status": "not_ready",
            "health": {"status": "ok", "http_status": 200},
            "readiness": {"status": "not_ready", "http_status": 503},
        }
        ready = {
            "schema_version": SERVICE_PROBE_SCHEMA_VERSION,
            "status": "ready",
            "health": {"status": "ok", "http_status": 200},
            "readiness": {"status": "ready", "http_status": 200},
        }
        now = [0.0]
        sleeps = []

        def monotonic():
            return now[0]

        def sleep(seconds):
            sleeps.append(seconds)
            now[0] += seconds

        with patch(
            "skill2workflow.service_client.fetch_service_probe",
            side_effect=[not_ready, ready],
        ) as probe:
            result = wait_for_service_ready(
                "http://127.0.0.1:8080",
                timeout_seconds=5,
                poll_interval_seconds=2,
                monotonic=monotonic,
                sleep=sleep,
            )

        self.assertEqual(result, ready)
        self.assertEqual(probe.call_count, 2)
        self.assertEqual(sleeps, [2.0])

    def test_service_wait_returns_last_not_ready_probe_at_deadline(self):
        not_ready = {
            "schema_version": SERVICE_PROBE_SCHEMA_VERSION,
            "status": "not_ready",
            "health": {"status": "ok", "http_status": 200},
            "readiness": {"status": "not_ready", "http_status": 503},
        }
        now = [0.0]
        sleeps = []

        with patch(
            "skill2workflow.service_client.fetch_service_probe",
            side_effect=[not_ready, not_ready, not_ready],
        ) as probe:
            result = wait_for_service_ready(
                "http://127.0.0.1:8080",
                timeout_seconds=3,
                poll_interval_seconds=2,
                monotonic=lambda: now[0],
                sleep=lambda seconds: (sleeps.append(seconds), now.__setitem__(0, now[0] + seconds)),
            )

        self.assertEqual(result, not_ready)
        self.assertEqual(probe.call_count, 3)
        self.assertEqual(sleeps, [2.0, 1.0])

    def test_service_wait_rejects_unbounded_timing_options(self):
        with self.assertRaisesRegex(ValueError, "timeout_seconds"):
            wait_for_service_ready(
                "http://127.0.0.1:8080",
                timeout_seconds=SERVICE_WAIT_MAX_TIMEOUT_SECONDS + 1,
            )
        with self.assertRaisesRegex(ValueError, "poll_interval_seconds"):
            wait_for_service_ready(
                "http://127.0.0.1:8080",
                poll_interval_seconds=SERVICE_WAIT_MAX_POLL_INTERVAL_SECONDS + 1,
            )
        with self.assertRaisesRegex(ValueError, "greater than 0"):
            wait_for_service_ready(
                "http://127.0.0.1:8080",
                poll_interval_seconds=0,
            )

    def test_service_workflow_inventory_uses_fixed_redacted_contract(self):
        observed = {}
        payload = {
            "schema_version": "skill2workflow-workflow-inventory-0.1.0",
            "summary": {
                "total": 1,
                "status_counts": {"published": 1, "deprecated": 0, "other": 0},
            },
            "versions": [
                {
                    "workflow_id": "workflow_remote_release",
                    "version": "1.2.3",
                    "status": "published",
                    "aliases": ["production"],
                    "checksum": "a" * 64,
                }
            ],
            "window": {"max_items": 100, "total": 1, "returned": 1, "truncated": False},
        }

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                observed["content_length"] = self.headers.get("Content-Length")
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_workflow_inventory(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(observed["path"], "/api/v1/workflows")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertFalse(thread.is_alive())

    def test_service_workflow_diff_uses_fixed_redacted_contract(self):
        observed = {}
        payload = {
            "schema_version": "skill2workflow-workflow-diff-0.1.0",
            "workflow_id": "workflow_remote_release",
            "from": {
                "version": "1.2.2",
                "status": "published",
                "checksum": "a" * 64,
                "aliases": ["production"],
            },
            "to": {
                "version": "1.2.3",
                "status": "published",
                "checksum": "b" * 64,
                "aliases": [],
            },
            "changed": True,
            "changes": {
                "sections": ["workflow", "policies", "nodes"],
                "workflow_changed": True,
                "entry_changed": False,
                "input_schema_changed": False,
                "policies_changed": False,
                "other_changed": False,
                "nodes": {"added": ["review"], "removed": [], "changed": []},
                "edges": {"added": [], "removed": [], "changed": []},
            },
        }

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = self.rfile.read(0)
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_workflow_diff(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "workflow_remote_release",
                "1.2.2",
                "1.2.3",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(
            observed["path"],
            "/api/v1/workflow-diffs/workflow_remote_release/1.2.2/1.2.3",
        )
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertFalse(thread.is_alive())

    def test_service_workflow_deprecate_uses_fixed_redacted_contract(self):
        observed = {}
        payload = {
            "schema_version": "skill2workflow-workflow-deprecation-0.1.0",
            "workflow_id": "workflow_remote_release",
            "version": "1.2.2",
            "status": "deprecated",
            "checksum": "a" * 64,
        }

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = post_workflow_deprecation(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "workflow_remote_release",
                "1.2.2",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(observed["path"], "/api/v1/workflow-deprecations")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertEqual(
            observed["body"],
            {"workflow_id": "workflow_remote_release", "version": "1.2.2"},
        )
        self.assertFalse(thread.is_alive())

    def test_service_workflow_deprecate_sends_compare_and_swap_metadata(self):
        observed = {}
        payload = {
            "schema_version": "skill2workflow-workflow-deprecation-0.1.0",
            "workflow_id": "workflow_remote_release",
            "version": "1.2.2",
            "status": "deprecated",
            "checksum": "a" * 64,
        }

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["body"] = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = post_workflow_deprecation(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "workflow_remote_release",
                "1.2.2",
                expected_checksum="a" * 64,
                expected_aliases=[],
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(
            observed["body"],
            {
                "workflow_id": "workflow_remote_release",
                "version": "1.2.2",
                "expected_checksum": "a" * 64,
                "expected_aliases": [],
            },
        )
        self.assertFalse(thread.is_alive())

    def test_service_workflow_deprecate_rejects_incomplete_compare_and_swap(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "precondition is incomplete"):
                post_workflow_deprecation(
                    "https://service.example",
                    token_file,
                    "workflow_remote_release",
                    "1.2.2",
                    expected_checksum="a" * 64,
                )

    def test_service_workflow_deprecate_rejects_unsafe_reference_before_network(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "workflow_id"):
                post_workflow_deprecation(
                    "https://service.example",
                    token_file,
                    "workflow/unsafe",
                    "1.2.3",
                )

    def test_service_workflow_diff_rejects_unsafe_reference_before_network(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "safe workflow identifier"):
                fetch_workflow_diff(
                    "https://service.example",
                    token_file,
                    "workflow/unsafe",
                    "1.0.0",
                    "2.0.0",
                )

    def test_service_workflow_promote_uses_fixed_contract(self):
        observed = {}
        payload = {
            "schema_version": "skill2workflow-workflow-promotion-0.1.0",
            "workflow_id": "workflow_remote_release",
            "version": "1.2.3",
            "alias": "production",
            "status": "promoted",
            "checksum": "b" * 64,
        }

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = post_workflow_promotion(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "workflow_remote_release",
                "1.2.3",
                alias="production",
                expected_current_version="1.2.2",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(observed["path"], "/api/v1/workflow-promotions")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertEqual(
            observed["body"],
            {
                "workflow_id": "workflow_remote_release",
                "version": "1.2.3",
                "alias": "production",
                "expected_current_version": "1.2.2",
            },
        )
        self.assertFalse(thread.is_alive())

    def test_service_workflow_promote_rejects_unsafe_alias_before_network(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "workflow alias"):
                post_workflow_promotion(
                    "https://service.example",
                    token_file,
                    "workflow_remote_release",
                    "1.2.3",
                    alias="../production",
                )

    def test_service_workflow_publish_uses_fixed_contract(self):
        observed = {}
        payload = {
            "schema_version": "skill2workflow-workflow-release-0.1.0",
            "workflow_id": "workflow_remote_release",
            "version": "1.2.3",
            "status": "published",
            "checksum": "a" * 64,
        }

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        workflow = _workflow_document()
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = post_workflow_release(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                workflow,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(observed["path"], "/api/v1/workflow-releases")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertEqual(observed["body"], {"workflow": workflow})
        self.assertFalse(thread.is_alive())

    def test_service_workflow_publish_rejects_oversized_request_before_network(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            workflow = _workflow_document()
            workflow["description"] = "x" * MAX_REMOTE_WORKFLOW_RELEASE_REQUEST_BYTES
            with self.assertRaises(ServiceActionError) as raised:
                post_workflow_release("https://service.example", token_file, workflow)

        self.assertEqual(raised.exception.status_code, 413)

    def test_service_trigger_posts_bounded_idempotent_envelope(self):
        observed = {}
        payload = {
            "trigger_id": "trigger_remote_001",
            "workflow_id": "workflow_remote",
            "workflow_version": "0.1.0",
            "run_id": "run_remote_001",
            "run_status": "waiting",
            "source": "service-cli",
            "idempotency_key": "remote-001",
            "input_keys": ["customer_id"],
        }

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = post_workflow_trigger(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "workflow_remote",
                "production",
                idempotency_key="remote-001",
                trigger_input={"customer_id": "customer_123"},
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(observed["path"], "/webhooks/workflow_remote/production")
        self.assertEqual(
            observed["authorization"], f"Bearer {AUTH_TOKEN}"
        )
        self.assertEqual(
            observed["body"],
            {
                "source": "service-cli",
                "idempotency_key": "remote-001",
                "input": {"customer_id": "customer_123"},
            },
        )
        self.assertFalse(thread.is_alive())

    def test_service_trigger_requires_idempotency_and_rejects_unsafe_path_before_network(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "idempotency_key is required"):
                post_workflow_trigger(
                    "https://service.example",
                    token_file,
                    "workflow_remote",
                    "0.1.0",
                    idempotency_key="",
                )
            with self.assertRaisesRegex(ValueError, "safe workflow identifier"):
                post_workflow_trigger(
                    "https://service.example",
                    token_file,
                    "../private",
                    "0.1.0",
                    idempotency_key="remote-001",
                )

    def test_service_trigger_rejects_oversized_complete_body_before_network(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaises(ServiceActionError) as raised:
                post_workflow_trigger(
                    "https://service.example",
                    token_file,
                    "workflow_remote",
                    "0.1.0",
                    idempotency_key="oversize-001",
                    trigger_input={
                        "value": "x" * (MAX_REMOTE_TRIGGER_REQUEST_BYTES - 60)
                    },
                )

        self.assertEqual(raised.exception.status_code, 413)

    def test_audit_consistency_uses_authenticated_get_and_validates_contract(self):
        observed = []
        payload = _audit_consistency_payload()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_audit_consistency(
                f"http://127.0.0.1:{server.server_port}", token_file
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(
            observed,
            [{"path": "/api/v1/audit-consistency", "authorization": f"Bearer {AUTH_TOKEN}"}],
        )
        self.assertFalse(thread.is_alive())

    def test_audit_consistency_rejects_oversized_response(self):
        body = b"x" * (MAX_AUDIT_CONSISTENCY_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_audit_consistency(f"http://127.0.0.1:{server.server_port}", token_file)
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_audit_consistency_can_target_one_safe_run_id(self):
        observed = []
        payload = _audit_consistency_payload()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(self.path)
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_audit_consistency(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                run_id=RUN_ID,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(observed, [f"/api/v1/audit-consistency/{RUN_ID}"])
        self.assertFalse(thread.is_alive())

    def test_audit_consistency_rejects_unsafe_target_before_network_access(self):
        contacted = threading.Event()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                contacted.set()
                _send_json(self, 200, _audit_consistency_payload())

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            with self.assertRaises(ValueError):
                fetch_audit_consistency(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    run_id="../private",
                )
            server.server_close()

        self.assertFalse(contacted.is_set())
    def test_support_bundle_uses_authenticated_get_and_validates_contract(self):
        observed = []
        payload = _support_bundle_payload()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            bundle = fetch_support_bundle(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(bundle, payload)
        self.assertEqual(
            observed,
            [
                {
                    "path": "/api/v1/support-bundle",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                }
            ],
        )
        self.assertFalse(thread.is_alive())

    def test_support_bundle_rejects_oversized_response(self):
        body = b"x" * (MAX_SUPPORT_BUNDLE_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_support_bundle(f"http://127.0.0.1:{server.server_port}", token_file)
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_run_list_uses_authenticated_get_and_validates_contract(self):
        observed = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-run-list-0.1.0",
                        "summary": {
                            "total": 1,
                            "status_counts": {
                                "created": 0,
                                "running": 0,
                                "waiting": 1,
                                "completed": 0,
                                "failed": 0,
                                "cancelled": 0,
                                "interrupted": 0,
                                "other": 0,
                            },
                        },
                        "runs": [
                            {
                                "run_id": RUN_ID,
                                "workflow_id": "workflow",
                                "workflow_version": "0.1.0",
                                "status": "waiting",
                                "current_node": "review",
                                "event_count": 2,
                                "node_result_count": 0,
                            }
                        ],
                        "window": {
                            "max_items": 100,
                            "total": 1,
                            "returned": 1,
                            "truncated": False,
                        },
                    },
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            listing = fetch_run_list(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(listing["runs"][0]["run_id"], RUN_ID)
        self.assertEqual(
            observed,
            [
                {
                    "path": "/runs",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                }
            ],
        )
        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_list_uses_authenticated_get_and_validates_contract(self):
        observed = []
        payload = _recurring_schedule_list_payload()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            listing = fetch_recurring_schedule_list(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(listing, payload)
        self.assertEqual(
            observed,
            [{
                "path": "/api/v1/recurring-schedules",
                "authorization": f"Bearer {AUTH_TOKEN}",
            }],
        )
        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_list_rejects_oversized_response(self):
        body = b"x" * (MAX_RECURRING_SCHEDULE_LIST_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_recurring_schedule_list(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_workflow_artifact_report_uses_authenticated_get_and_validates_contract(self):
        observed = []
        payload = _workflow_artifact_report_payload()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_workflow_artifact_report(
                f"http://127.0.0.1:{server.server_port}", token_file
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(
            observed,
            [{
                "path": "/api/v1/workflow-artifacts",
                "authorization": f"Bearer {AUTH_TOKEN}",
            }],
        )
        self.assertFalse(thread.is_alive())

    def test_workflow_artifact_report_rejects_oversized_response(self):
        body = b"x" * (MAX_WORKFLOW_ARTIFACT_REPORT_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_workflow_artifact_report(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_backup_readiness_uses_authenticated_get_and_validates_contract(self):
        observed = []
        payload = _backup_readiness_payload()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_backup_readiness(
                f"http://127.0.0.1:{server.server_port}", token_file
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(
            observed,
            [{
                "path": "/api/v1/backup-readiness",
                "authorization": f"Bearer {AUTH_TOKEN}",
            }],
        )
        self.assertFalse(thread.is_alive())

    def test_backup_readiness_rejects_oversized_response(self):
        body = b"x" * (MAX_BACKUP_READINESS_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_backup_readiness(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_backup_inventory_uses_authenticated_get_and_validates_contract(self):
        observed = []
        payload = _backup_inventory_payload()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_backup_inventory(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                max_items=7,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(
            observed,
            [{
                "path": "/api/v1/backup-inventory?max_items=7",
                "authorization": f"Bearer {AUTH_TOKEN}",
            }],
        )
        self.assertFalse(thread.is_alive())

    def test_backup_inventory_rejects_oversized_response(self):
        body = b"x" * (MAX_REMOTE_BACKUP_INVENTORY_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_backup_inventory(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_backup_inventory_page_uses_authenticated_get_and_validates_contract(self):
        observed = []
        payload = _backup_inventory_page_payload()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_backup_inventory_page(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                max_items=7,
                cursor="cursor-token",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(
            observed,
            [{
                "path": "/api/v1/backup-inventory-pages?max_items=7&cursor=cursor-token",
                "authorization": f"Bearer {AUTH_TOKEN}",
            }],
        )
        self.assertFalse(thread.is_alive())

    def test_backup_inventory_page_rejects_oversized_response(self):
        body = b"x" * (MAX_REMOTE_BACKUP_INVENTORY_PAGE_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_backup_inventory_page(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_backup_retention_plan_posts_authenticated_policy_and_validates_contract(self):
        observed = {}
        payload = _backup_retention_plan_payload()
        policy = {"schema_version": "skill2workflow-backup-retention-policy-0.1.0"}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_backup_retention_plan(
                f"http://127.0.0.1:{server.server_port}", token_file, policy
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(observed["path"], "/api/v1/backup-retention-plan")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertEqual(observed["body"], {"policy": policy})
        self.assertFalse(thread.is_alive())

    def test_backup_retention_plan_rejects_oversized_response(self):
        body = b"x" * (MAX_REMOTE_BACKUP_RETENTION_PLAN_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_backup_retention_plan(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    {},
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_retention_readiness_posts_policy_and_validates_fixed_contract(self):
        policy = {
            "schema_version": "skill2workflow-retention-policy-0.3.0",
            "retention": {
                "delete_before": "2026-01-01T00:00:00+00:00",
                "terminal_run_statuses": ["completed", "failed", "cancelled", "interrupted"],
                "terminal_dispatch_statuses": ["completed", "failed", "skipped", "uncertain"],
            },
        }
        payload = {
            "schema_version": "skill2workflow-retention-readiness-0.1.0",
            "status": "blocked",
            "storage": "sqlite",
            "state_layout_version": "skill2workflow-sqlite-layout-0.1.0",
            "active_scheduler_lease": True,
            "plan_available": False,
            "policy_sha256": "a" * 64,
            "delete_before": "2026-01-01T00:00:00+00:00",
            "eligible": {
                "terminal_runs": None,
                "run_events": None,
                "run_cancellations": None,
                "run_executions": None,
                "run_audit_events": None,
                "terminal_dispatches": None,
            },
            "preserved": {"nonterminal_runs": None, "claimed_dispatches": None},
            "blocking_reasons": ["active_scheduler_lease"],
        }
        observed = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                observed["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_retention_readiness(
                f"http://127.0.0.1:{server.server_port}", token_file, policy
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(observed["path"], "/api/v1/retention-readiness")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertEqual(observed["body"], {"policy": policy})
        self.assertFalse(thread.is_alive())

    def test_retention_readiness_rejects_oversized_response(self):
        policy = {
            "schema_version": "skill2workflow-retention-policy-0.3.0",
            "retention": {
                "delete_before": "2026-01-01T00:00:00+00:00",
                "terminal_run_statuses": ["completed", "failed", "cancelled", "interrupted"],
                "terminal_dispatch_statuses": ["completed", "failed", "skipped", "uncertain"],
            },
        }
        body = b"x" * (MAX_RETENTION_READINESS_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_retention_readiness(
                    f"http://127.0.0.1:{server.server_port}", token_file, policy
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_operational_readiness_uses_authenticated_get_and_validates_contract(self):
        payload = {
            "schema_version": "skill2workflow-operational-readiness-0.1.0",
            "status": "ready",
            "service": {
                "status": "ready",
                "ready": True,
                "storage": "sqlite",
                "state_layout_version": "skill2workflow-sqlite-layout-0.1.0",
                "scheduler_lease_owned": True,
            },
            "checks": {
                "workflow_artifacts": {"status": "clean", "issue_count": 0},
                "audit_integrity": {"status": "valid"},
                "offline_backup": {
                    "status": "blocked",
                    "active_scheduler_lease": True,
                },
            },
            "blocking_reasons": [],
            "operator_notes": ["offline_backup_requires_stop"],
        }
        observed = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_operational_readiness(
                f"http://127.0.0.1:{server.server_port}", token_file
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(observed["path"], "/api/v1/operational-readiness")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertFalse(thread.is_alive())

    def test_operational_readiness_rejects_oversized_response(self):
        body = b"x" * (MAX_OPERATIONAL_READINESS_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_operational_readiness(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_audit_integrity_uses_authenticated_get_and_validates_contract(self):
        observed = []
        payload = _audit_integrity_payload()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_audit_integrity(
                f"http://127.0.0.1:{server.server_port}", token_file
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(
            observed,
            [{
                "path": "/api/v1/audit-integrity",
                "authorization": f"Bearer {AUTH_TOKEN}",
            }],
        )
        self.assertFalse(thread.is_alive())

    def test_audit_integrity_rejects_oversized_response(self):
        body = b"x" * (MAX_AUDIT_INTEGRITY_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_audit_integrity(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_runtime_info_uses_authenticated_get_and_validates_contract(self):
        observed = []
        payload = _runtime_info_payload()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            report = fetch_runtime_info(
                f"http://127.0.0.1:{server.server_port}", token_file
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(report, payload)
        self.assertEqual(
            observed,
            [{
                "path": "/api/v1/runtime-info",
                "authorization": f"Bearer {AUTH_TOKEN}",
            }],
        )
        self.assertFalse(thread.is_alive())

    def test_runtime_info_rejects_oversized_response(self):
        body = b"x" * (MAX_RUNTIME_INFO_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_runtime_info(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_recurring_dispatch_list_uses_authenticated_global_and_targeted_paths(self):
        observed = []
        payload = _recurring_schedule_dispatch_list_payload()
        targeted_payload = _recurring_schedule_dispatch_list_payload(
            schedule_id="schedule_hourly_report"
        )

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(
                    self,
                    200,
                    targeted_payload
                    if self.path.endswith("/dispatches")
                    and "/recurring-schedules/" in self.path
                    else payload,
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            first = threading.Thread(target=server.handle_request, daemon=True)
            first.start()
            global_listing = fetch_recurring_schedule_dispatches(
                f"http://127.0.0.1:{server.server_port}", token_file
            )
            first.join(timeout=2)
            second = threading.Thread(target=server.handle_request, daemon=True)
            second.start()
            targeted_listing = fetch_recurring_schedule_dispatches(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                schedule_id="schedule_hourly_report",
            )
            second.join(timeout=2)
            server.server_close()

        self.assertEqual(global_listing, payload)
        self.assertEqual(targeted_listing, targeted_payload)
        self.assertEqual(
            observed,
            [
                {
                    "path": "/api/v1/recurring-schedule-dispatches",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                },
                {
                    "path": "/api/v1/recurring-schedules/schedule_hourly_report/dispatches",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                },
            ],
        )
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())

    def test_recurring_dispatch_list_rejects_oversized_response(self):
        body = b"x" * (MAX_RECURRING_SCHEDULE_DISPATCH_LIST_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_recurring_schedule_dispatches(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_recurring_dispatch_page_uses_cursor_and_validates_contract(self):
        observed = []
        payload = _recurring_schedule_dispatch_page_payload(
            schedule_id="schedule_hourly_report", next_cursor="next-page"
        )

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = fetch_recurring_schedule_dispatch_page(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                schedule_id="schedule_hourly_report",
                max_items=1,
                cursor="cursor-token",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(result, payload)
        self.assertEqual(
            observed,
            [{
                "path": "/api/v1/recurring-schedules/schedule_hourly_report/dispatch-pages?max_items=1&cursor=cursor-token",
                "authorization": f"Bearer {AUTH_TOKEN}",
            }],
        )
        self.assertFalse(thread.is_alive())

    def test_recurring_dispatch_page_rejects_oversized_response(self):
        body = b"x" * (MAX_RECURRING_SCHEDULE_DISPATCH_PAGE_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_recurring_schedule_dispatch_page(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_recurring_dispatch_review_posts_cas_payload_and_fetches_projection(self):
        observed = []
        posted = _recurring_schedule_dispatch_review_payload(changed=True)
        fetched = _recurring_schedule_dispatch_review_payload(changed=False)

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed.append(
                    {
                        "method": "POST",
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                        "body": json.loads(
                            self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                        ),
                    }
                )
                _send_json(self, 200, posted)

            def do_GET(self):
                observed.append(
                    {
                        "method": "GET",
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                _send_json(self, 200, fetched)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            post_thread = threading.Thread(target=server.handle_request, daemon=True)
            post_thread.start()
            result = post_recurring_schedule_dispatch_review(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "dispatch_001",
                expected_completed_at="2026-08-11T00:01:00+00:00",
                outcome="effect_not_observed",
            )
            post_thread.join(timeout=2)
            get_thread = threading.Thread(target=server.handle_request, daemon=True)
            get_thread.start()
            fetched_result = fetch_recurring_schedule_dispatch_review(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "dispatch_001",
            )
            get_thread.join(timeout=2)
            server.server_close()

        self.assertEqual(result, posted)
        self.assertEqual(fetched_result, fetched)
        self.assertEqual(
            observed,
            [
                {
                    "method": "POST",
                    "path": "/api/v1/recurring-schedule-dispatches/dispatch_001/review",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                    "body": {
                        "expected_completed_at": "2026-08-11T00:01:00+00:00",
                        "outcome": "effect_not_observed",
                    },
                },
                {
                    "method": "GET",
                    "path": "/api/v1/recurring-schedule-dispatches/dispatch_001/review",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                },
            ],
        )
        self.assertFalse(post_thread.is_alive())
        self.assertFalse(get_thread.is_alive())

    def test_recurring_dispatch_review_rejects_oversized_response(self):
        body = b"x" * (MAX_RECURRING_SCHEDULE_DISPATCH_REVIEW_RESPONSE_BYTES + 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_recurring_schedule_dispatch_review(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    "dispatch_001",
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_state_posts_authenticated_empty_object_and_validates_contract(self):
        observed = []
        payload = {
            "schema_version": "skill2workflow-recurring-schedule-action-0.1.0",
            "schedule_id": "schedule_hourly_report",
            "enabled": False,
            "status": "disabled",
            "changed": True,
        }

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                        "body": self.rfile.read(int(self.headers["Content-Length"])),
                    }
                )
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = post_recurring_schedule_state(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "schedule_hourly_report",
                enabled=False,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(result, payload)
        self.assertEqual(
            observed,
            [{
                "path": "/api/v1/recurring-schedules/schedule_hourly_report/disable",
                "authorization": f"Bearer {AUTH_TOKEN}",
                "body": b"{}",
            }],
        )
        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_state_can_send_expected_next_run_at_cas_token(self):
        observed = []
        payload = {
            "schema_version": "skill2workflow-recurring-schedule-action-0.1.0",
            "schedule_id": "schedule_hourly_report",
            "enabled": False,
            "status": "disabled",
            "changed": True,
        }

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = post_recurring_schedule_state(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "schedule_hourly_report",
                enabled=False,
                expected_next_run_at="2026-08-11T00:00:00Z",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(result, payload)
        self.assertEqual(
            observed,
            [{"expected_next_run_at": "2026-08-11T00:00:00Z"}],
        )
        self.assertFalse(thread.is_alive())

    def test_recurring_schedule_state_rejects_unsafe_identifier_and_contract_drift(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaises(ValueError):
                post_recurring_schedule_state(
                    "http://127.0.0.1:1",
                    token_file,
                    "../scheduler",
                    enabled=True,
                )
            with self.assertRaises(ValueError):
                post_recurring_schedule_state(
                    "http://127.0.0.1:1",
                    token_file,
                    "schedule_hourly_report",
                    enabled=True,
                    expected_next_run_at="\x00",
                )

            class Handler(BaseHTTPRequestHandler):
                def do_POST(self):
                    _send_json(self, 200, {"schema_version": "wrong"})

                def log_message(self, *_args):
                    return

            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                post_recurring_schedule_state(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    "schedule_hourly_report",
                    enabled=True,
                )
            thread.join(timeout=2)
            server.server_close()
        self.assertFalse(thread.is_alive())

    def test_run_detail_uses_authenticated_get_and_validates_redacted_contract(self):
        observed = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                        "content_length": self.headers.get("Content-Length"),
                    }
                )
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-run-detail-0.1.0",
                        "run": {
                            "run_id": RUN_ID,
                            "workflow_id": "workflow",
                            "workflow_version": "0.1.0",
                            "status": "waiting",
                            "current_node": "review",
                            "event_count": 1,
                            "node_result_count": 0,
                            "node_overlays": {},
                            "created_at": "",
                            "updated_at": "",
                        },
                        "events": [
                            {
                                "sequence": 1,
                                "type": "human_gate_waiting",
                                "has_error": False,
                            }
                        ],
                        "window": {
                            "max_events": 50,
                            "total": 1,
                            "returned": 1,
                            "truncated": False,
                        },
                    },
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            detail = fetch_run_detail(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                RUN_ID,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(detail["run"]["run_id"], RUN_ID)
        self.assertEqual(
            observed,
            [
                {
                    "path": f"/runs/{RUN_ID}",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                    "content_length": None,
                }
            ],
        )
        self.assertFalse(thread.is_alive())

    def test_run_detail_rejects_extra_fields_in_provider_response(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-run-detail-0.1.0",
                        "run": {"run_id": RUN_ID},
                        "events": [],
                        "window": {},
                        "private": "must-not-be-accepted",
                    },
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_run_detail(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    RUN_ID,
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_resume_and_cancel_send_bearer_token_and_exact_json_contracts(self):
        observed = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                        "body": json.loads(self.rfile.read(length).decode("utf-8")),
                    }
                )
                if self.path.endswith("/resume"):
                    payload = {"run_id": RUN_ID, "status": "completed", "approved": True}
                else:
                    payload = {"run_id": RUN_ID, "status": "cancelled"}
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"

            resumed = post_run_resume(base_url, token_file, RUN_ID, approved=True)
            cancelled = post_run_cancel(base_url, token_file, RUN_ID)

            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(resumed["approved"], True)
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(
            observed,
            [
                {
                    "path": f"/runs/{RUN_ID}/resume",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                    "body": {"approved": True},
                },
                {
                    "path": f"/runs/{RUN_ID}/cancel",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                    "body": {},
                },
            ],
        )
        self.assertFalse(thread.is_alive())

    def test_invalid_origin_and_run_id_fail_before_network_access(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "service URL"):
                post_run_cancel("http://example.com", token_file, RUN_ID)
            with self.assertRaisesRegex(ValueError, "safe run identifier"):
                post_run_cancel("http://127.0.0.1:1", token_file, "run_bad/segment")

    def test_http_error_is_fixed_and_does_not_echo_provider_body(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = b'{"error":"private provider response"}'
                self.send_response(409)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError) as caught:
                post_run_resume(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    RUN_ID,
                    approved=True,
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(str(caught.exception), "run is not waiting")
        self.assertEqual(caught.exception.status_code, 409)
        self.assertNotIn("private provider response", str(caught.exception))

    def test_redirect_and_oversized_response_are_rejected(self):
        contacted = threading.Event()

        class TargetHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                contacted.set()
                self.send_response(200)
                self.end_headers()

            def log_message(self, *_args):
                return

        target = HTTPServer(("127.0.0.1", 0), TargetHandler)

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{target.server_port}/target")
                self.end_headers()

            def log_message(self, *_args):
                return

        redirect = HTTPServer(("127.0.0.1", 0), RedirectHandler)
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            redirect_thread = threading.Thread(target=redirect.handle_request, daemon=True)
            redirect_thread.start()
            with self.assertRaises(ServiceActionError):
                post_run_cancel(
                    f"http://127.0.0.1:{redirect.server_port}",
                    token_file,
                    RUN_ID,
                )
            redirect_thread.join(timeout=2)

        redirect.server_close()
        target.server_close()
        self.assertFalse(contacted.is_set())

        class OversizedHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = b"x" * (MAX_SERVICE_ACTION_RESPONSE_BYTES + 1)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), OversizedHandler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                post_run_cancel(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    RUN_ID,
                )
            thread.join(timeout=2)
            server.server_close()
        self.assertFalse(thread.is_alive())


def _support_bundle_payload():
    status_counts = {
        "created": 0,
        "running": 0,
        "waiting": 0,
        "completed": 0,
        "failed": 0,
        "cancelled": 0,
        "interrupted": 0,
        "other": 0,
    }
    routes = (
        "health", "readiness", "metrics", "control_snapshot", "support_bundle",
        "run_list", "run_detail", "workflow_trigger", "run_cancel", "run_resume", "unknown",
    )
    zero_http = {"2xx": 0, "4xx": 0, "5xx": 0}
    return {
        "schema_version": "skill2workflow-support-bundle-0.1.0",
        "service": {
            "status": "ready",
            "ready": True,
            "storage": "sqlite",
            "scheduler_lease_owned": True,
        },
        "run_list": {
            "schema_version": "skill2workflow-run-list-0.1.0",
            "summary": {"total": 0, "status_counts": dict(status_counts)},
            "runs": [],
            "window": {"max_items": 100, "total": 0, "returned": 0, "truncated": False},
        },
        "observability": {
            "service_status": "ready",
            "ready": True,
            "scheduler_lease_owned": True,
            "uptime_seconds": 1.25,
            "workflow_status_counts": {"published": 0, "deprecated": 0, "other": 0},
            "run_status_counts": dict(status_counts),
            "dispatch_status_counts": {
                "claimed": 0, "completed": 0, "failed": 0, "skipped": 0,
                "uncertain": 0, "other": 0,
            },
            "audit_event_count": 0,
            "recurring_schedule_count": 0,
            "http_requests": {route: dict(zero_http) for route in routes},
        },
    }


def _audit_consistency_payload():
    return {
        "schema_version": "skill2workflow-run-audit-report-0.1.0",
        "status": "clean",
        "summary": {
            "run_count": 1,
            "checked_runs": 1,
            "attention_runs": 0,
            "missing_events": 0,
            "duplicate_events": 0,
            "unexpected_events": 0,
            "truncated": False,
        },
        "runs": [
            {
                "run_id": RUN_ID,
                "workflow_id": "workflow_service",
                "workflow_version": "0.1.0",
                "run_status": "completed",
                "status": "clean",
                "expected_event_count": 2,
                "observed_event_count": 2,
                "missing": [],
                "duplicate": [],
                "unexpected": [],
            }
        ],
    }


def _recurring_schedule_list_payload():
    return {
        "schema_version": "skill2workflow-recurring-schedule-list-0.1.0",
        "summary": {
            "total": 1,
            "status_counts": {"active": 1, "disabled": 0, "other": 0},
        },
        "schedules": [
            {
                "schedule_id": "schedule_hourly_report",
                "workflow_id": "workflow_service",
                "workflow_version": "0.1.0",
                "status": "active",
                "enabled": True,
                "starts_at": "2026-08-11T00:00:00+00:00",
                "next_run_at": "2026-08-11T01:00:00+00:00",
                "interval_seconds": 3600,
                "missed_run_policy": "latest",
                "last_scheduled_for": "",
                "last_run_id": "",
                "last_trigger_id": "",
            }
        ],
        "window": {
            "max_items": 100,
            "total": 1,
            "returned": 1,
            "truncated": False,
        },
    }


def _recurring_schedule_dispatch_list_payload(schedule_id=""):
    return {
        "schema_version": "skill2workflow-recurring-schedule-dispatch-list-0.1.0",
        "schedule_id": schedule_id,
        "summary": {
            "total": 1,
            "status_counts": {
                "claimed": 0,
                "completed": 0,
                "failed": 0,
                "skipped": 0,
                "uncertain": 1,
                "other": 0,
            },
        },
        "dispatches": [
            {
                "dispatch_id": "dispatch_001",
                "schedule_id": "schedule_hourly_report",
                "scheduled_for": "2026-08-11T00:00:00+00:00",
                "status": "uncertain",
                "coalesced_occurrences": 1,
                "run_id": "run_dispatch_001",
                "trigger_id": "trigger_dispatch_001",
                "error_type": "ProviderTimeout",
                "completed_at": "2026-08-11T00:01:00+00:00",
            }
        ],
        "window": {
            "max_items": 100,
            "total": 1,
            "returned": 1,
            "truncated": False,
        },
    }


def _recurring_schedule_dispatch_page_payload(schedule_id="", next_cursor=""):
    return {
        "schema_version": "skill2workflow-recurring-schedule-dispatch-page-0.1.0",
        "schedule_id": schedule_id,
        "summary": {
            "total": 1,
            "status_counts": {
                "claimed": 0,
                "completed": 0,
                "failed": 0,
                "skipped": 0,
                "uncertain": 1,
                "other": 0,
            },
        },
        "dispatches": [
            {
                "dispatch_id": "dispatch_001",
                "schedule_id": "schedule_hourly_report",
                "scheduled_for": "2026-08-11T00:00:00+00:00",
                "status": "uncertain",
                "coalesced_occurrences": 1,
                "run_id": "run_dispatch_001",
                "trigger_id": "trigger_dispatch_001",
                "error_type": "ProviderTimeout",
                "completed_at": "2026-08-11T00:01:00+00:00",
            }
        ],
        "window": {
            "max_items": 1,
            "total": 1,
            "returned": 1,
            "has_more": bool(next_cursor),
            "next_cursor": next_cursor,
        },
    }


def _recurring_schedule_dispatch_review_payload(changed=False):
    return {
        "schema_version": "skill2workflow-recurring-schedule-dispatch-review-0.1.0",
        "dispatch_id": "dispatch_001",
        "schedule_id": "schedule_hourly_report",
        "scheduled_for": "2026-08-11T00:00:00+00:00",
        "status": "uncertain",
        "expected_completed_at": "2026-08-11T00:01:00+00:00",
        "outcome": "effect_not_observed",
        "reviewed_at": "2026-08-11T00:02:00+00:00",
        "changed": changed,
    }


def _workflow_artifact_report_payload():
    return {
        "schema_version": "skill2workflow-workflow-artifact-report-0.1.0",
        "status": "attention",
        "summary": {
            "registry_records": 2,
            "referenced_artifacts": 2,
            "filesystem_artifacts": 3,
            "healthy": 1,
            "issue_count": 1,
            "missing": 0,
            "unsafe_reference": 0,
            "unsafe_artifact": 0,
            "invalid_json": 0,
            "oversized": 0,
            "checksum_mismatch": 0,
            "orphaned": 1,
            "truncated": False,
        },
        "issues": [{"kind": "orphaned", "artifact": "workflows/orphan.json"}],
    }


def _backup_inventory_payload():
    return {
        "schema_version": "skill2workflow-remote-backup-inventory-0.1.0",
        "status": "ok",
        "total": 1,
        "backups": [
            {
                "status": "valid",
                "created_at": "2026-08-17T00:00:00+00:00",
                "state_layout_version": "skill2workflow-sqlite-layout-0.1.0",
                "workflow_artifact_count": 2,
                "file_count": 6,
                "total_bytes": 4096,
            }
        ],
        "window": {"max_items": 7, "returned": 1, "truncated": False},
    }


def _backup_inventory_page_payload():
    return {
        "schema_version": "skill2workflow-remote-backup-inventory-page-0.1.0",
        "status": "ok",
        "total": 2,
        "backups": [
            {
                "status": "valid",
                "created_at": "2026-08-17T00:00:00+00:00",
                "state_layout_version": "skill2workflow-sqlite-layout-0.1.0",
                "workflow_artifact_count": 2,
                "file_count": 6,
                "total_bytes": 4096,
            }
        ],
        "window": {
            "max_items": 7,
            "total": 2,
            "returned": 1,
            "has_more": True,
            "next_cursor": "cursor-next",
        },
    }


def _backup_retention_plan_payload():
    return {
        "schema_version": "skill2workflow-remote-backup-retention-plan-0.1.0",
        "status": "ready",
        "storage": "filesystem",
        "policy_sha256": "a" * 64,
        "expire_before": "2026-08-14T00:00:03+00:00",
        "minimum_keep": 1,
        "inventory": {"max_items": 1000, "returned": 2, "truncated": False},
        "summary": {
            "valid_backups": 2,
            "invalid_backups": 0,
            "eligible_backups": 1,
            "eligible_bytes": 4096,
            "preserved_backups": 1,
            "preserved_bytes": 4096,
        },
        "blocking_reasons": [],
    }


def _backup_readiness_payload():
    return {
        "schema_version": "skill2workflow-backup-readiness-0.1.0",
        "status": "blocked",
        "storage": "sqlite",
        "state_layout_version": "skill2workflow-sqlite-layout-0.1.0",
        "database_count": 3,
        "workflow_artifact_count": 2,
        "active_scheduler_lease": True,
        "scheduler_database_synthesized": False,
        "backup_allowed": False,
        "blocking_reasons": ["active_scheduler_lease"],
    }


def _audit_integrity_payload():
    return {
        "schema_version": "skill2workflow-audit-integrity-0.1.0",
        "status": "valid",
        "algorithm": "sha256-chain-v1",
        "event_count": 3,
        "head_digest": "a" * 64,
        "first_invalid_sequence": 0,
        "reason": "",
    }


def _audit_event_page_fixture():
    return {
        "schema_version": "skill2workflow-audit-event-list-0.1.0",
        "filters": {
            "workflow_id": "workflow",
            "workflow_version": "0.1.0",
            "run_id": RUN_ID,
            "event_type": "connector_failed",
        },
        "events": [
            {
                "sequence": 1,
                "type": "connector_failed",
                "run_id": RUN_ID,
                "workflow_id": "workflow",
                "workflow_version": "0.1.0",
                "timestamp": "2026-08-17T00:00:00Z",
                "node_id": "call_api",
                "connector_id": "http",
                "connector_kind": "http",
                "connector_status": "failed",
                "attempt": 1,
                "max_attempts": 2,
                "next_attempt": 0,
                "backoff_ms": 0,
                "approved": False,
                "has_error": True,
            }
        ],
        "window": {
            "max_items": 10,
            "total": 1,
            "returned": 1,
            "truncated": False,
            "next_cursor": "",
        },
    }


def _runtime_info_payload():
    return {
        "schema_version": "skill2workflow-runtime-info-0.1.0",
        "package_version": "0.1.0",
        "compatibility_line": "0.1.x",
        "service_schema_version": "skill2workflow-service-0.2.0",
        "workflow_dsl_schema_version": "0.1.0",
        "storage": "sqlite",
        "state_layout_version": "skill2workflow-sqlite-layout-0.1.0",
        "service_status": "ready",
        "service_ready": True,
        "scheduler_lease_owned": True,
    }


def _workflow_document():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_remote_release",
            "name": "Remote release",
            "version": "1.2.3",
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


def _recurring_definition():
    return {
        "schema_version": "skill2workflow-schedule-0.2.0",
        "schedule": {
            "id": "schedule_hourly_report",
            "workflow_id": "workflow_recurring",
            "version": "1.0.0",
            "starts_at": "2026-08-11T00:00:00Z",
            "interval_seconds": 60,
            "missed_run_policy": "latest",
            "enabled": True,
        },
        "trigger": {"input": {"private": "private-input"}},
    }


def _send_json(handler, status_code, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
