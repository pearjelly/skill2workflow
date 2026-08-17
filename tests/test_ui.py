import json
import os
import threading
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request
from pathlib import Path
from unittest import TestCase

from skill2workflow.cli import main
from skill2workflow.ui import find_ui_root, serve_ui


ROOT = Path(__file__).resolve().parents[1]


class UiTests(TestCase):
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
