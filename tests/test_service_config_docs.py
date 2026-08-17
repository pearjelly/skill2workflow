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
        ):
            self.assertIn(phrase, guide)
