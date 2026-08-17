import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from skill2workflow.cli import main
from skill2workflow.preflight import (
    WORKFLOW_PREFLIGHT_SCHEMA_VERSION,
    build_workflow_preflight,
)


class WorkflowPreflightTests(unittest.TestCase):
    def setUp(self):
        self.workflow = json.loads(
            Path("examples/workflows/http-connector.workflow.json").read_text()
        )

    def test_missing_mapping_is_blocked_without_echoing_input(self):
        report = build_workflow_preflight(self.workflow)
        self.assertEqual(report["schema_version"], WORKFLOW_PREFLIGHT_SCHEMA_VERSION)
        self.assertFalse(report["ready"])
        self.assertEqual(report["summary"]["blocked_node_count"], 1)
        self.assertEqual(report["issues"][0]["code"], "required_mapping_input_missing")
        self.assertNotIn("example", json.dumps(report))
        self.assertEqual(report["safety"]["connector_calls"], False)
        self.assertEqual(report["safety"]["credentials_resolved"], False)

    def test_supplied_input_makes_mapping_ready(self):
        report = build_workflow_preflight(
            self.workflow,
            {"customer_id": "sensitive-value"},
            input_present=True,
        )
        self.assertTrue(report["ready"])
        self.assertEqual(report["input"]["provided_property_count"], 1)
        mapping = next(node for node in report["nodes"] if node["id"] == "call_api")["input_mapping"]
        self.assertEqual(mapping["status"], "ready")
        self.assertNotIn("sensitive-value", json.dumps(report))

    def test_input_schema_failure_is_value_free(self):
        workflow = copy.deepcopy(self.workflow)
        workflow["input_schema"] = {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
            "additionalProperties": False,
        }
        report = build_workflow_preflight(workflow, {"other": "secret"}, input_present=True)
        self.assertFalse(report["ready"])
        self.assertEqual(report["input"]["status"], "invalid")
        self.assertEqual(report["input"]["error_code"], "input_required")
        self.assertEqual(report["input"]["error_path"], ["input", "customer_id"])
        self.assertNotIn("secret", json.dumps(report))

    def test_cli_preflight_returns_nonzero_for_blocked_input(self):
        output = StringIO()
        with redirect_stdout(output):
            status = main([
                "preflight",
                "examples/workflows/http-connector.workflow.json",
                "--format",
                "json",
            ])
        self.assertEqual(status, 1)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ready"])

    def test_cli_preflight_accepts_object_input_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text('{"customer_id":"secret"}')
            output = StringIO()
            with redirect_stdout(output):
                status = main([
                    "preflight",
                    "examples/workflows/http-connector.workflow.json",
                    "--input",
                    str(path),
                ])
        self.assertEqual(status, 0)
        self.assertNotIn("secret", output.getvalue())
