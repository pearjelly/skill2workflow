import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class WorkflowReleaseDocumentationTests(TestCase):
    def test_local_workflow_inventory_guide_records_bounded_redacted_contract(self):
        guide = (ROOT / "docs" / "local-workflow-inventory.md").read_text(
            encoding="utf-8"
        )
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        cli = (ROOT / "src" / "skill2workflow" / "cli.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("skill2workflow workflows", guide)
        self.assertIn("--limit 100", guide)
        self.assertIn("skill2workflow-workflow-inventory-0.1.0", guide)
        self.assertIn("trigger inputs", guide)
        self.assertIn("complete-list", guide)
        self.assertIn("workflow-content redaction", stability)
        self.assertIn("bounded local published-workflow inventory", changelog)
        self.assertIn('"--limit"', cli)

    def test_artifact_diagnostic_window_is_documented(self):
        guide = (ROOT / "docs" / "workflow-artifacts.md").read_text(
            encoding="utf-8"
        )
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        self.assertIn("fixed issue window", guide)
        self.assertIn("complete issue set", guide)
        self.assertIn("registry rows are streamed", guide)
        self.assertIn("1-256", stability)

    def test_review_contract_and_cas_boundary_are_published(self):
        guide = (ROOT / "docs" / "workflow-releases.md").read_text(encoding="utf-8")
        plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-13-atomic-workflow-alias-promotion.md"
        ).read_text(encoding="utf-8")
        schema = json.loads(
            (ROOT / "schemas" / "workflow-diff-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        artifact_guide = (ROOT / "docs" / "workflow-artifacts.md").read_text(
            encoding="utf-8"
        )
        artifact_schema = json.loads(
            (ROOT / "schemas" / "workflow-artifact-report-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        run_audit_guide = (ROOT / "docs" / "run-audit-consistency.md").read_text(
            encoding="utf-8"
        )
        remote_audit_guide = (ROOT / "docs" / "remote-audit-consistency.md").read_text(
            encoding="utf-8"
        )
        targeted_audit_plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-13-targeted-remote-audit.md"
        ).read_text(encoding="utf-8")
        schedule_plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-13-remote-schedule-inventory.md"
        ).read_text(encoding="utf-8")
        schedule_action_guide = (
            ROOT / "docs" / "remote-schedule-actions.md"
        ).read_text(encoding="utf-8")
        schedule_action_plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-13-remote-schedule-actions.md"
        ).read_text(encoding="utf-8")
        schedule_action_schema = json.loads(
            (
                ROOT
                / "schemas"
                / "recurring-schedule-action-0.1.0.schema.json"
            ).read_text(encoding="utf-8")
        )
        dispatch_guide = (ROOT / "docs" / "remote-schedule-dispatches.md").read_text(
            encoding="utf-8"
        )
        dispatch_plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-13-remote-schedule-dispatches.md"
        ).read_text(encoding="utf-8")
        dispatch_schema = json.loads(
            (
                ROOT
                / "schemas"
                / "recurring-schedule-dispatch-list-0.1.0.schema.json"
            ).read_text(encoding="utf-8")
        )
        artifact_remote_guide = (
            ROOT / "docs" / "remote-workflow-artifacts.md"
        ).read_text(encoding="utf-8")
        artifact_remote_plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-13-remote-workflow-artifacts.md"
        ).read_text(encoding="utf-8")
        backup_readiness_guide = (
            ROOT / "docs" / "remote-backup-readiness.md"
        ).read_text(encoding="utf-8")
        backup_readiness_plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-13-remote-backup-readiness.md"
        ).read_text(encoding="utf-8")
        backup_readiness_schema = json.loads(
            (
                ROOT
                / "schemas"
                / "backup-readiness-0.1.0.schema.json"
            ).read_text(encoding="utf-8")
        )
        run_audit_schema = json.loads(
            (ROOT / "schemas" / "run-audit-report-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        audit_integrity_remote_guide = (
            ROOT / "docs" / "remote-audit-integrity.md"
        ).read_text(encoding="utf-8")
        audit_integrity_remote_plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-13-remote-audit-integrity.md"
        ).read_text(encoding="utf-8")
        runtime_info_guide = (ROOT / "docs" / "remote-runtime-info.md").read_text(
            encoding="utf-8"
        )
        runtime_info_plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-13-remote-runtime-info.md"
        ).read_text(encoding="utf-8")
        runtime_info_schema = json.loads(
            (ROOT / "schemas" / "runtime-info-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("# Reviewable Workflow Releases", guide)
        self.assertIn("workflow-diff", guide)
        self.assertIn("expected-current-version", guide)
        self.assertIn("without copying", guide)
        self.assertIn("workflow alias precondition failed", guide)
        self.assertIn("streams only records belonging to", guide)
        self.assertIn("BEGIN IMMEDIATE", guide)
        self.assertIn("cross-process transaction coordination", guide)
        self.assertIn("## Atomic Publication and Deprecation", guide)
        self.assertIn("publication of the same", guide)
        self.assertIn("Exactly one promotion succeeds", plan)
        self.assertIn("BEGIN IMMEDIATE", plan)
        publication_plan = (
            ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-08-13-atomic-workflow-publication.md"
        ).read_text(encoding="utf-8")
        self.assertIn("matching same-version publication retries idempotent", publication_plan)
        self.assertIn("exclusive immutable", publication_plan)
        self.assertIn("workflow-artifacts", artifact_guide)
        self.assertIn("2 MiB", artifact_guide)
        self.assertIn("known failure", artifact_guide)
        self.assertEqual(
            artifact_schema["$id"],
            "https://skill2workflow.dev/schemas/workflow-artifact-report-0.1.0.json",
        )
        self.assertEqual(
            artifact_schema["properties"]["schema_version"]["const"],
            "skill2workflow-workflow-artifact-report-0.1.0",
        )
        self.assertIn("Loop 74: Workflow Artifact Consistency", roadmap)
        self.assertIn("audit-consistency", run_audit_guide)
        self.assertIn("cross-database", run_audit_guide)
        self.assertIn("waiting` and `interrupted`", run_audit_guide)
        self.assertEqual(
            run_audit_schema["$id"],
            "https://skill2workflow.dev/schemas/run-audit-report-0.1.0.json",
        )
        self.assertEqual(
            run_audit_schema["properties"]["schema_version"]["const"],
            "skill2workflow-run-audit-report-0.1.0",
        )
        self.assertIn("Loop 75: Run Audit Consistency", roadmap)
        self.assertIn("Loop 76: Remote Run Audit Consistency", roadmap)
        self.assertIn("GET /api/v1/audit-consistency", remote_audit_guide)
        self.assertIn("service-audit-consistency", remote_audit_guide)
        self.assertIn("--run-id", remote_audit_guide)
        schedule_guide = (ROOT / "docs" / "remote-schedule-inventory.md").read_text(
            encoding="utf-8"
        )
        schedule_schema = json.loads(
            (ROOT / "schemas" / "recurring-schedule-list-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("service-recurring-schedules", schedule_guide)
        self.assertIn("trigger input", schedule_guide)
        create_guide = (ROOT / "docs" / "remote-schedule-create.md").read_text(
            encoding="utf-8"
        )
        create_schema = json.loads(
            (ROOT / "schemas" / "recurring-schedule-create-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("POST /api/v1/recurring-schedules", create_guide)
        self.assertIn("service-recurring-schedule-add", create_guide)
        self.assertIn("created: false", create_guide)
        self.assertIn("BEGIN IMMEDIATE", create_guide)
        self.assertIn("trigger input", create_guide)
        update_guide = (ROOT / "docs" / "remote-schedule-update.md").read_text(
            encoding="utf-8"
        )
        update_schema = json.loads(
            (ROOT / "schemas" / "recurring-schedule-update-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("PUT /api/v1/recurring-schedules/{schedule_id}", update_guide)
        self.assertIn("expected_next_run_at", update_guide)
        self.assertIn("compare-and-swap", update_guide)
        self.assertEqual(
            update_schema["$id"],
            "https://skill2workflow.dev/schemas/recurring-schedule-update-0.1.0.schema.json",
        )
        self.assertFalse(update_schema["additionalProperties"])
        self.assertEqual(
            create_schema["$id"],
            "https://skill2workflow.dev/schemas/recurring-schedule-create-0.1.0.schema.json",
        )
        self.assertFalse(create_schema["additionalProperties"])
        self.assertEqual(
            schedule_schema["$id"],
            "https://skill2workflow.dev/schemas/recurring-schedule-list-0.1.0.json",
        )
        self.assertEqual(
            schedule_schema["properties"]["schema_version"]["const"],
            "skill2workflow-recurring-schedule-list-0.1.0",
        )
        self.assertIn("one known run", targeted_audit_plan)
        self.assertIn("pre-network rejection", targeted_audit_plan)
        self.assertIn("trigger input", schedule_plan)
        self.assertIn("support-bundle 0.1.0", schedule_plan)
        self.assertIn("Loop 77", roadmap)
        self.assertIn("Loop 78: Remote Recurring-Schedule Inventory", roadmap)
        self.assertIn("POST /api/v1/recurring-schedules/{schedule_id}/disable", schedule_action_guide)
        self.assertIn("service-schedule-enable", schedule_action_guide)
        self.assertIn("BEGIN IMMEDIATE", schedule_action_plan)
        self.assertEqual(
            schedule_action_schema["$id"],
            "https://skill2workflow.dev/schemas/recurring-schedule-action-0.1.0.json",
        )
        self.assertEqual(
            schedule_action_schema["properties"]["schema_version"]["const"],
            "skill2workflow-recurring-schedule-action-0.1.0",
        )
        self.assertIn("Loop 79: Protected Remote Recurring-Schedule Actions", roadmap)
        self.assertIn("GET /api/v1/recurring-schedule-dispatches", dispatch_guide)
        self.assertIn("uncertain", dispatch_guide)
        self.assertIn("64 KiB", dispatch_plan)
        self.assertEqual(
            dispatch_schema["$id"],
            "https://skill2workflow.dev/schemas/recurring-schedule-dispatch-list-0.1.0.json",
        )
        self.assertEqual(
            dispatch_schema["properties"]["schema_version"]["const"],
            "skill2workflow-recurring-schedule-dispatch-list-0.1.0",
        )
        self.assertIn("Loop 80: Remote Recurring-Schedule Dispatch Diagnostics", roadmap)
        self.assertIn("GET /api/v1/workflow-artifacts", artifact_remote_guide)
        self.assertIn("64 KiB", artifact_remote_guide)
        self.assertIn("No artifact repair", artifact_remote_plan)
        self.assertIn("Loop 81: Remote Workflow Artifact Consistency", roadmap)
        self.assertIn("GET /api/v1/backup-readiness", backup_readiness_guide)
        self.assertIn("16 KiB", backup_readiness_guide)
        self.assertIn("active scheduler lease", backup_readiness_plan)
        self.assertEqual(
            backup_readiness_schema["$id"],
            "https://skill2workflow.dev/schemas/backup-readiness-0.1.0.json",
        )
        self.assertEqual(
            backup_readiness_schema["properties"]["schema_version"]["const"],
            "skill2workflow-backup-readiness-0.1.0",
        )
        self.assertIn("Loop 82: Remote Backup Readiness", roadmap)
        self.assertIn("GET /api/v1/audit-integrity", audit_integrity_remote_guide)
        self.assertIn("16 KiB", audit_integrity_remote_guide)
        self.assertIn("event payload", audit_integrity_remote_plan)
        self.assertIn("Loop 83: Remote Audit Integrity", roadmap)
        self.assertIn("GET /api/v1/runtime-info", runtime_info_guide)
        self.assertIn("service-runtime-info", runtime_info_guide)
        self.assertIn("16 KiB", runtime_info_guide)
        self.assertIn("readiness-independent", runtime_info_plan)
        self.assertEqual(
            runtime_info_schema["$id"],
            "https://skill2workflow.dev/schemas/runtime-info-0.1.0.json",
        )
        self.assertEqual(
            runtime_info_schema["properties"]["schema_version"]["const"],
            "skill2workflow-runtime-info-0.1.0",
        )
        self.assertIn("Loop 84: Remote Runtime Info", roadmap)
        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/workflow-diff-0.1.0.json",
        )
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-workflow-diff-0.1.0",
        )
        self.assertIn("Loop 73: Atomic Workflow Registry Mutations", roadmap)
        self.assertIn("workflow-diff", readme)

    def test_cli_registers_review_and_cas_commands(self):
        cli = (ROOT / "src" / "skill2workflow" / "cli.py").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"workflow-diff"', cli)
        self.assertIn('"workflow-artifacts"', cli)
        self.assertIn('"audit-consistency"', cli)
        self.assertIn('"service-audit-consistency"', cli)
        self.assertIn('"service-recurring-schedules"', cli)
        self.assertIn('"service-recurring-schedule-add"', cli)
        self.assertIn('"service-recurring-schedule-update"', cli)
        self.assertIn('"service-recurring-schedule-delete"', cli)
        self.assertIn('"service-recurring-dispatches"', cli)
        self.assertIn('"service-workflow-artifacts"', cli)
        self.assertIn('"service-backup-readiness"', cli)
        self.assertIn('"service-retention-readiness"', cli)
        self.assertIn('"service-operational-readiness"', cli)
        self.assertIn('"service-audit-integrity"', cli)
        self.assertIn('"service-trigger"', cli)
        self.assertIn('"service-runtime-info"', cli)
        self.assertIn('"service-schedule-enable"', cli)
        self.assertIn('"service-schedule-disable"', cli)
        self.assertIn("--expected-current-version", cli)
        self.assertIn('"workflow-diff"', package_smoke)
        self.assertIn('"workflow-artifacts"', package_smoke)
        self.assertIn('"audit-consistency"', package_smoke)
        self.assertIn('"service-audit-consistency"', package_smoke)
        self.assertIn('"service-recurring-schedules"', package_smoke)
        self.assertIn('"service-recurring-schedule-add"', package_smoke)
        self.assertIn('"service-recurring-schedule-update"', package_smoke)
        self.assertIn('"service-recurring-schedule-delete"', package_smoke)
        self.assertIn('"service-recurring-dispatches"', package_smoke)
        self.assertIn('"service-workflow-artifacts"', package_smoke)
        self.assertIn('"service-backup-readiness"', package_smoke)
        self.assertIn('"service-retention-readiness"', package_smoke)
        self.assertIn('"service-operational-readiness"', package_smoke)
        self.assertIn('"service-audit-integrity"', package_smoke)
        self.assertIn('"service-trigger"', package_smoke)
        self.assertIn('"service-runtime-info"', package_smoke)
        self.assertIn('"service-schedule-enable"', package_smoke)
        self.assertIn('"service-schedule-disable"', package_smoke)
