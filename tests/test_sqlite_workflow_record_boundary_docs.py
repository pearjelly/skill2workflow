from pathlib import Path
from tests.documentation_fixtures import assert_guide_reachable
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class SqliteWorkflowRecordBoundaryDocsTests(TestCase):
    def test_boundary_contract_is_documented_and_indexed(self):
        boundary = (ROOT / "docs" / "sqlite-workflow-record-boundary.md").read_text(
            encoding="utf-8"
        )
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("Loop 176", boundary)
        self.assertIn("2 MiB", boundary)
        self.assertIn("record_json", boundary)
        self.assertIn("SQLite workflow registry records use a fixed 2 MiB", stability)
        self.assertIn("sqlite-workflow-record-boundary.md", stability)
        self.assertIn("Delivery Loops 1-284 are complete", readme)
        assert_guide_reachable(self, 'docs/sqlite-workflow-record-boundary.md')
        self.assertIn("Loop 284 is complete with preflight input admission parity", roadmap)
        self.assertIn("Loop 176: Bounded SQLite Workflow Registry Records", roadmap)
        self.assertIn("sqlite-workflow-record-boundary.md", changelog)
