import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RunDetailDocumentationTests(TestCase):
    def test_schema_and_guide_publish_the_redacted_bounded_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "run-detail-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        guide = (ROOT / "docs" / "run-detail.md").read_text(encoding="utf-8")

        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/run-detail-0.1.0.schema.json",
        )
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-run-detail-0.1.0",
        )
        self.assertEqual(schema["properties"]["events"]["maxItems"], 50)
        self.assertEqual(schema["$defs"]["window"]["properties"]["max_events"]["maximum"], 50)
        for phrase in (
            "GET /runs/{run_id}",
            "latest 50",
            "64 KiB",
            "workflow DSL",
            "trigger context",
            "credential values",
            "raw error strings",
            "does not append audit events",
            "service-show",
            "no-store",
        ):
            self.assertIn(phrase, guide)

    def test_public_docs_cross_link_run_detail_and_installed_command(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        service = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        harness = (ROOT / "HARNESS.md").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(encoding="utf-8")

        self.assertIn("docs/run-detail.md", readme)
        self.assertIn("docs/run-list.md", readme)
        self.assertIn("GET /runs/{run_id}", service)
        self.assertIn("GET /runs", service)
        self.assertIn("service-show", stability)
        self.assertIn("service-runs", stability)
        self.assertIn("service-run-page", harness)
        self.assertIn('"service-show"', package_smoke)
        self.assertIn('"service-runs"', package_smoke)
        self.assertIn("service-run-page", service)
        self.assertIn("service-run-page", stability)
        self.assertIn('"service-run-page"', package_smoke)
        self.assertIn("docs/support-bundle.md", readme)
        self.assertIn("service-support-bundle", stability)
        self.assertIn('"service-support-bundle"', package_smoke)

    def test_run_list_schema_and_guide_publish_discovery_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "run-list-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        guide = (ROOT / "docs" / "run-list.md").read_text(encoding="utf-8")
        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/run-list-0.1.0.schema.json",
        )
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-run-list-0.1.0",
        )
        self.assertEqual(schema["properties"]["runs"]["maxItems"], 100)
        for phrase in (
            "## Local run summaries",
            "runs --state-dir",
            "control-runs --state-dir",
            "--limit 100",
            "1` through `1000",
            "durable update time",
            "filesystem fallback",
            "GET /runs",
            "latest 100",
            "fixed status counts",
            "does not acquire the scheduler lease",
            "does not append audit events",
            "service-runs",
            "service-show",
        ):
            self.assertIn(phrase, guide)

    def test_filtered_paged_run_list_contract_is_published(self):
        schema = json.loads(
            (ROOT / "schemas" / "run-list-0.2.0.schema.json").read_text(encoding="utf-8")
        )
        guide = (ROOT / "docs" / "run-list.md").read_text(encoding="utf-8")
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-run-list-0.2.0",
        )
        self.assertEqual(schema["properties"]["runs"]["maxItems"], 100)
        self.assertIn("GET /api/v1/runs", guide)
        self.assertIn("status=failed", guide)
        self.assertIn("next_cursor", guide)
        self.assertIn("service-run-page", guide)

    def test_support_bundle_schema_and_guide_publish_safe_incident_contract(self):
        schema = json.loads(
            (ROOT / "schemas" / "support-bundle-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        guide = (ROOT / "docs" / "support-bundle.md").read_text(encoding="utf-8")
        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/support-bundle-0.1.0.schema.json",
        )
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-support-bundle-0.1.0",
        )
        self.assertEqual(schema["$defs"]["runList"]["properties"]["runs"]["maxItems"], 100)
        for phrase in (
            "GET /api/v1/support-bundle",
            "128 KiB",
            "does not append audit events",
            "does not acquire the scheduler lease",
            "service-support-bundle",
            "0600",
            "workflow DSL",
            "credential values",
            "does not include",
        ):
            self.assertIn(phrase, guide)
