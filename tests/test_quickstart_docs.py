from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class InstalledQuickstartDocumentationTests(TestCase):
    def test_guide_documents_the_complete_installed_controlled_journey(self):
        guide = (ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")

        self.assertIn("# Installed Controlled Quickstart", guide)
        self.assertIn("skill2workflow quickstart", guide)
        self.assertIn("ready_for_review", guide)
        self.assertIn("resume-published", guide)
        self.assertIn("skill2workflow service", guide)
        self.assertIn("human gate", guide)
        self.assertIn("must not already exist", guide)
        self.assertIn("does not call an external connector", guide)
        self.assertIn("scripts/quickstart_smoke.py", guide)

    def test_readme_leads_with_installed_quickstart_and_preserves_source_demo(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        quickstart = readme.index("skill2workflow quickstart")
        source_demo = readme.index("scripts/demo_bootstrap.py")

        self.assertLess(quickstart, source_demo)
        self.assertIn("Installed wheel quickstart", readme)
        self.assertIn("Source-checkout contributor demo", readme)
        self.assertIn("Delivery Loops 1-92 are complete", readme)
        self.assertIn("installed controlled quickstart", readme)

    def test_roadmap_and_harness_record_completed_loop_52(self):
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        harness = (ROOT / "HARNESS.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("- Completed delivery loops: 1-92", roadmap)
        self.assertIn(
            "- Active loop: None; Loop 92 is complete with policy-bound remote retention readiness",
            roadmap,
        )
        self.assertIn("| Loop 52: Installed Controlled Quickstart | Complete |", roadmap)
        self.assertIn("scripts/quickstart_smoke.py", harness)
        self.assertIn("Installed controlled quickstart", agents)
