from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ServiceDoctorDocumentationTests(TestCase):
    def test_operator_guide_defines_read_only_contract_and_fixed_codes(self):
        guide = (ROOT / "docs" / "service-doctor.md").read_text(encoding="utf-8")

        self.assertIn("skill2workflow service-doctor --config", guide)
        self.assertIn("config`, `auth`, `credentials`, `state`, and `bind", guide)
        self.assertIn("never starts the service", guide)
        self.assertIn("does not modify", guide)
        self.assertIn("exit code `0`", guide)
        self.assertIn("exit code `1`", guide)
        self.assertIn("scripts/service_doctor_smoke.py", guide)

    def test_readme_and_roadmap_publish_completed_loop_53(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Delivery Loops 1-150 are complete", readme)
        self.assertIn("service-doctor", readme)
        self.assertIn("docs/service-doctor.md", readme)
        self.assertIn("Completed delivery loops: 1-150", roadmap)
        self.assertIn("Loop 53: Operational Readiness Doctor", roadmap)
        self.assertIn("| Loop 53: Operational Readiness Doctor | Complete |", roadmap)
