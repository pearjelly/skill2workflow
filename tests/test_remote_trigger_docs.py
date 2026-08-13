from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RemoteTriggerDocumentationTests(TestCase):
    def test_remote_trigger_contract_is_published(self):
        guide = (ROOT / "docs" / "remote-trigger.md").read_text(encoding="utf-8")
        service_guide = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("service-trigger", guide)
        self.assertIn("--idempotency-key", guide)
        self.assertIn("POST /webhooks/<workflow_id>/<version-or-alias>", guide)
        self.assertIn("1 MiB", guide)
        self.assertIn("409", guide)
        self.assertIn("remote-trigger.md", service_guide)
        self.assertIn("service-trigger", stability)
        self.assertIn("Loop 85: Protected Remote Workflow Triggering", roadmap)
        self.assertIn("Delivery Loops 1-107 are complete", readme)
        self.assertIn("service-trigger", changelog.lower())
        self.assertIn('"service-trigger"', package_smoke)
