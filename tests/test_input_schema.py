import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.compiler import validate_workflow, validate_workflow_structured
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.input_schema import (
    INPUT_SCHEMA_MAX_BYTES,
    InputSchemaValidationError,
    validate_input_schema_contract,
    validate_trigger_input,
)


class InputSchemaTests(TestCase):
    def test_contract_accepts_bounded_recursive_subset(self):
        schema = _input_schema()

        self.assertEqual(validate_input_schema_contract(schema), [])
        validate_trigger_input(
            schema,
            {"customer_id": "customer_123", "priority": "high", "count": 2},
        )

    def test_contract_rejects_unsupported_keywords_and_unbounded_shape(self):
        errors = validate_input_schema_contract(
            {
                "type": "object",
                "properties": {"name": {"type": "string", "pattern": ".*"}},
                "allOf": [],
            }
        )

        codes = {str(error["code"]) for error in errors}
        self.assertIn("input_schema_keyword_unsupported", codes)
        self.assertNotIn("input_schema_keyword_invalid", codes)

    def test_contract_rejects_oversized_schema_before_publication(self):
        schema = {
            "type": "object",
            "properties": {"payload": {"type": "string", "enum": ["x" * INPUT_SCHEMA_MAX_BYTES]}},
        }

        errors = validate_input_schema_contract(schema)

        self.assertIn("input_schema_too_large", {str(error["code"]) for error in errors})

    def test_runtime_rejects_missing_wrong_and_unknown_values_without_echoing_data(self):
        schema = _input_schema()
        cases = [
            ({"priority": "high"}, "input_required"),
            ({"customer_id": 123}, "input_type"),
            ({"customer_id": "sensitive-value", "unexpected": True}, "input_unknown_property"),
        ]
        for value, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(InputSchemaValidationError) as raised:
                    validate_trigger_input(schema, value)
                self.assertEqual(raised.exception.code, code)
                self.assertNotIn("sensitive-value", str(raised.exception))

    def test_publish_and_trigger_enforce_contract_before_sqlite_idempotency_claim(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            workflow = _workflow()
            control.publish_workflow(workflow)

            with self.assertRaisesRegex(ValueError, "wrong type"):
                control.trigger_workflow(
                    {
                        "workflow_id": "workflow_input_contract",
                        "version": "0.1.0",
                        "idempotency_key": "invalid-input-1",
                        "input": {"customer_id": 123},
                    }
                )

            self.assertEqual(control.list_runs(), [])
            with sqlite3.connect(state_dir / "control.sqlite3") as connection:
                self.assertEqual(
                    connection.execute("select count(*) from trigger_idempotency").fetchone()[0],
                    0,
                )

            result = control.trigger_workflow(
                {
                    "workflow_id": "workflow_input_contract",
                    "version": "0.1.0",
                    "idempotency_key": "valid-input-1",
                    "input": {"customer_id": "customer_123", "priority": "normal"},
                }
            )

        self.assertEqual(result["run_status"], "completed")

    def test_publish_rejects_malformed_input_schema(self):
        workflow = _workflow()
        workflow["input_schema"] = {"type": "string"}

        errors = validate_workflow_structured(workflow)

        self.assertIn("input_schema_root_invalid", {str(error["code"]) for error in errors})
        self.assertTrue(any("input_schema" in message for message in validate_workflow(workflow)))

    def test_workflows_without_input_schema_remain_compatible(self):
        workflow = _workflow()
        workflow.pop("input_schema")

        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(workflow)
            result = control.trigger_workflow(
                {
                    "workflow_id": "workflow_input_contract",
                    "version": "0.1.0",
                    "input": {"legacy": "accepted"},
                }
            )

        self.assertEqual(result["run_status"], "completed")

    def test_contract_docs_and_roadmap_describe_the_boundary(self):
        root = Path(__file__).resolve().parents[1]
        contract_docs = (root / "docs" / "workflow-dsl-contract.md").read_text(encoding="utf-8")
        trigger_docs = (root / "docs" / "triggers.md").read_text(encoding="utf-8")
        roadmap = (root / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Declarative Trigger Input Contracts", contract_docs)
        self.assertIn("before SQLite idempotency claims", trigger_docs)
        self.assertIn("Loop 67: Declarative Trigger Input Contracts", roadmap)


def _input_schema():
    return {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "minLength": 1},
            "priority": {"type": "string", "enum": ["high", "normal"]},
            "count": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        "required": ["customer_id"],
        "additionalProperties": False,
    }


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_input_contract",
            "name": "Input contract",
            "description": "Input contract test fixture",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_end", "from": "start", "to": "end", "condition": None, "label": "next"}
        ],
        "input_schema": _input_schema(),
    }
