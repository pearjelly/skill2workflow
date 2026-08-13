from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RemoteWorkflowReleaseDocumentationTests(TestCase):
    def test_remote_publication_contract_is_published_across_project_surfaces(self):
        guide = (ROOT / "docs" / "remote-workflow-release.md").read_text(
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

        self.assertIn("Loop 86", guide)
        self.assertIn("service-workflow-publish", guide)
        self.assertIn("POST /api/v1/workflow-releases", guide)
        self.assertIn('"workflow": <Workflow DSL object>', guide)
        self.assertIn("1 MiB", guide)
        self.assertIn("409", guide)
        self.assertIn("skill2workflow-workflow-release-0.1.0", guide)
        self.assertIn("remote-workflow-release.md", service_guide)
        self.assertIn("workflow-releases", stability)
        self.assertIn("Loop 86: Protected Remote Workflow Publication", roadmap)
        self.assertIn("Loop 86 adds", readme)
        self.assertIn("workflow-releases", changelog)
        self.assertIn('"service-workflow-publish"', package_smoke)
