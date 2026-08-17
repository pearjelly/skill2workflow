import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class QuickstartSchemaTests(TestCase):
    def test_quickstart_result_schema_locks_secret_free_operator_commands(self):
        schema = json.loads(
            (ROOT / "schemas" / "quickstart-result-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/quickstart-result-0.1.0.schema.json",
        )
        self.assertTrue(schema["additionalProperties"] is False)
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-quickstart-result-0.1.0",
        )
        commands = schema["properties"]["operator_commands"]
        self.assertTrue(commands["additionalProperties"] is False)
        self.assertEqual(
            set(commands["required"]),
            {"inspect_run", "approve_run", "service_doctor", "start_service"},
        )
        self.assertEqual(commands["properties"]["inspect_run"]["$ref"], "#/$defs/argv")
