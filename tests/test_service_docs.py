from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ServiceDocumentationTests(TestCase):
    def test_service_guide_documents_config_lifecycle_and_security_boundary(self):
        guide = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")

        self.assertIn("skill2workflow-service-0.2.0", guide)
        self.assertIn("skill2workflow service --config", guide)
        self.assertIn("GET /healthz", guide)
        self.assertIn("GET /readyz", guide)
        self.assertIn("SIGTERM", guide)
        self.assertIn("SQLite", guide)
        self.assertIn("loopback", guide)
        self.assertIn("Bearer authentication", guide)
        self.assertIn("MAX_CONCURRENT_BUSINESS_REQUESTS", guide)
        self.assertIn("Retry-After: 1", guide)
        self.assertIn("service concurrency limit reached", guide)
        self.assertIn("service_boundary_smoke.py", guide)
        self.assertIn("GET /api/v1/recurring-schedules", guide)
        self.assertIn("remote-schedule-inventory.md", guide)

    def test_readme_points_to_service_entry_point_and_completed_beta_gate(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("Delivery Loops 1-78 are complete", readme)
        self.assertIn("docs/service.md", readme)
        self.assertIn("Current maturity: Self-hosted Beta", readme)
