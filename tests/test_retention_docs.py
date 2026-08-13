import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RetentionDocumentationTests(TestCase):
    def test_policy_schema_matches_fixed_safe_runtime_contract(self):
        schema = json.loads(
            (ROOT / "schemas/retention-policy-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-retention-policy-0.1.0",
        )
        retention = schema["properties"]["retention"]
        self.assertFalse(retention["additionalProperties"])
        self.assertEqual(
            retention["properties"]["terminal_run_statuses"]["prefixItems"][0][
                "const"
            ],
            "completed",
        )
        self.assertEqual(
            retention["properties"]["terminal_dispatch_statuses"]["maxItems"],
            4,
        )

    def test_operator_guide_defines_copy_disposal_cutover_and_residual_boundary(self):
        guide = (ROOT / "docs/data-retention.md").read_text(encoding="utf-8")

        for phrase in (
            "state-retention-plan",
            "state-retention-apply",
            "copy-on-write",
            "waiting",
            "claimed",
            "secure_delete",
            "VACUUM",
            "source directory",
            "backup",
            "cut over",
            "rollback",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guide)

    def test_readme_and_roadmap_record_loop_47_without_overclaiming_production(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Delivery Loops 1-74 are complete", readme)
        self.assertIn("Loop 47", readme)
        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("- Completed delivery loops: 1-74", roadmap)
        self.assertIn("Loop 47: Data Retention And Disposal", roadmap)
        self.assertIn("Current maturity remains Self-hosted Beta", roadmap)
