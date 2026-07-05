import json
import threading
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.webhooks import (
    WebhookError,
    handle_webhook_request,
    parse_webhook_request,
    serve_webhook_requests,
)


class WebhookTests(TestCase):
    def test_parse_webhook_request_maps_post_body_to_trigger_request(self):
        request = parse_webhook_request(
            "POST",
            "/webhooks/workflow_demo/0.1.0",
            json.dumps(
                {
                    "source": "partner-system",
                    "idempotency_key": "event-001",
                    "input": {
                        "customer_id": "customer_123",
                        "priority": "high",
                    },
                }
            ).encode("utf-8"),
        )

        self.assertEqual(
            request,
            {
                "workflow_id": "workflow_demo",
                "version": "0.1.0",
                "source": "partner-system",
                "idempotency_key": "event-001",
                "input": {
                    "customer_id": "customer_123",
                    "priority": "high",
                },
            },
        )

    def test_parse_webhook_request_defaults_source_and_input(self):
        request = parse_webhook_request("POST", "/webhooks/workflow_demo/0.1.0", b"{}")

        self.assertEqual(request["workflow_id"], "workflow_demo")
        self.assertEqual(request["version"], "0.1.0")
        self.assertEqual(request["source"], "local-webhook")
        self.assertEqual(request["idempotency_key"], "")
        self.assertEqual(request["input"], {})

    def test_parse_webhook_request_rejects_invalid_requests(self):
        cases = [
            ("GET", "/webhooks/workflow_demo/0.1.0", b"{}", 405, "webhook requests must use POST"),
            ("POST", "/wrong/workflow_demo/0.1.0", b"{}", 404, "webhook path must be /webhooks/<workflow_id>/<version>"),
            ("POST", "/webhooks/workflow_demo", b"{}", 404, "webhook path must be /webhooks/<workflow_id>/<version>"),
            ("POST", "/webhooks/workflow_demo/0.1.0", b"{", 400, "webhook body must be valid JSON"),
            ("POST", "/webhooks/workflow_demo/0.1.0", b"[]", 400, "webhook body must be a JSON object"),
            (
                "POST",
                "/webhooks/workflow_demo/0.1.0",
                json.dumps({"input": []}).encode("utf-8"),
                400,
                "webhook input must be a JSON object",
            ),
        ]

        for method, path, body, status_code, message in cases:
            with self.subTest(message=message):
                with self.assertRaises(WebhookError) as raised:
                    parse_webhook_request(method, path, body)
                self.assertEqual(raised.exception.status_code, status_code)
                self.assertEqual(str(raised.exception), message)

    def test_handle_webhook_request_triggers_published_workflow_with_compact_audit(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            control.publish_workflow(_workflow("1.0.0"))

            result = handle_webhook_request(
                control,
                "POST",
                "/webhooks/workflow_webhook/1.0.0",
                json.dumps(
                    {
                        "source": "partner-system",
                        "idempotency_key": "event-001",
                        "input": {"customer_id": "customer_123"},
                    }
                ).encode("utf-8"),
            )
            detail = control.get_run(result["run_id"])
            audit_events = control.list_audit_events(run_id=result["run_id"])

        self.assertTrue(result["trigger_id"].startswith("trigger_"))
        self.assertEqual(result["workflow_id"], "workflow_webhook")
        self.assertEqual(result["workflow_version"], "1.0.0")
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["source"], "partner-system")
        self.assertEqual(result["idempotency_key"], "event-001")
        self.assertEqual(result["input_keys"], ["customer_id"])
        self.assertNotIn("input", result)
        self.assertEqual(detail["context"]["input"], {"customer_id": "customer_123"})
        self.assertEqual(detail["context"]["trigger"]["source"], "partner-system")
        self.assertEqual([event["type"] for event in audit_events], ["run_started", "run_completed"])
        self.assertEqual(audit_events[0]["trigger_source"], "partner-system")
        self.assertEqual(audit_events[0]["input_keys"], ["customer_id"])
        self.assertNotIn("input", audit_events[0])

    def test_handle_webhook_request_works_with_sqlite_storage(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow("2.0.0"))

            result = handle_webhook_request(
                control,
                "POST",
                "/webhooks/workflow_webhook/2.0.0",
                json.dumps({"input": {"case_id": "case_123"}}).encode("utf-8"),
            )
            reloaded = LocalControlPlane(state_dir, storage="sqlite")
            detail = reloaded.get_run(result["run_id"])
            audit_events = reloaded.list_audit_events(run_id=result["run_id"])

        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(detail["context"]["input"], {"case_id": "case_123"})
        self.assertEqual(audit_events[0]["trigger_source"], "local-webhook")
        self.assertEqual(audit_events[0]["input_keys"], ["case_id"])

    def test_serve_webhook_requests_handles_one_local_post(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            control.publish_workflow(_workflow("3.0.0"))
            ready = threading.Event()
            address = {}

            thread = threading.Thread(
                target=serve_webhook_requests,
                kwargs={
                    "host": "127.0.0.1",
                    "port": 0,
                    "control_plane": control,
                    "once": True,
                    "ready_callback": lambda server: (address.update({"server": server.server_address}), ready.set()),
                },
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            host, port = address["server"]
            payload = json.dumps({"input": {"ticket_id": "ticket_123"}}).encode("utf-8")
            request = urllib.request.Request(
                f"http://{host}:{port}/webhooks/workflow_webhook/3.0.0",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(request, timeout=2) as response:
                status = response.status
                body = json.loads(response.read().decode("utf-8"))
            thread.join(timeout=2)

        self.assertEqual(status, 200)
        self.assertEqual(body["workflow_id"], "workflow_webhook")
        self.assertEqual(body["workflow_version"], "3.0.0")
        self.assertEqual(body["run_status"], "completed")
        self.assertEqual(body["input_keys"], ["ticket_id"])
        self.assertFalse(thread.is_alive())


def _workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_webhook",
            "name": "webhook",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }
