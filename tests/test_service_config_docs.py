from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ServiceConfigDocumentationTests(TestCase):
    def test_service_config_boundary_documents_the_startup_contract(self):
        guide = (ROOT / "docs" / "service-config-boundary.md").read_text(
            encoding="utf-8"
        )

        for phrase in (
            "65,536",
            "64 KiB",
            "regular,\nnon-symlink",
            "device/inode",
            "growth race",
            "0600",
            "does not provide encrypted configuration",
            "runtime.http_allowed_origins",
            "before credential resolution or network access",
        ):
            self.assertIn(phrase, guide)

    def test_schema_documents_optional_http_origin_upper_bound(self):
        import json

        schema = json.loads(
            (ROOT / "schemas" / "service-config-0.2.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        policy = schema["properties"]["runtime"]["properties"]["http_allowed_origins"]
        self.assertEqual(policy["type"], "array")
        self.assertEqual(policy["maxItems"], 32)
        self.assertTrue(policy["uniqueItems"])
