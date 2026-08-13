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
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(encoding="utf-8")

        self.assertIn("docs/run-detail.md", readme)
        self.assertIn("GET /runs/{run_id}", service)
        self.assertIn("service-show", stability)
        self.assertIn('"service-show"', package_smoke)
