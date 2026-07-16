from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class LarkLiveConnectorValidationDocsTests(TestCase):
    def test_live_validation_evidence_is_compact_and_redacted(self):
        evidence = (ROOT / "docs" / "lark-live-connector-validation.md").read_text(encoding="utf-8")

        self.assertIn("# Lark/Feishu Live Connector Validation", evidence)
        self.assertIn("- connector_id: `lark_task`", evidence)
        self.assertIn("- operation: `create_task`", evidence)
        self.assertIn("- mode: `live`", evidence)
        self.assertIn("- credential_status: `resolved`", evidence)
        self.assertIn("- idempotency_key_present: `true`", evidence)
        self.assertIn("- provider_status: `completed`", evidence)
        self.assertIn("- lark_task_id_present: `true`", evidence)
        self.assertIn("- assignee_present: `true`", evidence)
        self.assertIn(
            "Raw task values, user ids, credentials, request bodies, response bodies, and task ids are intentionally omitted.",
            evidence,
        )
