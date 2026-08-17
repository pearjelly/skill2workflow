import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class WorkflowExplanationDocumentationTests(TestCase):
    def test_fixed_schema_and_public_surfaces_are_linked(self):
        schema = json.loads(
            (ROOT / "schemas" / "workflow-explanation-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        guide = (ROOT / "docs" / "workflow-explanation.md").read_text(encoding="utf-8")
        service = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cli = (ROOT / "src" / "skill2workflow" / "cli.py").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(encoding="utf-8")

        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/workflow-explanation-0.1.0.json",
        )
        for content in (guide, service, stability, readme):
            self.assertIn("skill2workflow-workflow-explanation-0.1.0", content)
        self.assertIn("GET /api/v1/workflow-explanations", service)
        self.assertIn("service-workflow-explain", guide)
        self.assertIn('"service-workflow-explain"', cli)
        self.assertIn('"service-workflow-explain"', package_smoke)
