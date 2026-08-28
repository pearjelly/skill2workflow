import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class CancellationDocumentationTests(TestCase):
    def test_operator_guide_defines_cooperative_idempotent_boundary(self):
        guide = (ROOT / "docs/cancellation.md").read_text(encoding="utf-8")

        for phrase in (
            "cancel-run",
            "POST /runs/{run_id}/cancel",
            "cancel_requested",
            "cancelled",
            "idempotent",
            "waiting",
            "retry",
            "external request",
            "does not interrupt",
            "run_cancellations",
            "backup",
            "retention",
            "failure window",
            "service-audit-consistency",
            "missing bounded",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guide)

    def test_v2_retention_schema_has_fixed_cancelled_terminal_status(self):
        schema = json.loads(
            (ROOT / "schemas/retention-policy-0.2.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        statuses = schema["properties"]["retention"]["properties"][
            "terminal_run_statuses"
        ]
        self.assertEqual(
            [item["const"] for item in statuses["prefixItems"]],
            ["completed", "failed", "cancelled"],
        )
        self.assertEqual(statuses["minItems"], 3)
        self.assertEqual(statuses["maxItems"], 3)

    def test_public_docs_record_loop_48_without_claiming_forceful_abort(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        service = (ROOT / "docs/service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs/stability.md").read_text(encoding="utf-8")

        self.assertIn("Delivery Loops 1-230 are complete", readme)
        self.assertIn("Loop 48", readme)
        self.assertIn("- Completed delivery loops: 1-230", roadmap)
        self.assertIn("Loop 48: Durable Cooperative Run Cancellation", roadmap)
        self.assertIn("Current maturity remains Self-hosted Beta", roadmap)
        self.assertIn("/runs/{run_id}/cancel", service)
        self.assertIn("cooperative", service)
        self.assertIn("retention-policy-0.2.0", stability)

    def test_public_docs_record_cross_database_retry_reconciliation(self):
        approval = (ROOT / "docs" / "human-approval.md").read_text(encoding="utf-8")
        schedule = (ROOT / "docs" / "remote-schedule-actions.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("repairs only missing bounded audit evidence", approval)
        self.assertIn("changed: false", schedule)
        self.assertIn("scheduler commit succeeds", schedule)
