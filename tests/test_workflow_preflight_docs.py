import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class WorkflowPreflightDocumentationTests(TestCase):
    def test_fixed_schema_and_public_surfaces_are_linked(self):
        schema = json.loads(
            (ROOT / "schemas" / "workflow-preflight-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        guide = (ROOT / "docs" / "workflow-preflight.md").read_text(encoding="utf-8")
        service = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cli = (ROOT / "src" / "skill2workflow" / "cli.py").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(encoding="utf-8")

        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/workflow-preflight-0.1.0.schema.json",
        )
        for content in (guide, service, stability, readme):
            self.assertIn("skill2workflow-workflow-preflight-0.1.0", content)
        self.assertIn("POST /api/v1/workflow-preflights", service)
        self.assertIn("service-workflow-preflight", guide)
        self.assertIn('"service-workflow-preflight"', cli)
        self.assertIn('"service-workflow-preflight"', package_smoke)
