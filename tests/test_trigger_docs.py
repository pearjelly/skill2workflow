import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class TriggerDocumentationTests(TestCase):
    def test_trigger_guide_publishes_durable_idempotency_boundary(self):
        guide = (ROOT / "docs" / "triggers.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for phrase in (
            "Durable Trigger Idempotency",
            "128 UTF-8 bytes",
            "request fingerprint",
            "completed identical request",
            "HTTP `409`",
            "unresolved outcome",
            "stores trigger input values, credentials",
            "backup and restore",
            "evaluation remains metadata-only",
        ):
            self.assertIn(phrase, guide)
        self.assertIn("Loop 62: Durable SQLite Trigger Idempotency", roadmap)
        self.assertIn("docs/triggers.md#durable-trigger-idempotency", readme)

    def test_trigger_ledger_is_not_a_payload_store(self):
        schema = json.loads(
            (ROOT / "schemas" / "state-layout-marker-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            schema["properties"]["state_layout_version"]["const"],
            "skill2workflow-sqlite-layout-0.1.0",
        )
        source = (ROOT / "src" / "skill2workflow" / "storage.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("trigger_idempotency", source)
        self.assertIn("request_fingerprint", source)
        self.assertIn("response_json", source)
        self.assertNotIn("input_json", source)
