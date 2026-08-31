from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class GoLiveDocumentationTests(TestCase):
    def test_go_live_checklist_links_existing_safe_operator_controls(self):
        guide = (ROOT / "docs" / "go-live.md").read_text(encoding="utf-8")
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("# Single-Instance Go-Live Checklist", guide)
        self.assertIn("skill2workflow service-init", guide)
        self.assertIn("skill2workflow service-doctor", guide)
        self.assertIn("skill2workflow service-go-live-check", guide)
        self.assertIn("skill2workflow systemd-unit", guide)
        self.assertIn("skill2workflow service-probe", guide)
        self.assertIn("skill2workflow service-operational-readiness", guide)
        self.assertIn("does not prove provider availability", guide)
        self.assertIn("never retries a write automatically", guide)
        self.assertIn("running_service", guide)
        self.assertIn("claim multi-tenant RBAC", guide)
        self.assertIn("[Go-live checklist](go-live.md)", index)
        self.assertIn("[go-live checklist](docs/go-live.md)", readme)
        self.assertIn("Added `service-go-live-check`", changelog)
