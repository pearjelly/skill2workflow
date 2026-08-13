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
            "retry.backoff_ms",
            "60,000 milliseconds",
            "bounded connector retry backoff",
            "policies.default_timeout_ms",
            "active-execution segment",
            "execution_timeout",
            "human gate is waiting",
            "policies.workflow_timeout_ms",
            "workflow_timeout",
            "30 days",
            "global wall-clock deadline",
            "bounded deadline sweep",
            "active scheduler lease",
            "pending cancellation wins over expiry",
            "256 candidates per pass",
            "automatic idempotency enforcement for JSON/local evaluation",
            "on_fallback",
            "node_fallback",
        ):
            self.assertIn(phrase, guide)
        self.assertIn("execution_timeout", compatibility)
        self.assertEqual(
            schema["$defs"]["policies"]["properties"]["default_timeout_ms"]["maximum"],
            86400000,
        )
        self.assertEqual(
            schema["$defs"]["retry_policy"]["properties"]["backoff_ms"]["maximum"],
            60000,
        )
        self.assertEqual(
            schema["$defs"]["policies"]["properties"]["workflow_timeout_ms"]["maximum"],
            2_592_000_000,
        )
