from tests.documentation_fixtures import read_api_section
from pathlib import Path
from tests.documentation_fixtures import assert_guide_reachable
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RemoteWorkflowPromotionDocumentationTests(TestCase):
    def test_remote_promotion_contract_is_published_across_project_surfaces(self):
        guide = read_api_section('remote-workflow-promotion')
        service_guide = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs/loops/history.md").read_text(encoding="utf-8")
        _readme = (ROOT / "README.md").read_text(encoding="utf-8")
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
        self.assertIn("api-reference.md#remote-workflow-promotion", service_guide)
        self.assertIn("workflow-promotions", stability)
        assert_guide_reachable(self, 'docs/api-reference.md#remote-workflow-promotion')
        self.assertIn("workflow-promotions", changelog)
        self.assertIn('"service-workflow-promote"', package_smoke)
        self.assertIn("Loop 87", roadmap)
