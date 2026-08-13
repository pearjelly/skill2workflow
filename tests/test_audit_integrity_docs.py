import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class AuditIntegrityDocumentationTests(TestCase):
    def test_integrity_schema_and_operator_guide_publish_the_fixed_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "audit-integrity-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        guide = (ROOT / "docs" / "audit-integrity.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        remote_guide = (ROOT / "docs" / "remote-audit-integrity.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/audit-integrity-0.1.0.schema.json",
        )
        self.assertIn("sha256-chain-v1", guide)
        self.assertIn("audit-verify", guide)
        self.assertIn("backup-verify", guide)
        self.assertIn("Loop 65: SQLite Audit Integrity", roadmap)
        self.assertIn("audit integrity", changelog.lower())
        self.assertIn("GET /api/v1/audit-integrity", remote_guide)
        self.assertIn("service-audit-integrity", remote_guide)
        self.assertIn("16 KiB", remote_guide)
