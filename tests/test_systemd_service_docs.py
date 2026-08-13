from pathlib import Path
from unittest import TestCase


class SystemdServiceDocumentationTests(TestCase):
    def test_operator_guide_defines_a_manual_hardened_supervisor_boundary(self):
        root = Path(__file__).resolve().parents[1]
        guide = (root / "docs" / "systemd-service.md").read_text(encoding="utf-8")
        normalized = " ".join(guide.split())

        self.assertIn("# Linux systemd Supervision", guide)
        self.assertIn("skill2workflow systemd-unit", guide)
        self.assertIn("systemd-analyze verify", guide)
        self.assertIn("systemctl enable --now", guide)
        self.assertIn("journalctl", guide)
        self.assertIn("host-local operational output", guide)
        self.assertIn("SendSIGKILL=no", guide)
        self.assertIn("ReadWritePaths", guide)
        self.assertIn("64 KiB", guide)
        self.assertIn("does not escalate to `SIGKILL`", guide)
        self.assertIn("does not provide system account provisioning", normalized)
        self.assertIn("scripts/systemd_service_smoke.py", guide)

    def test_public_docs_and_roadmap_record_loop_56_without_overclaiming(self):
        root = Path(__file__).resolve().parents[1]
        roadmap = (root / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")
        guide = (root / "docs" / "systemd-service.md").read_text(encoding="utf-8")
        normalized = " ".join(guide.split())

        self.assertIn("Loop 56: Linux systemd Supervision", roadmap)
        self.assertIn("systemd", roadmap)
        self.assertIn("systemd", readme)
        self.assertIn("Self-hosted Beta", readme)
        self.assertNotIn("hosted control plane", guide)
        self.assertIn("does not provide", normalized)
