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
        self.assertIn("--limit 100", guide)
        self.assertIn("--max-items", guide)
        self.assertIn("1` through `100", guide)
        self.assertIn("skill2workflow-local-schedule-list-0.1.0", guide)
        self.assertIn("skill2workflow-local-schedule-dispatch-list-0.1.0", guide)
        self.assertIn("trigger inputs", guide)
        self.assertIn("claim-expiry", guide)
        self.assertIn("SQLite cursor", guide)
        self.assertIn("unbounded source read", guide)

    def test_bounded_local_schedule_schemas_fix_the_redacted_window_contract(self):
        schedule_schema = json.loads(
            (ROOT / "schemas" / "local-schedule-list-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        dispatch_schema = json.loads(
            (ROOT / "schemas" / "local-schedule-dispatch-list-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schedule_schema["properties"]["schema_version"]["const"],
            "skill2workflow-local-schedule-list-0.1.0",
        )
        self.assertEqual(
            dispatch_schema["properties"]["schema_version"]["const"],
            "skill2workflow-local-schedule-dispatch-list-0.1.0",
        )
        self.assertEqual(
            schedule_schema["$defs"]["window"]["properties"]["max_items"]["maximum"],
            1000,
        )
        self.assertEqual(
            dispatch_schema["$defs"]["window"]["properties"]["max_items"]["minimum"],
            1,
        )
        self.assertNotIn(
            "trigger", schedule_schema["$defs"]["schedule"]["properties"]
        )
        self.assertNotIn(
            "owner_id", dispatch_schema["$defs"]["dispatch"]["properties"]
        )
        self.assertFalse(schedule_schema["additionalProperties"])
        self.assertFalse(dispatch_schema["additionalProperties"])

    def test_readme_and_roadmap_advance_only_after_all_beta_loops(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("Delivery Loops 1-142 are complete", readme)
        self.assertIn("docs/recurring-scheduling.md", readme)
        self.assertIn("- Current maturity: Self-hosted Beta", roadmap)
        self.assertIn("| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Complete |", roadmap)
