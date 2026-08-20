import json
import os
import threading
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request
from pathlib import Path
from unittest import TestCase

from skill2workflow.cli import main
from skill2workflow.ui import (
    _parse_live_audit_page_cursor,
    _parse_live_run_page_cursor,
    find_ui_root,
    serve_ui,
)


ROOT = Path(__file__).resolve().parents[1]


class UiTests(TestCase):
    def test_live_run_page_cursor_parser_accepts_only_one_opaque_cursor(self):
        self.assertEqual(_parse_live_run_page_cursor(""), "")
        self.assertEqual(_parse_live_run_page_cursor("cursor=abc-123"), "abc-123")
        for query in ("status=waiting", "cursor=", "cursor=abc&cursor=def", "cursor=abc%2Fdef"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                _parse_live_run_page_cursor(query)

    def test_live_audit_page_cursor_parser_accepts_only_one_opaque_cursor(self):
        self.assertEqual(_parse_live_audit_page_cursor(""), "")
        self.assertEqual(_parse_live_audit_page_cursor("cursor=abc-123"), "abc-123")
        for query in (
            "status=waiting",
            "cursor=",
            "cursor=abc&cursor=def",
            "cursor=abc%2Fdef",
        ):
            with self.subTest(query=query), self.assertRaises(ValueError):
                _parse_live_audit_page_cursor(query)

    def test_find_ui_root_discovers_source_assets(self):
        root = find_ui_root()

        self.assertEqual(root, ROOT)
        self.assertTrue((root / "web" / "index.html").is_file())
        self.assertTrue((root / "examples" / "control-plane-snapshot.json").is_file())

    def test_ui_server_is_loopback_only_and_serves_static_assets_once(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            serve_ui(host="0.0.0.0", port=0, once=True)

        observed = {}

        def ready(server):
            observed["port"] = server.server_port

        thread = threading.Thread(
            target=serve_ui,
            kwargs={"host": "127.0.0.1", "port": 0, "once": True, "ready_callback": ready},
            daemon=True,
        )
        thread.start()
        for _ in range(100):
            if "port" in observed:
                break
            thread.join(0.01)
        self.assertIn("port", observed)
        with urllib.request.urlopen(
            f"http://127.0.0.1:{observed['port']}/web/index.html", timeout=2
        ) as response:
            body = response.read()
            self.assertEqual(response.status, 200)
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertIn(b"Workflow DSL Visual Editor", body)

    def test_cli_ui_command_forwards_loopback_server_options(self):
        captured = {}

        def fake_serve_ui(**kwargs):
            captured.update(kwargs)

        from unittest.mock import patch

        with patch("skill2workflow.cli.serve_ui", side_effect=fake_serve_ui):
            exit_code = main(["ui", "--host", "localhost", "--port", "4317", "--once"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            captured,
            {
                "host": "localhost",
                "port": 4317,
                "once": True,
                "service_url": None,
                "auth_token_file": None,
            },
        )

    def test_live_proxy_keeps_token_server_side_and_returns_bounded_snapshot(self):
        snapshot = json.loads(
            (ROOT / "examples" / "control-plane-snapshot.json").read_text(
                encoding="utf-8"
            )
        )
        snapshot["window"] = {
            "max_items": 100,
            **{
                field: {
                    "total": len(snapshot[field]),
                    "returned": len(snapshot[field]),
                    "truncated": False,
                }
                for field in (
                    "workflows",
                    "runs",
                    "audit_events",
                    "connectors",
                    "version_comparisons",
                )
            },
        }
        observed = {}

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                if self.path != "/api/v1/control-snapshot":
                    self.send_response(404)
                    self.end_headers()
                    return
                body = json.dumps(snapshot, separators=(",", ":")).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        upstream = HTTPServer(("127.0.0.1", 0), UpstreamHandler)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token_file = Path(directory) / "ingress.token"
                token_file.write_text(
                    "ui-test-token-012345678901234567890123456789\n",
                    encoding="utf-8",
                )
                os.chmod(token_file, 0o600)
                ui_port = {}

                def ready(server):
                    ui_port["value"] = server.server_port

                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1",
                        "port": 0,
                        "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file,
                        "ready_callback": ready,
                    },
                    daemon=True,
                )
                ui_thread.start()
                for _ in range(100):
                    if "value" in ui_port:
                        break
                    ui_thread.join(0.01)
                self.assertIn("value", ui_port)
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/control-snapshot",
                    timeout=2,
                ) as response:
                    body = response.read()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/control-snapshot")
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
                self.assertNotIn(b"ui-test-token-012345678901234567890123456789", body)
                self.assertIn(b"skill2workflow-control-snapshot-0.1.0", body)
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_mode_requires_a_complete_configuration(self):
        with self.assertRaisesRegex(ValueError, "both"):
            serve_ui(
                host="127.0.0.1",
                port=0,
                once=True,
                service_url="https://service.example.test",
            )

    def test_live_proxy_exposes_only_the_fixed_service_probe_contract(self):
        responses = {
            "/healthz": {"service": "skill2workflow", "status": "ok"},
            "/readyz": {
                "service": "skill2workflow",
                "status": "ready",
                "storage": "sqlite",
            },
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                payload = responses.get(self.path)
                if payload is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        upstream = HTTPServer(("127.0.0.1", 0), UpstreamHandler)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token_file = Path(directory) / "ingress.token"
                token_file.write_text(
                    "ui-test-token-012345678901234567890123456789\n",
                    encoding="utf-8",
                )
                os.chmod(token_file, 0o600)
                ui_port = {}

                def ready(server):
                    ui_port["value"] = server.server_port

                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1",
                        "port": 0,
                        "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file,
                        "ready_callback": ready,
                    },
                    daemon=True,
                )
                ui_thread.start()
                for _ in range(100):
                    if "value" in ui_port:
                        break
                    ui_thread.join(0.01)
                self.assertIn("value", ui_port)
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/service-probe",
                    timeout=2,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["schema_version"], "skill2workflow-service-probe-0.1.0")
                    self.assertEqual(payload["status"], "ready")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_a_fixed_downloadable_support_bundle(self):
        from unittest.mock import patch

        bundle = {
            "schema_version": "skill2workflow-support-bundle-0.1.0",
            "status": "ready",
        }
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / "ingress.token"
            token_file.write_text(
                "ui-test-token-012345678901234567890123456789\n",
                encoding="utf-8",
            )
            os.chmod(token_file, 0o600)
            ui_port = {}

            def ready(server):
                ui_port["value"] = server.server_port

            with patch("skill2workflow.ui.fetch_support_bundle", return_value=bundle):
                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1",
                        "port": 0,
                        "once": True,
                        "service_url": "https://service.example.test",
                        "auth_token_file": token_file,
                        "ready_callback": ready,
                    },
                    daemon=True,
                )
                ui_thread.start()
                for _ in range(100):
                    if "value" in ui_port:
                        break
                    ui_thread.join(0.01)
                self.assertIn("value", ui_port)
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/support-bundle",
                    timeout=2,
                ) as response:
                    body = response.read()
                    self.assertEqual(response.status, 200)
                    self.assertIn(
                        'attachment; filename="skill2workflow-support-bundle.json"',
                        response.headers["Content-Disposition"],
                    )
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertIn(b"skill2workflow-support-bundle-0.1.0", body)
                self.assertNotIn(b"ui-test-token", body)

    def test_live_proxy_exposes_fixed_human_gate_resume_without_browser_token(self):
        observed = {}

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = self.rfile.read(int(self.headers["Content-Length"]))
                if self.path != "/runs/run_waiting/resume":
                    self.send_response(404)
                    self.end_headers()
                    return
                payload = {
                    "run_id": "run_waiting",
                    "status": "completed",
                    "approved": True,
                }
                body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        upstream = HTTPServer(("127.0.0.1", 0), UpstreamHandler)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token_file = Path(directory) / "ingress.token"
                token_file.write_text(
                    "ui-test-token-012345678901234567890123456789\n",
                    encoding="utf-8",
                )
                os.chmod(token_file, 0o600)
                ui_port = {}

                def ready(server):
                    ui_port["value"] = server.server_port

                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1",
                        "port": 0,
                        "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file,
                        "ready_callback": ready,
                    },
                    daemon=True,
                )
                ui_thread.start()
                for _ in range(100):
                    if "value" in ui_port:
                        break
                    ui_thread.join(0.01)
                self.assertIn("value", ui_port)
                request = urllib.request.Request(
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/runs/run_waiting/resume",
                    data=b'{"approved":true}',
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["run_id"], "run_waiting")
                    self.assertTrue(payload["approved"])
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/runs/run_waiting/resume")
                self.assertEqual(observed["body"], b'{"approved":true}')
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
                self.assertNotIn(b"ui-test-token", observed["body"])
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_fixed_cooperative_cancel_without_browser_token(self):
        observed = {}

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = self.rfile.read(int(self.headers["Content-Length"]))
                payload = {"run_id": "run_waiting", "status": "cancelled"}
                body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        upstream = HTTPServer(("127.0.0.1", 0), UpstreamHandler)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token_file = Path(directory) / "ingress.token"
                token_file.write_text(
                    "ui-test-token-012345678901234567890123456789\n",
                    encoding="utf-8",
                )
                os.chmod(token_file, 0o600)
                ui_port = {}

                def ready(server):
                    ui_port["value"] = server.server_port

                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1",
                        "port": 0,
                        "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file,
                        "ready_callback": ready,
                    },
                    daemon=True,
                )
                ui_thread.start()
                for _ in range(100):
                    if "value" in ui_port:
                        break
                    ui_thread.join(0.01)
                self.assertIn("value", ui_port)
                request = urllib.request.Request(
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/runs/run_waiting/cancel",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload, {"run_id": "run_waiting", "status": "cancelled"})
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/runs/run_waiting/cancel")
                self.assertEqual(observed["body"], b"{}")
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_bounded_run_detail_without_browser_token(self):
        observed = {}
        detail = {
            "schema_version": "skill2workflow-run-detail-0.1.0",
            "run": {
                "run_id": "run_waiting",
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
                {"sequence": 1, "type": "human_gate_waiting", "has_error": False}
            ],
            "window": {
                "max_events": 50,
                "total": 1,
                "returned": 1,
                "truncated": False,
            },
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                body = json.dumps(detail, separators=(",", ":")).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        upstream = HTTPServer(("127.0.0.1", 0), UpstreamHandler)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token_file = Path(directory) / "ingress.token"
                token_file.write_text(
                    "ui-test-token-012345678901234567890123456789\n",
                    encoding="utf-8",
                )
                os.chmod(token_file, 0o600)
                ui_port = {}

                def ready(server):
                    ui_port["value"] = server.server_port

                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1",
                        "port": 0,
                        "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file,
                        "ready_callback": ready,
                    },
                    daemon=True,
                )
                ui_thread.start()
                for _ in range(100):
                    if "value" in ui_port:
                        break
                    ui_thread.join(0.01)
                self.assertIn("value", ui_port)
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/runs/run_waiting",
                    timeout=2,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["run"]["run_id"], "run_waiting")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/runs/run_waiting")
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_fixed_cursor_paged_run_discovery_without_browser_token(self):
        observed = {}
        status_counts = {
            "created": 0,
            "running": 0,
            "waiting": 1,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "interrupted": 0,
            "other": 0,
        }
        page = {
            "schema_version": "skill2workflow-run-list-0.2.0",
            "summary": {"total": 1, "status_counts": status_counts},
            "filters": {"status": "", "workflow_id": ""},
            "runs": [
                {
                    "run_id": "run_waiting",
                    "workflow_id": "workflow",
                    "workflow_version": "0.1.0",
                    "status": "waiting",
                    "current_node": "review",
                    "event_count": 1,
                    "node_result_count": 0,
                }
            ],
            "window": {
                "max_items": 100,
                "total": 1,
                "returned": 1,
                "has_more": False,
                "next_cursor": None,
            },
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                body = json.dumps(page, separators=(",", ":")).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        upstream = HTTPServer(("127.0.0.1", 0), UpstreamHandler)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token_file = Path(directory) / "ingress.token"
                token_file.write_text(
                    "ui-test-token-012345678901234567890123456789\n",
                    encoding="utf-8",
                )
                os.chmod(token_file, 0o600)
                ui_port = {}

                def ready(server):
                    ui_port["value"] = server.server_port

                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1",
                        "port": 0,
                        "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file,
                        "ready_callback": ready,
                    },
                    daemon=True,
                )
                ui_thread.start()
                for _ in range(100):
                    if "value" in ui_port:
                        break
                    ui_thread.join(0.01)
                self.assertIn("value", ui_port)
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/run-page",
                    timeout=2,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["runs"][0]["run_id"], "run_waiting")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/runs?max_items=100")
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_fixed_cursor_paged_audit_without_browser_token(self):
        observed = {}
        event = {
            "sequence": 1,
            "type": "run_started",
            "run_id": "run_audit",
            "workflow_id": "workflow",
            "workflow_version": "0.1.0",
            "timestamp": "2026-08-20T00:00:00Z",
            "node_id": "start",
            "connector_id": "",
            "connector_kind": "",
            "connector_status": "",
            "attempt": 0,
            "max_attempts": 0,
            "next_attempt": 0,
            "backoff_ms": 0,
            "approved": False,
            "has_error": False,
        }
        page = {
            "schema_version": "skill2workflow-audit-event-list-0.1.0",
            "filters": {
                "workflow_id": "",
                "workflow_version": "",
                "run_id": "",
                "event_type": "",
            },
            "events": [event],
            "window": {
                "max_items": 100,
                "total": 1,
                "returned": 1,
                "truncated": False,
                "next_cursor": "",
            },
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                body = json.dumps(page, separators=(",", ":")).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        upstream = HTTPServer(("127.0.0.1", 0), UpstreamHandler)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token_file = Path(directory) / "ingress.token"
                token_file.write_text(
                    "ui-test-token-012345678901234567890123456789\n",
                    encoding="utf-8",
                )
                os.chmod(token_file, 0o600)
                ui_port = {}

                def ready(server):
                    ui_port["value"] = server.server_port

                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1",
                        "port": 0,
                        "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file,
                        "ready_callback": ready,
                    },
                    daemon=True,
                )
                ui_thread.start()
                for _ in range(100):
                    if "value" in ui_port:
                        break
                    ui_thread.join(0.01)
                self.assertIn("value", ui_port)
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/audit-page?cursor=older123",
                    timeout=2,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["events"][0]["sequence"], 1)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(
                    observed["path"],
                    "/api/v1/audit-events?max_items=100&cursor=older123",
                )
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_fixed_schedule_inventory_without_browser_token(self):
        observed = {}
        page = {
            "schema_version": "skill2workflow-recurring-schedule-list-0.1.0",
            "summary": {
                "total": 1,
                "status_counts": {"active": 1, "disabled": 0, "other": 0},
            },
            "schedules": [
                {
                    "schedule_id": "schedule_demo",
                    "workflow_id": "workflow_demo",
                    "workflow_version": "0.1.0",
                    "status": "active",
                    "enabled": True,
                    "starts_at": "2026-08-20T00:00:00Z",
                    "next_run_at": "2026-08-20T01:00:00Z",
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

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                body = json.dumps(page, separators=(",", ":")).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        upstream = HTTPServer(("127.0.0.1", 0), UpstreamHandler)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token_file = Path(directory) / "ingress.token"
                token_file.write_text(
                    "ui-test-token-012345678901234567890123456789\n",
                    encoding="utf-8",
                )
                os.chmod(token_file, 0o600)
                ui_port = {}

                def ready(server):
                    ui_port["value"] = server.server_port

                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1",
                        "port": 0,
                        "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file,
                        "ready_callback": ready,
                    },
                    daemon=True,
                )
                ui_thread.start()
                for _ in range(100):
                    if "value" in ui_port:
                        break
                    ui_thread.join(0.01)
                self.assertIn("value", ui_port)
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/recurring-schedules",
                    timeout=2,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["schedules"][0]["schedule_id"], "schedule_demo")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/recurring-schedules")
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)
