from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class SqliteRunStateBoundaryDocsTests(TestCase):
    def test_guide_states_fixed_write_and_decode_boundary(self):
        guide = (ROOT / "docs" / "sqlite-run-state-boundary.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("8 MiB", guide)
        self.assertIn("Every SQLite run-state insert or update", guide)
        self.assertIn("interrupted-run recovery", guide)
        self.assertIn("startup summary repair", guide)
        self.assertIn("malformed, or non-object documents", guide)

    def test_public_docs_link_the_boundary(self):
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for document in (stability, roadmap, readme):
            self.assertIn("sqlite-run-state-boundary.md", document)

    def test_roadmap_and_readme_promote_loop_174(self):
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Completed delivery loops: 1-232", roadmap)
        self.assertIn("Loop 232 is complete with offline editor assets", roadmap)
        self.assertIn("Delivery Loops 1-232 are complete", readme)
