import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.live_snapshot import (
    MAX_LIVE_SNAPSHOT_BYTES,
    fetch_live_control_snapshot,
    write_private_snapshot,
)


AUTH_TOKEN = "live-snapshot-test-token-0123456789abcdef"


class LiveSnapshotClientTests(TestCase):
    def test_private_output_replaces_symlink_without_touching_target(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            victim = root / "victim.json"
            output = root / "snapshot.json"
            victim.write_text("private-victim", encoding="utf-8")
            output.symlink_to(victim)

            write_private_snapshot(output, {"status": "safe"})

            written = json.loads(output.read_text(encoding="utf-8"))
            victim_value = victim.read_text(encoding="utf-8")
            output_mode = output.stat().st_mode & 0o777
            output_is_symlink = output.is_symlink()

        self.assertEqual(written, {"status": "safe"})
        self.assertEqual(victim_value, "private-victim")
        self.assertFalse(output_is_symlink)
        self.assertEqual(output_mode, 0o600)

    def test_private_output_failure_preserves_existing_file_and_cleans_temp(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "snapshot.json"
            output.write_text("previous", encoding="utf-8")

            with patch("skill2workflow.live_snapshot.json.dump", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    write_private_snapshot(output, {"status": "new"})

            current = output.read_text(encoding="utf-8")
            leftovers = list(root.glob(".snapshot.json.*"))

        self.assertEqual(current, "previous")
        self.assertEqual(leftovers, [])

    def test_fetch_uses_protected_token_and_accepts_fixed_snapshot_contract(self):
        payload = {
            "schema_version": "skill2workflow-control-snapshot-0.1.0",
            "summary": {
                "workflow_count": 0,
                "run_count": 0,
                "audit_event_count": 0,
                "connector_count": 0,
                "status_counts": {},
                "run_status_counts": {},
            },
            "workflows": [],
            "runs": [],
            "audit_events": [],
            "connectors": [],
            "version_comparisons": [],
            "operator_insights": {},
            "window": {
                "max_items": 100,
                "workflows": {"total": 0, "returned": 0, "truncated": False},
                "runs": {"total": 0, "returned": 0, "truncated": False},
                "audit_events": {"total": 0, "returned": 0, "truncated": False},
                "connectors": {"total": 0, "returned": 0, "truncated": False},
                "version_comparisons": {
                    "total": 0,
                    "returned": 0,
                    "truncated": False,
                },
            },
        }
        observed = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                data = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "ingress.token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()

            snapshot = fetch_live_control_snapshot(
                f"http://127.0.0.1:{server.server_port}", token_file
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(snapshot, payload)
        self.assertEqual(observed["path"], "/api/v1/control-snapshot")
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertFalse(thread.is_alive())

    def test_fetch_rejects_insecure_remote_or_ambiguous_base_urls(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "ingress.token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            invalid_urls = (
                "http://example.com",
                "ftp://127.0.0.1:8080",
                "http://127.0.0.1:8080/path",
                "http://127.0.0.1:8080?query=private",
                "https://user:password@example.com",
            )
            for url in invalid_urls:
                with self.subTest(url=url):
                    with self.assertRaisesRegex(ValueError, "service URL"):
                        fetch_live_control_snapshot(url, token_file)

    def test_fetch_rejects_oversized_or_wrong_schema_response_without_echo(self):
        responses = (
            (b"x" * (MAX_LIVE_SNAPSHOT_BYTES + 1), "application/json"),
            (json.dumps({"schema_version": "private-wrong-schema"}).encode(), "application/json"),
        )

        for body, content_type in responses:
            with self.subTest(size=len(body)):
                class Handler(BaseHTTPRequestHandler):
                    def do_GET(self):
                        self.send_response(200)
                        self.send_header("Content-Type", content_type)
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        try:
                            self.wfile.write(body)
                        except (BrokenPipeError, ConnectionResetError):
                            pass

                    def log_message(self, *_args):
                        return

                with TemporaryDirectory() as tmp:
                    token_file = Path(tmp) / "ingress.token"
                    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
                    token_file.chmod(0o600)
                    server = HTTPServer(("127.0.0.1", 0), Handler)
                    thread = threading.Thread(target=server.handle_request, daemon=True)
                    thread.start()
                    with self.assertRaisesRegex(ValueError, "live control snapshot unavailable") as caught:
                        fetch_live_control_snapshot(
                            f"http://127.0.0.1:{server.server_port}", token_file
                        )
                    thread.join(timeout=2)
                    server.server_close()

                self.assertNotIn("private", str(caught.exception))

    def test_fetch_rejects_semantically_inconsistent_window(self):
        payload = {
            "schema_version": "skill2workflow-control-snapshot-0.1.0",
            "summary": {
                "workflow_count": 1,
                "run_count": 0,
                "audit_event_count": 0,
                "connector_count": 0,
                "status_counts": {"published": 1},
                "run_status_counts": {},
            },
            "workflows": [],
            "runs": [],
            "audit_events": [],
            "connectors": [],
            "version_comparisons": [],
            "operator_insights": {},
            "window": {
                "max_items": 100,
                "workflows": {"total": 1, "returned": 1, "truncated": False},
                "runs": {"total": 0, "returned": 0, "truncated": False},
                "audit_events": {"total": 0, "returned": 0, "truncated": False},
                "connectors": {"total": 0, "returned": 0, "truncated": False},
                "version_comparisons": {
                    "total": 0,
                    "returned": 0,
                    "truncated": False,
                },
            },
        }

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "ingress.token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()

            with self.assertRaisesRegex(ValueError, "live control snapshot unavailable"):
                fetch_live_control_snapshot(
                    f"http://127.0.0.1:{server.server_port}", token_file
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_fetch_refuses_redirect_without_contacting_the_target(self):
        contacted = threading.Event()

        class TargetHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                contacted.set()
                self.send_response(200)
                self.end_headers()

            def log_message(self, *_args):
                return

        target = HTTPServer(("127.0.0.1", 0), TargetHandler)

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header(
                    "Location",
                    f"http://127.0.0.1:{target.server_port}/capture",
                )
                self.end_headers()

            def log_message(self, *_args):
                return

        redirect = HTTPServer(("127.0.0.1", 0), RedirectHandler)
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "ingress.token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            redirect_thread = threading.Thread(
                target=redirect.handle_request, daemon=True
            )
            redirect_thread.start()

            with self.assertRaisesRegex(ValueError, "live control snapshot unavailable"):
                fetch_live_control_snapshot(
                    f"http://127.0.0.1:{redirect.server_port}", token_file
                )
            redirect_thread.join(timeout=2)

        redirect.server_close()
        target.server_close()
        self.assertFalse(contacted.is_set())
        self.assertFalse(redirect_thread.is_alive())
