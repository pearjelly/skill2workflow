import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RuntimePolicyDocumentationTests(TestCase):
    def test_timeout_contract_is_documented_and_current(self):
        guide = (ROOT / "docs" / "runtime-policy.md").read_text(encoding="utf-8")
        compatibility = (ROOT / "docs" / "workflow-dsl-compatibility.md").read_text(
            encoding="utf-8"
        )
        schema = json.loads(
            (ROOT / "schemas" / "workflow.schema.json").read_text(encoding="utf-8")
        )
        for phrase in (
            "policies.default_timeout_ms",
            "active-execution segment",
            "execution_timeout",
            "human gate is waiting",
            "automatic idempotency enforcement for JSON/local evaluation",
        ):
            self.assertIn(phrase, guide)
        self.assertIn("execution_timeout", compatibility)
        self.assertEqual(
            schema["$defs"]["policies"]["properties"]["default_timeout_ms"]["maximum"],
            86400000,
        )
