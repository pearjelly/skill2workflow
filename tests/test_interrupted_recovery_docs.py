import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class InterruptedRecoveryDocumentationTests(TestCase):
    def test_guide_defines_unknown_outcome_fencing_takeover_and_operator_boundary(self):
        guide = (ROOT / "docs/interrupted-recovery.md").read_text(encoding="utf-8")

        for phrase in (
            "interrupted",
            "unknown external outcome",
            "execution ticket",
            "fencing",
            "scheduler lease",
            "waiting",
            "no automatic retry",
            "SIGKILL",
            "control-runs",
            "audit",
            "retention-policy-0.3.0",
            "exactly-once",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guide)

    def test_v3_retention_schema_has_exact_interrupted_terminal_contract(self):
        schema = json.loads(
            (ROOT / "schemas/retention-policy-0.3.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-retention-policy-0.3.0",
        )
        statuses = schema["properties"]["retention"]["properties"][
            "terminal_run_statuses"
        ]
        self.assertEqual(statuses["maxItems"], 4)
        self.assertEqual(statuses["prefixItems"][-1]["const"], "interrupted")

    def test_readme_roadmap_and_operator_commands_record_loop_49_without_overclaim(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        harness = (ROOT / "HARNESS.md").read_text(encoding="utf-8")

        self.assertIn("Delivery Loops 1-93 are complete", readme)
        self.assertIn("Loop 49", readme)
        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("- Completed delivery loops: 1-93", roadmap)
        self.assertIn("Loop 49: Interrupted Run Recovery", roadmap)
        self.assertIn("Current maturity remains Self-hosted Beta", roadmap)
        command = "python3 scripts/interrupted_recovery_smoke.py"
        self.assertIn(command, agents)
        self.assertIn(command, harness)
