import hashlib
import json
import os
import threading
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.error
import urllib.request
from pathlib import Path
from unittest import TestCase

from skill2workflow.cli import main
from skill2workflow.ui import (
    _parse_live_audit_page_cursor,
    _parse_live_workflow_explanation_path,
    _parse_live_workflow_diff_path,
    _parse_live_workflow_preflight_path,
    _parse_live_schedule_dispatch_page_path,
    _parse_live_schedule_dispatch_review_path,
    _parse_live_run_page_cursor,
    find_ui_root,
    serve_ui,
)


ROOT = Path(__file__).resolve().parents[1]


class UiTests(TestCase):
    def test_editor_bundles_pinned_litegraph_assets_without_a_cdn(self):
        vendor = ROOT / "web" / "vendor" / "litegraph-0.7.18"
        expected_digests = {
            "litegraph.min.js": "6a6bd1480057107b8dc12b40730b88afb01729ebcbf0555cd67f5a229f381589",
            "litegraph.css": "565cee8d54e7dfd16295f0ec7b19f910a739c0f42d5263198e3416a38a6006b3",
            "LICENSE": "8bc224b3d4a8e3a7729f57bc7f4eb35f3946d6b476edbf9e725c551dd7f6d72b",
        }
        for filename, expected_digest in expected_digests.items():
            with self.subTest(filename=filename):
                self.assertEqual(
                    hashlib.sha256((vendor / filename).read_bytes()).hexdigest(),
                    expected_digest,
                )

        page = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('./vendor/litegraph-0.7.18/litegraph.css', page)
        self.assertIn('./vendor/litegraph-0.7.18/litegraph.min.js', page)
        self.assertNotIn("cdn.jsdelivr.net", page)
        record = (vendor / "README.md").read_text(encoding="utf-8")
        self.assertIn("litegraph.js` 0.7.18", record)
        self.assertIn(expected_digests["litegraph.min.js"], record)

    def test_editor_stages_skill_files_with_strict_utf8_byte_decoding(self):
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        start = app.index("async function stageSelectedSkill")
        end = app.index("async function compileStagedSkill", start)
        stage_source = app[start:end]

        self.assertIn('new TextDecoder("utf-8", { fatal: true })', stage_source)
        self.assertIn("await file.arrayBuffer()", stage_source)
        self.assertNotIn("file.text()", stage_source)
        self.assertIn("cannot verify UTF-8 SKILL.md input", stage_source)

    def test_live_workflow_explanation_path_parser_accepts_only_two_safe_components(self):
        self.assertEqual(
            _parse_live_workflow_explanation_path(
                "/api/v1/workflow-explanations/workflow_demo/0.1.0"
            ),
            ("workflow_demo", "0.1.0"),
        )
        for path in (
            "/api/v1/workflow-explanations/workflow_demo",
            "/api/v1/workflow-explanations/workflow_demo/0.1.0/extra",
            "/api/v1/workflow-explanations/workflow%2Fdemo/0.1.0",
            "/api/v1/workflow-explanations/workflow_demo/0.1.0%3Fdebug",
        ):
            with self.subTest(path=path):
                self.assertIsNone(_parse_live_workflow_explanation_path(path))

    def test_live_workflow_preflight_path_parser_accepts_only_two_safe_components(self):
        self.assertEqual(
            _parse_live_workflow_preflight_path(
                "/api/v1/workflow-preflights/workflow_demo/0.1.0"
            ),
            ("workflow_demo", "0.1.0"),
        )
        for path in (
            "/api/v1/workflow-preflights/workflow_demo",
            "/api/v1/workflow-preflights/workflow_demo/0.1.0/extra",
            "/api/v1/workflow-preflights/workflow%2Fdemo/0.1.0",
        ):
            with self.subTest(path=path):
                self.assertIsNone(_parse_live_workflow_preflight_path(path))

    def test_live_workflow_diff_path_parser_accepts_only_three_safe_components(self):
        self.assertEqual(
            _parse_live_workflow_diff_path(
                "/api/v1/workflow-diffs/workflow_demo/0.1.0/0.2.0"
            ),
            ("workflow_demo", "0.1.0", "0.2.0"),
        )
        for path in (
            "/api/v1/workflow-diffs/workflow_demo/0.1.0",
            "/api/v1/workflow-diffs/workflow_demo/0.1.0/0.2.0/extra",
            "/api/v1/workflow-diffs/workflow%2Fdemo/0.1.0/0.2.0",
        ):
            with self.subTest(path=path):
                self.assertIsNone(_parse_live_workflow_diff_path(path))

    def test_live_schedule_dispatch_page_path_parser_accepts_optional_cursor(self):
        self.assertEqual(
            _parse_live_schedule_dispatch_page_path(
                "/api/v1/recurring-schedule-dispatch-pages/schedule_demo"
            ),
            ("schedule_demo", ""),
        )
        self.assertEqual(
            _parse_live_schedule_dispatch_page_path(
                "/api/v1/recurring-schedule-dispatch-pages/schedule_demo/cursor-1"
            ),
            ("schedule_demo", "cursor-1"),
        )
        for path in (
            "/api/v1/recurring-schedule-dispatch-pages",
            "/api/v1/recurring-schedule-dispatch-pages/schedule_demo/extra/parts",
            "/api/v1/recurring-schedule-dispatch-pages/schedule%2Fdemo",
            "/api/v1/recurring-schedule-dispatch-pages/schedule_demo/cursor%2F1",
        ):
            with self.subTest(path=path):
                self.assertIsNone(_parse_live_schedule_dispatch_page_path(path))

    def test_live_schedule_dispatch_review_path_parser_accepts_only_one_safe_id(self):
        self.assertEqual(
            _parse_live_schedule_dispatch_review_path(
                "/api/v1/recurring-schedule-dispatch-reviews/dispatch_demo"
            ),
            "dispatch_demo",
        )
        for path in (
            "/api/v1/recurring-schedule-dispatch-reviews",
            "/api/v1/recurring-schedule-dispatch-reviews/dispatch_demo/extra",
            "/api/v1/recurring-schedule-dispatch-reviews/dispatch%2Fdemo",
        ):
            with self.subTest(path=path):
                self.assertIsNone(_parse_live_schedule_dispatch_review_path(path))

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
        self.assertIn(b"Choose SKILL.md", body)
        self.assertIn(b"Compile SKILL", body)
        self.assertIn(b"SKILL Compile Review", body)
        self.assertIn(b"Validate DSL", body)
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("/api/v1/skill-compiles", app)
        self.assertIn("/api/v1/workflow-validations", app)
        self.assertIn("compileStagedSkill", app)
        self.assertIn("parseSkillCompileResponse", app)
        self.assertIn("validateCurrentWorkflow", app)
        self.assertIn("parseWorkflowValidationResponse", app)
        self.assertIn("skill2workflow-skill-compile-review-0.1.0", app)
        self.assertIn("skill2workflow-local-workflow-validation-0.1.0", app)

    def test_ui_server_compiles_one_bounded_skill_without_service_credentials(self):
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
        request = urllib.request.Request(
            f"http://127.0.0.1:{observed['port']}/api/v1/skill-compiles",
            data=json.dumps(
                {
                    "skill_markdown": "---\nname: local-preview\n---\n\n## Checklist\n\n1. Review draft\n",
                },
                separators=(",", ":"),
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            compiled = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        workflow = compiled["workflow"]
        self.assertEqual(workflow["workflow"]["id"], "workflow_local_preview")
        self.assertEqual(workflow["nodes"][1]["metadata"]["source"]["file"], "SKILL.md")
        self.assertEqual(
            compiled["review"],
            {
                "schema_version": "skill2workflow-skill-compile-review-0.1.0",
                "ordered_step_count": 1,
                "executable_node_count": 1,
                "human_gate_count": 0,
                "verification_node_count": 0,
                "hard_gate_count": 0,
                "notices": ["human_gate_not_inferred", "verification_not_inferred"],
            },
        )
        self.assertNotIn("Review draft", json.dumps(compiled["review"]))

    def test_ui_server_validates_one_workflow_with_a_source_free_result(self):
        observed = {}

        def ready(server):
            observed["port"] = server.server_port

        workflow = json.loads(
            (ROOT / "examples" / "workflows" / "approval-flow.workflow.json").read_text(
                encoding="utf-8"
            )
        )
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
        request = urllib.request.Request(
            f"http://127.0.0.1:{observed['port']}/api/v1/workflow-validations",
            data=json.dumps({"workflow": workflow}, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            result = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(
            result,
            {
                "schema_version": "skill2workflow-local-workflow-validation-0.1.0",
                "valid": True,
                "error_count": 0,
                "errors": [],
                "truncated": False,
            },
        )

    def test_ui_server_validation_does_not_echo_workflow_values(self):
        observed = {}

        def ready(server):
            observed["port"] = server.server_port

        secret_marker = "private authoring text must not be echoed"
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {
                "id": "workflow_private",
                "name": secret_marker,
                "version": "0.1.0",
                "status": "draft",
            },
            "entry": "start",
            "nodes": [
                {"id": "start", "type": "start", "title": secret_marker, "on_success": "missing"},
                {"id": "end", "type": "end"},
            ],
            "edges": [],
        }
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
        request = urllib.request.Request(
            f"http://127.0.0.1:{observed['port']}/api/v1/workflow-validations",
            data=json.dumps({"workflow": workflow}, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            raw = response.read()
            result = json.loads(raw.decode("utf-8"))
            self.assertEqual(response.status, 200)
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertFalse(result["valid"])
        self.assertGreater(result["error_count"], 0)
        self.assertTrue(result["errors"])
        self.assertFalse(result["truncated"])
        self.assertNotIn(secret_marker.encode("utf-8"), raw)
        self.assertTrue(
            all(set(error) in ({"code"}, {"code", "node_index"}) for error in result["errors"])
        )
        self.assertIn(
            {"code": "node_transition_target_missing", "node_index": 0},
            result["errors"],
        )

    def test_ui_server_rejects_malformed_skill_compile_before_parsing(self):
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
        request = urllib.request.Request(
            f"http://127.0.0.1:{observed['port']}/api/v1/skill-compiles",
            data=b'{"skill_markdown":"draft","source_path":"outside"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request, timeout=2)
        error = raised.exception
        try:
            self.assertEqual(error.code, 400)
            self.assertEqual(
                json.loads(error.read().decode("utf-8")),
                {"error": "skill compile body is malformed"},
            )
        finally:
            error.close()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

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

    def test_live_proxy_exposes_schedule_dispatch_page_without_browser_token(self):
        observed = {}
        page = {
            "schema_version": "skill2workflow-recurring-schedule-dispatch-page-0.1.0",
            "schedule_id": "schedule_demo",
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
                    "dispatch_id": "dispatch_demo",
                    "schedule_id": "schedule_demo",
                    "scheduled_for": "2026-08-20T01:00:00Z",
                    "status": "uncertain",
                    "coalesced_occurrences": 1,
                    "run_id": "run_demo",
                    "trigger_id": "trigger_demo",
                    "error_type": "unknown_outcome",
                    "completed_at": "2026-08-20T01:00:05Z",
                }
            ],
            "window": {
                "max_items": 100,
                "total": 1,
                "returned": 1,
                "has_more": False,
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
                    "http://127.0.0.1:{}/api/v1/recurring-schedule-dispatch-pages/schedule_demo/cursor-1".format(
                        ui_port["value"]
                    ),
                    timeout=2,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["dispatches"][0]["status"], "uncertain")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(
                    observed["path"],
                    "/api/v1/recurring-schedules/schedule_demo/dispatch-pages?max_items=100&cursor=cursor-1",
                )
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_records_schedule_dispatch_review_without_browser_token(self):
        observed = {}
        review = {
            "schema_version": "skill2workflow-recurring-schedule-dispatch-review-0.1.0",
            "dispatch_id": "dispatch_demo",
            "schedule_id": "schedule_demo",
            "scheduled_for": "2026-08-20T01:00:00Z",
            "status": "uncertain",
            "expected_completed_at": "2026-08-20T01:00:05Z",
            "outcome": "effect_confirmed",
            "reviewed_at": "2026-08-20T02:00:00Z",
            "changed": True,
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                content_length = int(self.headers.get("Content-Length", "0"))
                observed["body"] = json.loads(self.rfile.read(content_length).decode("utf-8"))
                body = json.dumps(review, separators=(",", ":")).encode("utf-8")
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
                    "http://127.0.0.1:{}/api/v1/recurring-schedule-dispatch-reviews/dispatch_demo".format(
                        ui_port["value"]
                    ),
                    data=json.dumps(
                        {
                            "expected_completed_at": "2026-08-20T01:00:05Z",
                            "outcome": "effect_confirmed",
                        },
                        separators=(",", ":"),
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertTrue(payload["changed"])
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(
                    observed["path"],
                    "/api/v1/recurring-schedule-dispatches/dispatch_demo/review",
                )
                self.assertEqual(
                    observed["body"],
                    {
                        "expected_completed_at": "2026-08-20T01:00:05Z",
                        "outcome": "effect_confirmed",
                    },
                )
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_operational_readiness_without_browser_token(self):
        observed = {}
        report = {
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

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                body = json.dumps(report, separators=(",", ":")).encode("utf-8")
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
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/operational-readiness",
                    timeout=2,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["status"], "ready")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/operational-readiness")
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_workflow_inventory_without_browser_token(self):
        observed = {}
        inventory = {
            "schema_version": "skill2workflow-workflow-inventory-0.1.0",
            "summary": {
                "total": 1,
                "status_counts": {"published": 1, "deprecated": 0, "other": 0},
            },
            "versions": [
                {
                    "workflow_id": "workflow_demo",
                    "version": "0.1.0",
                    "status": "published",
                    "aliases": ["production"],
                    "checksum": "a" * 64,
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
                body = json.dumps(inventory, separators=(",", ":")).encode("utf-8")
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
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/workflows",
                    timeout=2,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["versions"][0]["aliases"], ["production"])
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/workflows")
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_promotes_workflow_without_browser_token(self):
        observed = {}
        promotion = {
            "schema_version": "skill2workflow-workflow-promotion-0.1.0",
            "workflow_id": "workflow_demo",
            "version": "0.2.0",
            "alias": "production",
            "status": "promoted",
            "checksum": "b" * 64,
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = json.dumps(promotion, separators=(",", ":")).encode("utf-8")
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
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-promotions",
                    data=json.dumps(
                        {
                            "workflow_id": "workflow_demo",
                            "version": "0.2.0",
                            "alias": "production",
                            "expected_current_version": "0.1.0",
                        },
                        separators=(",", ":"),
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["status"], "promoted")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/workflow-promotions")
                self.assertEqual(
                    observed["body"],
                    {
                        "workflow_id": "workflow_demo",
                        "version": "0.2.0",
                        "alias": "production",
                        "expected_current_version": "0.1.0",
                    },
                )
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_publishes_workflow_without_browser_token(self):
        observed = {}
        release = {
            "schema_version": "skill2workflow-workflow-release-0.1.0",
            "workflow_id": "workflow_demo",
            "version": "0.3.0",
            "status": "published",
            "checksum": "c" * 64,
        }
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {"id": "workflow_demo", "version": "0.3.0"},
            "entry": "start",
            "nodes": [],
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = json.dumps(release, separators=(",", ":")).encode("utf-8")
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
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-releases",
                    data=json.dumps({"workflow": workflow}, separators=(",", ":")).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload, release)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/workflow-releases")
                self.assertEqual(observed["body"], {"workflow": workflow})
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_preflights_staged_workflow_without_browser_token(self):
        observed = {}
        report = {
            "schema_version": "skill2workflow-workflow-release-preflight-0.1.0",
            "workflow": {"id": "workflow_demo", "version": "0.3.0"},
            "document_valid": True,
            "empty_trigger_ready": False,
            "summary": {
                "node_count": 2,
                "connector_node_count": 0,
                "side_effecting_node_count": 0,
                "mapping_count": 0,
                "blocked_node_count": 0,
                "issue_count": 1,
            },
            "issues": [
                {"code": "input_invalid", "severity": "error", "node_id": None, "path": ["input"]}
            ],
            "safety": {
                "side_effect_free": True,
                "connector_calls": False,
                "credentials_resolved": False,
                "raw_values_included": False,
            },
        }
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {"id": "workflow_demo", "version": "0.3.0"},
            "entry": "start",
            "nodes": [],
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = json.dumps(report, separators=(",", ":")).encode("utf-8")
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
                token_file.write_text("ui-test-token-012345678901234567890123456789\n", encoding="utf-8")
                os.chmod(token_file, 0o600)
                ui_port = {}

                def ready(server):
                    ui_port["value"] = server.server_port

                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1", "port": 0, "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file, "ready_callback": ready,
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
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-release-preflights",
                    data=json.dumps({"workflow": workflow}, separators=(",", ":")).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.loads(response.read().decode("utf-8")), report)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/workflow-release-preflights")
                self.assertEqual(observed["body"], {"workflow": workflow})
                self.assertEqual(observed["authorization"], "Bearer ui-test-token-012345678901234567890123456789")
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_reviews_staged_workflow_target_without_browser_token(self):
        observed = {}
        review = {
            "schema_version": "skill2workflow-workflow-release-target-review-0.1.0",
            "workflow": {"id": "workflow_demo", "version": "0.3.0"},
            "candidate_checksum": "a" * 64,
            "target": {"state": "conflict", "published_checksum": "b" * 64},
            "publication_ready": False,
            "empty_trigger_ready": False,
            "summary": {
                "node_count": 2,
                "connector_node_count": 0,
                "side_effecting_node_count": 0,
                "mapping_count": 0,
                "blocked_node_count": 0,
                "issue_count": 1,
            },
            "issues": [
                {"code": "input_invalid", "severity": "error", "node_id": None, "path": ["input"]}
            ],
            "safety": {
                "side_effect_free": True,
                "connector_calls": False,
                "credentials_resolved": False,
                "raw_values_included": False,
            },
        }
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {"id": "workflow_demo", "version": "0.3.0"},
            "entry": "start",
            "nodes": [],
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = json.dumps(review, separators=(",", ":")).encode("utf-8")
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
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-release-target-reviews",
                    data=json.dumps({"workflow": workflow}, separators=(",", ":")).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.loads(response.read().decode("utf-8")), review)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/workflow-release-target-reviews")
                self.assertEqual(observed["body"], {"workflow": workflow})
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_starts_checked_empty_trigger_without_browser_token(self):
        observed = {}
        receipt = {
            "trigger_id": "trigger_ui_001",
            "workflow_id": "workflow_demo",
            "workflow_version": "0.3.0",
            "run_id": "run_ui_001",
            "run_status": "waiting",
            "source": "live-ui",
            "idempotency_key": "live-ui-0123456789abcdef0123456789abcdef0123",
            "input_keys": [],
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = json.dumps(receipt, separators=(",", ":")).encode("utf-8")
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
                token_file.write_text("ui-test-token-012345678901234567890123456789\n", encoding="utf-8")
                os.chmod(token_file, 0o600)
                ui_port = {}

                def ready(server):
                    ui_port["value"] = server.server_port

                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1", "port": 0, "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file, "ready_callback": ready,
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
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-empty-triggers",
                    data=json.dumps(
                        {
                            "workflow_id": "workflow_demo", "version": "0.3.0",
                            "idempotency_key": receipt["idempotency_key"],
                        },
                        separators=(",", ":"),
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.loads(response.read().decode("utf-8")), receipt)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/webhooks/workflow_demo/0.3.0")
                self.assertEqual(
                    observed["body"],
                    {"source": "live-ui", "idempotency_key": receipt["idempotency_key"], "input": {}},
                )
                self.assertEqual(observed["authorization"], "Bearer ui-test-token-012345678901234567890123456789")
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_preflights_staged_input_without_browser_token(self):
        observed = {}
        report = {
            "schema_version": "skill2workflow-workflow-preflight-0.1.0",
            "workflow": {"id": "workflow_demo", "version": "0.3.0", "status": "published"},
            "ready": True,
            "input": {
                "provided": True, "status": "valid", "provided_property_count": 1,
                "declared_property_count": 1, "required_property_count": 1,
                "missing_required_count": 0, "unknown_property_count": 0,
                "error_code": None, "error_path": None,
            },
            "summary": {
                "node_count": 2, "connector_node_count": 0, "side_effecting_node_count": 0,
                "mapping_count": 0, "blocked_node_count": 0, "issue_count": 0,
            },
            "nodes": [
                {"id": "start", "type": "start", "connector": None, "input_mapping": {"status": "not_applicable", "mapping_count": 0, "mapped_count": 0, "missing_required_count": 0, "missing_optional_count": 0}},
                {"id": "end", "type": "end", "connector": None, "input_mapping": {"status": "not_applicable", "mapping_count": 0, "mapped_count": 0, "missing_required_count": 0, "missing_optional_count": 0}},
            ],
            "issues": [],
            "safety": {"side_effect_free": True, "connector_calls": False, "credentials_resolved": False, "raw_values_included": False},
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = json.dumps(report, separators=(",", ":")).encode("utf-8")
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
                token_file.write_text("ui-test-token-012345678901234567890123456789\n", encoding="utf-8")
                os.chmod(token_file, 0o600)
                ui_port = {}
                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={"host": "127.0.0.1", "port": 0, "once": True, "service_url": f"http://127.0.0.1:{upstream.server_port}", "auth_token_file": token_file, "ready_callback": lambda server: ui_port.update({"value": server.server_port})},
                    daemon=True,
                )
                ui_thread.start()
                for _ in range(100):
                    if "value" in ui_port:
                        break
                    ui_thread.join(0.01)
                request = urllib.request.Request(
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-input-preflights",
                    data=b'{"workflow_id":"workflow_demo","version":"0.3.0","input":{"customer_id":"private"}}',
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.loads(response.read().decode("utf-8")), report)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/workflow-preflights/workflow_demo/0.3.0")
                self.assertEqual(observed["body"], {"input": {"customer_id": "private"}})
                self.assertEqual(observed["authorization"], "Bearer ui-test-token-012345678901234567890123456789")
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_starts_staged_input_without_browser_token(self):
        observed = {}
        idempotency_key = "live-ui-0123456789abcdef0123456789abcdef0123"
        receipt = {
            "trigger_id": "trigger_staged_input",
            "workflow_id": "workflow_demo",
            "workflow_version": "0.3.0",
            "run_id": "run_staged_input",
            "run_status": "created",
            "source": "live-ui",
            "idempotency_key": idempotency_key,
            "input_keys": ["customer_id"],
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = json.dumps(receipt, separators=(",", ":")).encode("utf-8")
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
                token_file.write_text("ui-test-token-012345678901234567890123456789\n", encoding="utf-8")
                os.chmod(token_file, 0o600)
                ui_port = {}
                ui_thread = threading.Thread(
                    target=serve_ui,
                    kwargs={
                        "host": "127.0.0.1", "port": 0, "once": True,
                        "service_url": f"http://127.0.0.1:{upstream.server_port}",
                        "auth_token_file": token_file,
                        "ready_callback": lambda server: ui_port.update({"value": server.server_port}),
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
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-input-triggers",
                    data=json.dumps(
                        {
                            "workflow_id": "workflow_demo",
                            "version": "0.3.0",
                            "idempotency_key": idempotency_key,
                            "input": {"customer_id": "private"},
                        },
                        separators=(",", ":"),
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.loads(response.read().decode("utf-8")), receipt)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/webhooks/workflow_demo/0.3.0")
                self.assertEqual(
                    observed["body"],
                    {
                        "source": "live-ui",
                        "idempotency_key": idempotency_key,
                        "input": {"customer_id": "private"},
                    },
                )
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_rejects_client_selected_staged_input_source(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / "ingress.token"
            token_file.write_text("ui-test-token-012345678901234567890123456789\n", encoding="utf-8")
            os.chmod(token_file, 0o600)
            ui_port = {}
            ui_thread = threading.Thread(
                target=serve_ui,
                kwargs={
                    "host": "127.0.0.1", "port": 0, "once": True,
                    "service_url": "http://127.0.0.1:1", "auth_token_file": token_file,
                    "ready_callback": lambda server: ui_port.update({"value": server.server_port}),
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
                f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-input-triggers",
                data=(
                    b'{"workflow_id":"workflow_demo","version":"0.3.0",'
                    b'"idempotency_key":"live-ui-test","input":{},"source":"browser"}'
                ),
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=2)
            error = raised.exception
            try:
                self.assertEqual(error.code, 400)
                self.assertEqual(
                    json.loads(error.read().decode("utf-8")),
                    {"error": "workflow input trigger body is malformed"},
                )
            finally:
                error.close()
            ui_thread.join(timeout=2)
            self.assertFalse(ui_thread.is_alive())

    def test_live_proxy_rejects_nonempty_empty_trigger_body_before_upstream(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / "ingress.token"
            token_file.write_text("ui-test-token-012345678901234567890123456789\n", encoding="utf-8")
            os.chmod(token_file, 0o600)
            ui_port = {}

            def ready(server):
                ui_port["value"] = server.server_port

            ui_thread = threading.Thread(
                target=serve_ui,
                kwargs={
                    "host": "127.0.0.1", "port": 0, "once": True,
                    "service_url": "http://127.0.0.1:1", "auth_token_file": token_file,
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
                f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-empty-triggers",
                data=b'{"workflow_id":"workflow_demo","version":"0.3.0","idempotency_key":"live-ui-test","input":{"secret":"no"}}',
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=2)
            error = raised.exception
            try:
                self.assertEqual(error.code, 400)
                self.assertEqual(
                    json.loads(error.read().decode("utf-8")),
                    {"error": "workflow empty trigger body is malformed"},
                )
            finally:
                error.close()
            ui_thread.join(timeout=2)
            self.assertFalse(ui_thread.is_alive())

    def test_live_proxy_rejects_malformed_workflow_publication_before_upstream(self):
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
                    "service_url": "http://127.0.0.1:1",
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
                f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-releases",
                data=b'{"workflow":[]}',
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=2)
            error = raised.exception
            try:
                self.assertEqual(error.code, 400)
                self.assertEqual(
                    json.loads(error.read().decode("utf-8")),
                    {"error": "workflow publication body is malformed"},
                )
            finally:
                error.close()
            ui_thread.join(timeout=2)
            self.assertFalse(ui_thread.is_alive())

    def test_live_proxy_deprecates_workflow_with_compare_and_swap_without_browser_token(self):
        observed = {}
        deprecation = {
            "schema_version": "skill2workflow-workflow-deprecation-0.1.0",
            "workflow_id": "workflow_demo",
            "version": "0.2.0",
            "status": "deprecated",
            "checksum": "b" * 64,
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = json.dumps(deprecation, separators=(",", ":")).encode("utf-8")
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
                    f"http://127.0.0.1:{ui_port['value']}/api/v1/workflow-deprecations",
                    data=json.dumps(
                        {
                            "workflow_id": "workflow_demo",
                            "version": "0.2.0",
                            "expected_checksum": "b" * 64,
                            "expected_aliases": [],
                        },
                        separators=(",", ":"),
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["status"], "deprecated")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(observed["path"], "/api/v1/workflow-deprecations")
                self.assertEqual(
                    observed["body"],
                    {
                        "workflow_id": "workflow_demo",
                        "version": "0.2.0",
                        "expected_checksum": "b" * 64,
                        "expected_aliases": [],
                    },
                )
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_workflow_explanation_without_browser_token(self):
        observed = {}
        explanation = {
            "schema_version": "skill2workflow-workflow-explanation-0.1.0",
            "workflow": {"id": "workflow_demo", "version": "0.1.0", "status": "published"},
            "entry": "start",
            "summary": {
                "node_count": 2,
                "edge_count": 1,
                "human_gate_count": 0,
                "connector_node_count": 0,
                "side_effecting_node_count": 0,
                "terminal_node_count": 1,
                "retrying_node_count": 0,
                "timed_node_count": 0,
                "input_property_count": 0,
                "required_input_count": 0,
            },
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "transitions": {"success": "end", "failure": None, "fallback": None},
                    "connector": None,
                    "external_side_effect": False,
                    "retry": {"max_attempts": 0, "backoff_ms": 0},
                    "timeout_ms": None,
                },
                {
                    "id": "end",
                    "type": "end",
                    "transitions": {"success": None, "failure": None, "fallback": None},
                    "connector": None,
                    "external_side_effect": False,
                    "retry": {"max_attempts": 0, "backoff_ms": 0},
                    "timeout_ms": None,
                },
            ],
            "edges": [{"from": "start", "to": "end", "label": "next", "conditioned": False}],
            "input_contract": {
                "present": False,
                "type": "object",
                "required": [],
                "properties": [],
                "additional_properties": True,
            },
            "policies": {
                "default_retry": {"max_attempts": 0, "backoff_ms": 0},
                "default_timeout_ms": None,
                "workflow_timeout_ms": None,
            },
            "safety": {
                "side_effect_free": True,
                "connector_calls": False,
                "credentials_resolved": False,
                "raw_values_included": False,
            },
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                body = json.dumps(explanation, separators=(",", ":")).encode("utf-8")
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
                    "http://127.0.0.1:{}/api/v1/workflow-explanations/workflow_demo/0.1.0".format(
                        ui_port["value"]
                    ),
                    timeout=2,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["workflow"]["id"], "workflow_demo")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(
                    observed["path"],
                    "/api/v1/workflow-explanations/workflow_demo/0.1.0",
                )
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_workflow_diff_without_browser_token(self):
        observed = {}
        diff = {
            "schema_version": "skill2workflow-workflow-diff-0.1.0",
            "workflow_id": "workflow_demo",
            "from": {
                "version": "0.1.0",
                "status": "published",
                "checksum": "a" * 64,
                "aliases": ["stable"],
            },
            "to": {
                "version": "0.2.0",
                "status": "published",
                "checksum": "b" * 64,
                "aliases": ["production"],
            },
            "changed": True,
            "changes": {
                "sections": ["nodes", "policies"],
                "workflow_changed": False,
                "entry_changed": False,
                "input_schema_changed": False,
                "policies_changed": True,
                "other_changed": False,
                "nodes": {"added": ["call"], "removed": [], "changed": []},
                "edges": {"added": ["start->call"], "removed": [], "changed": []},
            },
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                body = json.dumps(diff, separators=(",", ":")).encode("utf-8")
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
                    "http://127.0.0.1:{}/api/v1/workflow-diffs/workflow_demo/0.1.0/0.2.0".format(
                        ui_port["value"]
                    ),
                    timeout=2,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertTrue(payload["changed"])
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(
                    observed["path"],
                    "/api/v1/workflow-diffs/workflow_demo/0.1.0/0.2.0",
                )
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)

    def test_live_proxy_exposes_empty_workflow_preflight_without_browser_token(self):
        observed = {}
        report = {
            "schema_version": "skill2workflow-workflow-preflight-0.1.0",
            "workflow": {"id": "workflow_demo", "version": "0.1.0", "status": "published"},
            "ready": True,
            "input": {
                "provided": False,
                "status": "valid",
                "provided_property_count": 0,
                "declared_property_count": 0,
                "required_property_count": 0,
                "missing_required_count": 0,
                "unknown_property_count": 0,
                "error_code": None,
                "error_path": None,
            },
            "summary": {
                "node_count": 2,
                "connector_node_count": 0,
                "side_effecting_node_count": 0,
                "mapping_count": 0,
                "blocked_node_count": 0,
                "issue_count": 0,
            },
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "connector": None,
                    "input_mapping": {
                        "status": "not_applicable",
                        "mapping_count": 0,
                        "mapped_count": 0,
                        "missing_required_count": 0,
                        "missing_optional_count": 0,
                    },
                },
                {
                    "id": "end",
                    "type": "end",
                    "connector": None,
                    "input_mapping": {
                        "status": "not_applicable",
                        "mapping_count": 0,
                        "mapped_count": 0,
                        "missing_required_count": 0,
                        "missing_optional_count": 0,
                    },
                },
            ],
            "issues": [],
            "safety": {
                "side_effect_free": True,
                "connector_calls": False,
                "credentials_resolved": False,
                "raw_values_included": False,
            },
        }

        class UpstreamHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed["authorization"] = self.headers.get("Authorization", "")
                observed["path"] = self.path
                observed["body"] = self.rfile.read(int(self.headers["Content-Length"]))
                body = json.dumps(report, separators=(",", ":")).encode("utf-8")
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
                    "http://127.0.0.1:{}/api/v1/workflow-preflights/workflow_demo/0.1.0".format(
                        ui_port["value"]
                    ),
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                    self.assertTrue(payload["ready"])
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                ui_thread.join(timeout=2)
                self.assertFalse(ui_thread.is_alive())
                self.assertEqual(
                    observed["path"],
                    "/api/v1/workflow-preflights/workflow_demo/0.1.0",
                )
                self.assertEqual(observed["body"], b"{}")
                self.assertEqual(
                    observed["authorization"],
                    "Bearer ui-test-token-012345678901234567890123456789",
                )
        finally:
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join(timeout=2)
