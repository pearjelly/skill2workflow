import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.cli import main
from skill2workflow.explain import (
    MAX_WORKFLOW_EXPLANATION_BYTES,
    WORKFLOW_EXPLANATION_SCHEMA_VERSION,
    build_workflow_explanation,
)


class WorkflowExplanationTests(TestCase):
    def test_explanation_is_structural_and_does_not_copy_connector_values(self):
        workflow = _workflow()

        explanation = build_workflow_explanation(workflow)

        self.assertEqual(
            explanation["schema_version"], WORKFLOW_EXPLANATION_SCHEMA_VERSION
        )
        self.assertEqual(explanation["workflow"], {
            "id": "workflow_explain",
            "version": "0.1.0",
            "status": "draft",
        })
        self.assertEqual(explanation["entry"], "start")
        self.assertEqual(explanation["summary"]["node_count"], 5)
        self.assertEqual(explanation["summary"]["human_gate_count"], 1)
        self.assertEqual(explanation["summary"]["connector_node_count"], 1)
        self.assertEqual(explanation["summary"]["side_effecting_node_count"], 1)
        self.assertEqual(explanation["input_contract"]["required"], ["customer_id"])
        self.assertEqual(explanation["input_contract"]["properties"][0], {
            "name": "customer_id",
            "type": "string",
            "required": True,
            "nested": False,
        })
        connector = next(node for node in explanation["nodes"] if node["id"] == "call_api")
        self.assertEqual(connector["connector"], {
            "id": "http",
            "kind": "http",
            "method": "POST",
            "credential_handle_count": 1,
            "input_mapping_count": 1,
            "external_side_effect": True,
        })
        self.assertEqual(explanation["safety"], {
            "side_effect_free": True,
            "connector_calls": False,
            "credentials_resolved": False,
            "raw_values_included": False,
        })
        encoded = json.dumps(explanation, ensure_ascii=False, sort_keys=True)
        for secret in ("https://private.example/secret", "Bearer private-header", "private-body", "private-credential", "do-not-copy"):
            self.assertNotIn(secret, encoded)

    def test_explanation_is_deterministic_and_bounded(self):
        workflow = _workflow()
        first = build_workflow_explanation(workflow)
        second = build_workflow_explanation(json.loads(json.dumps(workflow)))
        self.assertEqual(first, second)
        encoded = json.dumps(first, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.assertLessEqual(len(encoded), MAX_WORKFLOW_EXPLANATION_BYTES)

    def test_cli_explain_json_and_text_are_read_only(self):
        with TemporaryDirectory() as tmp:
            workflow_path = Path(tmp) / "workflow.json"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            json_stdout = StringIO()
            with redirect_stdout(json_stdout):
                self.assertEqual(main(["explain", str(workflow_path)]), 0)
            payload = json.loads(json_stdout.getvalue())
            self.assertEqual(payload["schema_version"], WORKFLOW_EXPLANATION_SCHEMA_VERSION)

            text_stdout = StringIO()
            with redirect_stdout(text_stdout):
                self.assertEqual(main(["explain", str(workflow_path), "--format", "text"]), 0)
            self.assertIn("workflow_explain@0.1.0", text_stdout.getvalue())
            self.assertIn("external side effects: 1", text_stdout.getvalue())

    def test_cli_explain_rejects_invalid_workflow_without_traceback(self):
        with TemporaryDirectory() as tmp:
            workflow_path = Path(tmp) / "invalid.json"
            workflow_path.write_text("{}", encoding="utf-8")
            stderr = StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main(["explain", str(workflow_path)]), 1)
            self.assertIn("workflow.schema_version must be 0.1.0", stderr.getvalue())


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_explain",
            "name": "private name should not be copied",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "private_field": {"type": "string"},
            },
            "required": ["customer_id"],
            "additionalProperties": False,
        },
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "title": "Start",
                "on_success": "review",
            },
            {
                "id": "review",
                "type": "human_gate",
                "title": "Review",
                "on_success": "call_api",
                "on_failure": "failure",
                "retry": {"max_attempts": 0},
            },
            {
                "id": "call_api",
                "type": "tool_call",
                "title": "Call endpoint",
                "on_success": "end",
                "on_failure": "failure",
                "timeout_ms": 2500,
                "retry": {"max_attempts": 2, "backoff_ms": 100},
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "credentials": [{"handle": "private-credential"}],
                    "request": {
                        "method": "POST",
                        "url": "https://private.example/secret",
                        "headers": {"Authorization": "Bearer private-header"},
                        "body": {"value": "private-body"},
                        "input_mapping": [
                            {"from": "/input/customer_id", "to": "/body/customer_id"}
                        ],
                    },
                },
                "action": {"instruction": "do-not-copy"},
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "e1", "from": "start", "to": "review", "label": "next"},
            {"id": "e2", "from": "review", "to": "call_api", "label": "next"},
            {"id": "e3", "from": "review", "to": "failure", "label": "failure", "condition": {"expr": "secret"}},
            {"id": "e4", "from": "call_api", "to": "end", "label": "next"},
            {"id": "e5", "from": "call_api", "to": "failure", "label": "failure", "condition": {"expr": "secret"}},
        ],
        "policies": {
            "default_retry": {"max_attempts": 1, "backoff_ms": 50},
            "default_timeout_ms": 300000,
            "workflow_timeout_ms": 600000,
        },
    }
