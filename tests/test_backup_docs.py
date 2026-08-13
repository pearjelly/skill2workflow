import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class BackupDocumentationTests(TestCase):
    def test_manifest_schema_matches_runtime_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "state-backup-manifest-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-state-backup-0.1.0",
        )
        self.assertEqual(schema["properties"]["database_count"]["const"], 3)
        self.assertEqual(
            schema["properties"]["state_layout_version"]["enum"],
            [
                "skill2workflow-sqlite-layout-legacy-unversioned",
                "skill2workflow-sqlite-layout-0.1.0",
            ],
        )
        self.assertTrue(schema["properties"]["scheduler_leases_cleared"]["const"])
        self.assertEqual(
            schema["properties"]["scheduler_database_synthesized"]["type"],
            "boolean",
        )
        self.assertEqual(
            schema["properties"]["files"]["items"]["properties"]["sha256"]["pattern"],
            "^[0-9a-f]{64}$",
        )
        self.assertIn(
            "workflows/",
            schema["properties"]["files"]["items"]["properties"]["path"]["pattern"],
        )
        self.assertIn(
            "state_layout",
            schema["properties"]["files"]["items"]["properties"]["kind"]["enum"],
        )
        self.assertFalse(schema["additionalProperties"])

    def test_operator_guide_defines_offline_security_and_recovery_drill(self):
        guide = (ROOT / "docs" / "backup-restore.md").read_text(encoding="utf-8")

        for text in (
            "skill2workflow-state-backup-0.1.0",
            "stop the service",
            "offline",
            "backup-verify",
            "integrity_check",
            "SHA-256",
            "must not already exist",
            "credentials are not included",
            "owner-only",
            "encrypt",
            "backup_restore_smoke.py",
        ):
            self.assertIn(text, guide)

    def test_readme_and_roadmap_record_loop_44_without_overclaiming_production(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Delivery Loops 1-113 are complete", readme)
        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("docs/backup-restore.md", readme)
        self.assertIn("- Completed delivery loops: 1-113", roadmap)
        self.assertIn("- Current maturity: Self-hosted Beta", roadmap)
        self.assertIn("| Loop 44: Verified Backup And Restore | Complete |", roadmap)
        self.assertIn("Production Baseline remains directional", roadmap)
