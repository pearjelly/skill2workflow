import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ServiceProbeDocumentationTests(TestCase):
    def test_service_probe_guide_and_schema_define_the_same_boundary(self):
        guide = (ROOT / "docs" / "service-probe.md").read_text(encoding="utf-8")
        schema = json.loads(
            (ROOT / "schemas" / "service-probe-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn("skill2workflow service-probe", guide)
        self.assertIn("/healthz", guide)
        self.assertIn("/readyz", guide)
        self.assertIn("8 KiB", guide)
        self.assertIn("five-second timeout", guide)
        self.assertIn("skill2workflow service-wait", guide)
        self.assertIn("bounded", guide)
        self.assertIn("polls", guide)
        self.assertIn("does not add an HTTP route", guide)
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-service-probe-0.1.0",
        )
        self.assertEqual(
            schema["properties"]["status"]["enum"],
            ["ready", "not_ready", "unavailable"],
        )
        self.assertIn("health", schema["required"])
        self.assertIn("readiness", schema["required"])

    def test_public_docs_link_the_probe_and_roadmap_records_loop_95(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        service = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("docs/service-probe.md", readme)
        self.assertIn("service-wait", readme)
        self.assertIn("service-probe", service)
        self.assertIn("Loop 95: Deployment Service Probe", roadmap)
        self.assertIn("Loops 44-222 complete", roadmap)
