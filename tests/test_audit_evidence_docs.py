"""Documentation coverage for the local audit evidence boundary."""

from __future__ import annotations

from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class AuditEvidenceDocumentationTests(TestCase):
    def test_guide_and_public_entry_points_describe_bounded_private_export(self):
        guide = (ROOT / "docs" / "audit-evidence.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        package_smoke = (ROOT / "scripts" / "package_smoke.py").read_text(encoding="utf-8")
        for phrase in (
            "audit-evidence",
            "SQLite",
            "1 through 100",
            "truncated",
            "next_cursor",
            "owner-only",
            "symbolic link",
            "raw provider errors",
            "does not repair",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guide)
        self.assertIn("docs/audit-evidence.md", readme)
        self.assertIn("audit-evidence", stability)
        self.assertIn('"audit-evidence"', package_smoke)
