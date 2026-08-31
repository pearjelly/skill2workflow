from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ServiceBootstrapDocumentationTests(TestCase):
    def test_bootstrap_guide_documents_safe_first_run_and_boundaries(self):
        guide = (ROOT / "docs" / "service-bootstrap.md").read_text(encoding="utf-8")
        service = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")

        self.assertIn("# Secure Service Bootstrap", guide)
        self.assertIn("skill2workflow service-init", guide)
        self.assertIn("0700", guide)
        self.assertIn("0600", guide)
        self.assertIn("never prints", guide)
        self.assertIn("must not already exist", guide)
        self.assertIn("external TLS", guide)
        self.assertIn("not included in state backups", guide)
        self.assertIn("scripts/service_bootstrap_smoke.py", guide)
        self.assertIn("service-token-rotation.md", guide)
        self.assertIn("--http-allowed-origin", guide)
        self.assertIn("service-bootstrap.md", service)

    def test_roadmap_and_readme_record_completed_loop_51_without_maturity_inflation(self):
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        harness = (ROOT / "HARNESS.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("- Completed delivery loops: 1-258", roadmap)
        self.assertIn(
            "- Active loop: None; Loop 258 is complete with live CAS action conflict recovery",
            roadmap,
        )
        self.assertIn("| Loop 51: Secure Service Bootstrap | Complete |", roadmap)
        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("Delivery Loops 1-258 are complete", readme)
        self.assertIn("secure service bootstrap", readme)
        self.assertIn("scripts/service_bootstrap_smoke.py", harness)
        self.assertIn("Secure service bootstrap", agents)

    def test_wheel_contract_includes_service_init(self):
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('"service-init"', package_smoke)
        self.assertIn("initialize_service_workspace", package_smoke)

    def test_token_rotation_guide_and_cli_preserve_local_secret_boundary(self):
        guide = (ROOT / "docs" / "service-token-rotation.md").read_text(
            encoding="utf-8"
        )
        service = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("service-token-rotate", guide)
        self.assertIn("atomic", guide)
        self.assertIn("never", guide)
        self.assertIn("service-token-rotation.md", service)
        self.assertIn('"service-token-rotate"', package_smoke)
