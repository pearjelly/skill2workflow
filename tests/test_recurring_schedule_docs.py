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
        self.assertIn("recurring_schedule_summaries", guide)
        self.assertIn("does not parse complete definitions", guide)
        self.assertIn("PUT /api/v1/recurring-schedules/{schedule_id}", guide)
        self.assertIn("compare-and-swap token", guide)
        self.assertIn("fixed 2 MiB UTF-8 envelope", guide)

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
        self.assertIn("Delivery Loops 1-191 are complete", readme)
        self.assertIn("Loop 165 adds a fixed 2 MiB UTF-8 document bound", readme)
        self.assertIn("Loop 146 adds a compact SQLite recurring-schedule projection", readme)
        self.assertIn("docs/recurring-scheduling.md", readme)
        self.assertIn("- Current maturity: Self-hosted Beta", roadmap)
        self.assertIn("### Loop 146: Compact SQLite Recurring-Schedule Projections", roadmap)
        create_schema = json.loads(
            (ROOT / "schemas" / "recurring-schedule-create-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        create_guide = (ROOT / "docs" / "remote-schedule-create.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            create_schema["properties"]["schema_version"]["const"],
            "skill2workflow-recurring-schedule-create-0.1.0",
        )
        self.assertFalse(create_schema["additionalProperties"])
        self.assertIn("POST /api/v1/recurring-schedules", create_guide)
        self.assertIn("created: false", create_guide)
        self.assertIn("BEGIN IMMEDIATE", create_guide)
        self.assertIn("16 KiB", create_guide)
        self.assertIn("trigger input", create_guide)
        self.assertIn("changed definition", create_guide)
        self.assertIn("### Loop 154: Protected Remote Recurring-Schedule Creation", roadmap)
        self.assertIn("### Loop 155: Protected Remote Recurring-Schedule Updates", roadmap)
        self.assertIn("### Loop 156: Protected Remote Recurring-Schedule Retirement", roadmap)
        self.assertIn("### Loop 157: CAS-Protected Remote Recurring-Schedule State Actions", roadmap)
        self.assertIn("### Loop 158: Safe Remote Recurring-Schedule Patches", roadmap)
        update_schema = json.loads(
            (ROOT / "schemas" / "recurring-schedule-update-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        update_guide = (ROOT / "docs" / "remote-schedule-update.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            update_schema["properties"]["schema_version"]["const"],
            "skill2workflow-recurring-schedule-update-0.1.0",
        )
        self.assertFalse(update_schema["additionalProperties"])
        self.assertIn("PUT /api/v1/recurring-schedules/{schedule_id}", update_guide)
        self.assertIn("expected_next_run_at", update_guide)
        self.assertIn("preserve durable dispatch progress", update_guide)
        delete_schema = json.loads(
            (ROOT / "schemas" / "recurring-schedule-delete-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        delete_guide = (ROOT / "docs" / "remote-schedule-delete.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            delete_schema["properties"]["schema_version"]["const"],
            "skill2workflow-recurring-schedule-delete-0.1.0",
        )
        self.assertFalse(delete_schema["additionalProperties"])
        self.assertIn("DELETE /api/v1/recurring-schedules/{schedule_id}", delete_guide)
        self.assertIn("tombstone", delete_guide)
        self.assertIn("active claim", delete_guide)
        action_guide = (ROOT / "docs" / "remote-schedule-actions.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("expected_next_run_at", action_guide)
        self.assertIn("precondition failed", action_guide)
        self.assertIn("legacy empty JSON object", action_guide)
        patch_schema = json.loads(
            (ROOT / "schemas" / "recurring-schedule-patch-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        patch_guide = (ROOT / "docs" / "remote-schedule-patch.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            patch_schema["properties"]["schema_version"]["const"],
            "skill2workflow-recurring-schedule-patch-0.1.0",
        )
        self.assertFalse(patch_schema["additionalProperties"])
        self.assertIn("PATCH /api/v1/recurring-schedules/{schedule_id}", patch_guide)
        self.assertIn("trigger input", patch_guide)
        self.assertIn("safe fields", patch_guide)
        self.assertIn("service-recurring-schedule-patch", patch_guide)
        self.assertIn("| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Complete |", roadmap)
