import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class WorkflowReleaseDocumentationTests(TestCase):
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
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("# Reviewable Workflow Releases", guide)
        self.assertIn("workflow-diff", guide)
        self.assertIn("expected-current-version", guide)
        self.assertIn("without copying", guide)
        self.assertIn("workflow alias precondition failed", guide)
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
        self.assertIn("--expected-current-version", cli)
        self.assertIn('"workflow-diff"', package_smoke)
        self.assertIn('"workflow-artifacts"', package_smoke)
