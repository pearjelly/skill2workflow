import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RecurringScheduleDocumentationTests(TestCase):
    def test_recurring_schedule_schema_matches_runtime_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "recurring-schedule-0.2.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-schedule-0.2.0",
        )
        recurrence = schema["properties"]["schedule"]["properties"]
        trigger = schema["properties"]["trigger"]["properties"]
        self.assertEqual(recurrence["missed_run_policy"]["enum"], ["latest", "skip"])
        self.assertEqual(recurrence["interval_seconds"]["minimum"], 1)
        self.assertEqual(trigger["idempotency_key_prefix"]["pattern"], "^[A-Za-z0-9_.:-]+$")
        self.assertFalse(schema["additionalProperties"])

    def test_operator_guide_defines_delivery_recovery_and_lease_semantics(self):
        guide = (ROOT / "docs" / "recurring-scheduling.md").read_text(encoding="utf-8")

        self.assertIn("skill2workflow-schedule-0.2.0", guide)
        self.assertIn("missed_run_policy", guide)
        self.assertIn("`latest`", guide)
        self.assertIn("`skip`", guide)
        self.assertIn("claim-before-execute", guide)
        self.assertIn("`uncertain`", guide)
        self.assertIn("schedule-dispatches", guide)
        self.assertIn("schedule-disable", guide)
        self.assertIn("SQLite lease", guide)
        self.assertIn("standby", guide)
        self.assertIn("not exactly-once", guide)
        self.assertIn("capped at 1 MiB", guide)
        self.assertIn("recurring_scheduler_smoke.py", guide)

    def test_readme_and_roadmap_advance_only_after_all_beta_loops(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("Delivery Loops 1-99 are complete", readme)
        self.assertIn("docs/recurring-scheduling.md", readme)
        self.assertIn("- Current maturity: Self-hosted Beta", roadmap)
        self.assertIn("| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Complete |", roadmap)
