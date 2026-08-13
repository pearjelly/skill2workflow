import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RuntimeInfoDocumentationTests(TestCase):
    def test_runtime_info_contract_is_published_and_bounded(self):
        schema = json.loads(
            (ROOT / "schemas" / "runtime-info-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        guide = (ROOT / "docs" / "remote-runtime-info.md").read_text(
            encoding="utf-8"
        )
        service_guide = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertEqual(
            schema["$id"],
            "https://skill2workflow.dev/schemas/runtime-info-0.1.0.json",
        )
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-runtime-info-0.1.0",
        )
        self.assertIn("GET /api/v1/runtime-info", guide)
        self.assertIn("service-runtime-info", guide)
        self.assertIn("16 KiB", guide)
        self.assertIn("never includes hostnames, ports, filesystem paths", guide)
        self.assertIn("GET /api/v1/runtime-info", service_guide)
        self.assertIn("Loop 84: Remote Runtime Info", roadmap)
        self.assertIn("remote runtime identity", changelog.lower())
