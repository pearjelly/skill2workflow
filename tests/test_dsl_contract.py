import json
from pathlib import Path
from unittest import TestCase

from skill2workflow.compiler import validate_workflow, validate_workflow_structured


ROOT = Path(__file__).resolve().parents[1]


class DslContractTests(TestCase):
    def test_workflow_schema_is_versioned_and_documents_required_fields(self):
        schema = json.loads((ROOT / "schemas" / "workflow.schema.json").read_text(encoding="utf-8"))

        self.assertEqual(schema["$id"], "https://skill2workflow.dev/schemas/workflow-0.1.0.json")
        self.assertEqual(schema["title"], "skill2workflow Workflow DSL")
        self.assertEqual(schema["properties"]["schema_version"]["const"], "0.1.0")
        self.assertEqual(
            schema["required"],
            ["schema_version", "workflow", "entry", "nodes", "edges"],
        )
        self.assertIn("node", schema["$defs"])
        self.assertIn("edge", schema["$defs"])
        connector_properties = schema["$defs"]["connector_binding"]["properties"]
        self.assertIn("request", connector_properties)
        self.assertIn("credentials", connector_properties)
        request_properties = schema["$defs"]["connector_request"]["properties"]
        self.assertIn("input_mapping", request_properties)
        self.assertEqual(request_properties["input_mapping"]["items"]["properties"]["from"]["pattern"], "^/input/.+")
        self.assertEqual(request_properties["input_mapping"]["items"]["properties"]["to"]["pattern"], "^/body/.+")

    def test_approval_flow_example_is_a_golden_valid_workflow_fixture(self):
        workflow = json.loads(
            (ROOT / "examples" / "workflows" / "approval-flow.workflow.json").read_text(encoding="utf-8")
        )

        self.assertEqual(validate_workflow_structured(workflow), [])
        self.assertEqual(validate_workflow(workflow), [])
        self.assertEqual(workflow["schema_version"], "0.1.0")

    def test_all_example_workflows_are_valid_contract_fixtures(self):
        workflow_paths = sorted((ROOT / "examples" / "workflows").glob("*.workflow.json"))

        self.assertGreaterEqual(len(workflow_paths), 2)
        for path in workflow_paths:
            with self.subTest(path=path.name):
                workflow = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_workflow_structured(workflow), [])

    def test_structured_validation_errors_have_codes_paths_and_messages(self):
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {"id": "workflow_invalid", "name": "invalid", "version": "0.1.0", "status": "draft"},
            "entry": "missing",
            "nodes": [
                {"id": "start", "type": "start", "title": "Start", "on_success": "step"},
                {"id": "step", "type": "step", "title": "Step", "on_success": "end", "on_failure": "failure"},
                {"id": "failure", "type": "failure", "title": "Failure"},
                {"id": "end", "type": "end", "title": "End"},
            ],
            "edges": [
                {"id": "edge_1", "from": "start", "to": "missing", "condition": None, "label": "next"},
                {"id": "edge_1", "from": "step", "to": "end", "condition": None, "label": "next"},
            ],
        }

        errors = validate_workflow_structured(workflow)

        self.assertIn(
            {
                "code": "entry_missing",
                "message": "workflow.entry must reference an existing node",
                "path": ["entry"],
                "severity": "error",
            },
            errors,
        )
        self.assertIn(
            {
                "code": "duplicate_edge_id",
                "message": "edge ids must be unique",
                "path": ["edges"],
                "severity": "error",
            },
            errors,
        )
        self.assertIn(
            {
                "code": "edge_target_missing",
                "message": "edge_1.to references missing node missing",
                "path": ["edges", 0, "to"],
                "severity": "error",
            },
            errors,
        )
