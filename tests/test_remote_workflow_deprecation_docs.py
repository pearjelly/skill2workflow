from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RemoteWorkflowDeprecationDocumentationTests(TestCase):
    def test_remote_deprecation_contract_is_published_across_project_surfaces(self):
        guide = (ROOT / "docs" / "remote-workflow-deprecation.md").read_text(
            encoding="utf-8"
        )
        service_guide = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        observability = (ROOT / "docs" / "observability.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("Loop 90", guide)
        self.assertIn("service-workflow-deprecate", guide)
        self.assertIn("POST /api/v1/workflow-deprecations", guide)
        self.assertIn("1 MiB", guide)
        self.assertIn("deprecated", guide)
        self.assertIn("workflow_deprecated", guide)
        self.assertIn("skill2workflow-workflow-deprecation-0.1.0", guide)
        self.assertIn("remote-workflow-deprecation.md", service_guide)
        self.assertIn("workflow-deprecations", stability)
        self.assertIn("workflow_deprecation", observability)
        self.assertIn("Loop 90 adds", readme)
        self.assertIn("workflow-deprecations", changelog)
        self.assertIn('"service-workflow-deprecate"', package_smoke)
        self.assertIn("Loop 90", roadmap)
