from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class JsonControlIndexDocumentationTests(TestCase):
    def test_boundary_guide_records_the_fixed_contract(self):
        guide = (ROOT / "docs" / "json-control-index-boundary.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "Loop 171",
            "8,388,608 bytes (8 MiB)",
            "regular, non-symlink descriptor",
            "O_NOFOLLOW",
            "device/inode",
            "one byte beyond",
            "JSON-to-SQLite import",
        ):
            self.assertIn(phrase, guide)

    def test_public_docs_link_the_boundary(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("docs/json-control-index-boundary.md", readme)
        self.assertIn("json-control-index-boundary.md", stability)
        self.assertIn("Loop 171: Bounded Local JSON Control Index", roadmap)
