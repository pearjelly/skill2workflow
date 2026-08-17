import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class MigrationDocumentationTests(TestCase):
    def test_state_layout_marker_schema_matches_runtime_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "state-layout-marker-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-state-layout-marker-0.1.0",
        )
        self.assertEqual(
            schema["properties"]["state_layout_version"]["const"],
            "skill2workflow-sqlite-layout-0.1.0",
        )
        self.assertEqual(
            schema["properties"]["service_initialized"]["type"],
            "boolean",
        )
        self.assertFalse(schema["additionalProperties"])

    def test_operator_guide_defines_preflight_backup_cutover_and_rollback(self):
        guide = (ROOT / "docs" / "upgrade-migration.md").read_text(encoding="utf-8")
        normalized = guide.lower()

        for text in (
            "state-upgrade-plan",
            "state-upgrade",
            "stop the service",
            "pre-upgrade backup",
            "copy-on-write",
            "must not already exist",
            "rollback",
            "old binary",
            "future layout",
            "state_upgrade_smoke.py",
            "atomic, non-overwriting publication path",
        ):
            self.assertIn(text, normalized)

    def test_readme_and_roadmap_record_loop_45_without_overclaiming_production(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Delivery Loops 1-204 are complete", readme)
        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("docs/upgrade-migration.md", readme)
        self.assertIn("- Completed delivery loops: 1-204", roadmap)
        self.assertIn("- Current maturity: Self-hosted Beta", roadmap)
        self.assertIn("| Loop 45: State Upgrade And Migration | Complete |", roadmap)
        self.assertIn("Production Baseline remains directional", roadmap)
