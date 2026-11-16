from tests.documentation_fixtures import read_api_section
from pathlib import Path
from tests.documentation_fixtures import assert_guide_reachable
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RemoteWorkflowInventoryDocumentationTests(TestCase):
    def test_remote_inventory_contract_is_published_across_project_surfaces(self):
        guide = read_api_section('remote-workflow-inventory')
        service_guide = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        observability = (ROOT / "docs" / "observability.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs/loops/history.md").read_text(encoding="utf-8")
        _readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(
            encoding="utf-8"
        )
        schema = (ROOT / "schemas" / "workflow-inventory-0.1.0.schema.json").read_text(
            encoding="utf-8"
        )

        self.assertIn("Loop 91", guide)
        self.assertIn("service-workflows", guide)
        self.assertIn("GET /api/v1/workflows", guide)
        self.assertIn("64 KiB", guide)
        self.assertIn("100", guide)
        self.assertIn("skill2workflow-workflow-inventory-0.1.0", guide)
        self.assertIn("skill2workflow-workflow-inventory-0.1.0", schema)
        self.assertIn("api-reference.md#remote-workflow-inventory", service_guide)
        self.assertIn("workflow-inventory-0.1.0", stability)
        self.assertIn("workflow_inventory", observability)
        assert_guide_reachable(self, 'docs/api-reference.md#remote-workflow-inventory')
        self.assertIn("/api/v1/workflows", changelog)
        self.assertIn('"service-workflows"', package_smoke)
        self.assertIn("Loop 91", roadmap)
