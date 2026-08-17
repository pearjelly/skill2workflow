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

    def test_inventory_schema_matches_bounded_value_free_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "state-backup-list-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-state-backup-list-0.1.0",
        )
        self.assertEqual(schema["properties"]["backups"]["maxItems"], 1000)
        self.assertEqual(schema["$defs"]["window"]["properties"]["max_items"]["maximum"], 1000)
        self.assertEqual(
            schema["$defs"]["backup"]["properties"]["status"]["enum"],
            ["valid", "invalid"],
        )
        self.assertNotIn("path", schema["$defs"]["backup"]["properties"])

    def test_retention_policy_and_plan_schemas_match_fail_closed_contract(self):
        policy = json.loads(
            (ROOT / "schemas" / "backup-retention-policy-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        plan = json.loads(
            (ROOT / "schemas" / "backup-retention-plan-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            policy["properties"]["schema_version"]["const"],
            "skill2workflow-backup-retention-policy-0.1.0",
        )
        self.assertEqual(
            policy["properties"]["retention"]["properties"]["minimum_keep"]["maximum"],
            1000,
        )
        self.assertEqual(
            plan["properties"]["schema_version"]["const"],
            "skill2workflow-backup-retention-plan-0.1.0",
        )
        self.assertEqual(
            plan["properties"]["blocking_reasons"]["items"]["enum"],
            ["inventory_truncated"],
        )
        self.assertNotIn("delete", plan["properties"])

    def test_remote_retention_plan_schema_and_guide_match_redacted_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "remote-backup-retention-plan-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        guide = (ROOT / "docs" / "remote-backup-retention-plan.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-remote-backup-retention-plan-0.1.0",
        )
        self.assertEqual(
            schema["properties"]["blocking_reasons"]["items"]["enum"],
            ["inventory_truncated"],
        )
        self.assertNotIn("name", schema["properties"])
        for text in (
            "POST /api/v1/backup-retention-plan",
            "service-backup-retention-plan",
            "inventory_truncated",
            "never performs deletion",
            "Backup\nnames",
            "after observing the first 1,001 sets",
            "lower-bound scan",
        ):
            self.assertIn(text, guide)

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
            "backup-list",
            "read-only",
            "absolute paths",
            "integrity status",
            "state-backup-list-0.1.0.schema.json",
            "backup-retention-plan",
            "minimum_keep",
            "inventory_truncated",
            "backup-retention-policy-0.1.0.schema.json",
            "backup-retention-plan-0.1.0.schema.json",
            "workflow registry is read through a stable cursor",
        ):
            self.assertIn(text, guide)

    def test_inventory_contract_is_recorded_in_public_docs(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "backup-restore.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(
            encoding="utf-8"
        )

        for document in (readme, stability, changelog, package_smoke):
            self.assertIn("backup-list", document)
        self.assertIn("service-backup-retention-plan", readme)
        self.assertIn("service-backup-retention-plan", stability)
        self.assertIn("service-backup-retention-plan", changelog)
        self.assertIn('"service-backup-retention-plan"', package_smoke)
        self.assertIn("1-1000", stability)
        self.assertIn("does not delete, upload, or rewrite", guide)
        self.assertIn('"backup-list"', package_smoke)

    def test_readme_and_roadmap_record_loop_44_without_overclaiming_production(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Delivery Loops 1-174 are complete", readme)
        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("docs/backup-restore.md", readme)
        self.assertIn("- Completed delivery loops: 1-174", roadmap)
        self.assertIn("- Current maturity: Self-hosted Beta", roadmap)
        self.assertIn("| Loop 44: Verified Backup And Restore | Complete |", roadmap)
        self.assertIn("Production Baseline remains directional", roadmap)
