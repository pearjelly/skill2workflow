from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class InstalledUiDocumentationTests(TestCase):
    def test_installed_ui_contract_is_published(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "installed-ui.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("skill2workflow ui --port 4173", readme)
        self.assertIn("docs/installed-ui.md", readme)
        self.assertIn("loopback-only", docs)
        self.assertIn("does not read runtime state", docs)
        self.assertIn("--service-url", docs)
        self.assertIn("--auth-token-file", docs)
        self.assertIn("Load Live Snapshot", docs)
        self.assertIn("same-origin `/api/v1/control-snapshot`", docs)
        self.assertIn("/api/v1/service-probe", docs)
        self.assertIn("static mode", docs)
        self.assertIn("not ready", docs)
        self.assertIn("Download Support Bundle", docs)
        self.assertIn("/api/v1/support-bundle", docs)
        self.assertIn("Installed UI", guide)
        self.assertIn('"share/skill2workflow/web"', pyproject)
        self.assertIn("Loop 206: Installed Static UI Launcher", roadmap)
        self.assertIn("Loop 207: Authenticated Live Control-Plane UI", roadmap)
        self.assertIn("Loop 208: Live Service Readiness Badge", roadmap)
        self.assertIn("Loop 209: Bounded Live Snapshot Refresh", roadmap)
        self.assertIn("Loop 210: Protected Live Support-Bundle Download", roadmap)
        self.assertIn("Loop 211: Confirmation-Protected Live Human-Gate Action", roadmap)
