import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RemoteAuditEventsDocumentationTests(TestCase):
    def test_schema_and_guide_publish_bounded_redacted_cursor_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "audit-event-list-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        guide = (ROOT / "docs" / "remote-audit-events.md").read_text(encoding="utf-8")
        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/audit-event-list-0.1.0.schema.json",
        )
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-audit-event-list-0.1.0",
        )
        self.assertEqual(schema["properties"]["events"]["maxItems"], 100)
        self.assertEqual(schema["$defs"]["window"]["properties"]["max_items"]["maximum"], 100)
        for phrase in (
            "GET /api/v1/audit-events",
            "opaque",
            "64 KiB",
            "raw provider errors",
            "credential values",
            "service-audit-events",
            "does not acquire the scheduler lease",
            "sequence order",
        ):
            self.assertIn(phrase, guide)

    def test_public_docs_and_packaging_expose_remote_audit_events(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        service = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(encoding="utf-8")
        self.assertIn("docs/remote-audit-events.md", readme)
        self.assertIn("GET /api/v1/audit-events", service)
        self.assertIn("service-audit-events", stability)
        self.assertIn('"service-audit-events"', package_smoke)
