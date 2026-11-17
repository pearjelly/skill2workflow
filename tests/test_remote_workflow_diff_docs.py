from tests.documentation_fixtures import read_api_section
from pathlib import Path
from tests.documentation_fixtures import assert_guide_reachable
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RemoteWorkflowDiffDocumentationTests(TestCase):
    def test_remote_diff_contract_is_published_across_project_surfaces(self):
        guide = read_api_section('remote-workflow-diff')
        service_guide = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        _readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(encoding="utf-8")

        self.assertIn("Loop 88", guide)
        self.assertIn("service-workflow-diff", guide)
        self.assertIn("GET /api/v1/workflow-diffs", guide)
        self.assertIn("64 KiB", guide)
        self.assertIn("skill2workflow-workflow-diff-0.1.0", guide)
        self.assertIn("api-reference.md#remote-workflow-diff", service_guide)
        self.assertIn("workflow-diffs", stability)
        assert_guide_reachable(self, 'docs/api-reference.md#remote-workflow-diff')
        self.assertIn("workflow-diffs", changelog)
        self.assertIn('"service-workflow-diff"', package_smoke)
