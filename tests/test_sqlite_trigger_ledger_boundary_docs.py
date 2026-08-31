from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class SqliteTriggerLedgerBoundaryDocsTests(TestCase):
    def test_boundary_contract_is_documented_and_indexed(self):
        boundary = (ROOT / "docs" / "sqlite-trigger-ledger-boundary.md").read_text(
            encoding="utf-8"
        )
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("Loop 177", boundary)
        self.assertIn("64 KiB", boundary)
        self.assertIn("response_json", boundary)
        self.assertIn("SQLite trigger-ledger responses use a fixed 64 KiB", stability)
        self.assertIn("sqlite-trigger-ledger-boundary.md", stability)
        self.assertIn("Delivery Loops 1-256 are complete", readme)
        self.assertIn("sqlite-trigger-ledger-boundary.md", readme)
        self.assertIn("Loop 256 is complete with live publication-target review", roadmap)
        self.assertIn("Loop 177: Bounded SQLite Trigger-Ledger Responses", roadmap)
        self.assertIn("sqlite-trigger-ledger-boundary.md", changelog)
