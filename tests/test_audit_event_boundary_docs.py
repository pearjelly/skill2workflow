from pathlib import Path
from tests.documentation_fixtures import assert_guide_reachable
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class AuditEventBoundaryDocsTests(TestCase):
    def test_guide_states_shared_event_write_and_decode_boundary(self):
        guide = (ROOT / "docs" / "audit-event-boundary.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("1 MiB", guide)
        self.assertIn("Every audit append", guide)
        self.assertIn("JSONL reads", guide)
        self.assertIn("SQLite reads", guide)
        self.assertIn("partial logical emission", guide)

    def test_public_docs_link_the_boundary(self):
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert_guide_reachable(self, 'docs/audit-event-boundary.md')
        for document in (stability, roadmap):
            self.assertIn("audit-event-boundary.md", document)

    def test_roadmap_and_readme_promote_loop_175(self):
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Completed delivery loops: 1-285", roadmap)
        self.assertIn(
            "Loop 285 is complete with reader-focused documentation entrypoints", roadmap
        )
        self.assertIn("Delivery Loops 1-285 are complete", readme)
