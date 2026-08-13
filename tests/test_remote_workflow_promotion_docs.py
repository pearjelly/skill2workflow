from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RemoteWorkflowPromotionDocumentationTests(TestCase):
    def test_remote_promotion_contract_is_published_across_project_surfaces(self):
        guide = (ROOT / "docs" / "remote-workflow-promotion.md").read_text(
            encoding="utf-8"
        )
        service_guide = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("Loop 87", guide)
        self.assertIn("service-workflow-promote", guide)
        self.assertIn("POST /api/v1/workflow-promotions", guide)
        self.assertIn("expected_current_version", guide)
        self.assertIn("1 MiB", guide)
        self.assertIn("409", guide)
        self.assertIn("skill2workflow-workflow-promotion-0.1.0", guide)
        self.assertIn("remote-workflow-promotion.md", service_guide)
        self.assertIn("workflow-promotions", stability)
        self.assertIn("Loop 87 adds", readme)
        self.assertIn("workflow-promotions", changelog)
        self.assertIn('"service-workflow-promote"', package_smoke)
        self.assertIn("Loop 87", roadmap)
