from pathlib import Path
from unittest import TestCase


class ChangelogContractTests(TestCase):
    def test_changelog_records_unreleased_product_and_safety_scope(self):
        changelog = (
            Path(__file__).resolve().parents[1] / "CHANGELOG.md"
        ).read_text(encoding="utf-8")

        self.assertTrue(changelog.startswith("# Changelog\n"))
        self.assertLess(
            changelog.index("## [Unreleased]"),
            changelog.index("## [0.1.0] - 2026-07-03"),
        )
        for capability in (
            "authenticated self-hosted runtime service",
            "durable recurring scheduling",
            "backup and restore",
            "state upgrade",
            "runtime observability",
            "data retention",
            "cooperative cancellation",
            "interrupted-run recovery",
            "secure service bootstrap",
            "installed controlled quickstart",
            "descriptor-bound connector credential reads",
            "backup expiration planning",
        ):
            self.assertIn(capability, changelog)

        self.assertIn("Self-hosted Beta", changelog)
        self.assertIn("Workflow DSL `0.1.0`", changelog)
        self.assertIn("does not provide exactly-once execution", changelog)
        self.assertIn("external TLS termination", changelog)
        self.assertIn("cross-database operator-action reconciliation", changelog)
        self.assertIn(
            "[Unreleased]: https://github.com/pearjelly/skill2workflow/compare/v0.1.0...HEAD",
            changelog,
        )
        self.assertIn(
            "[0.1.0]: https://github.com/pearjelly/skill2workflow/releases/tag/v0.1.0",
            changelog,
        )

    def test_release_process_and_contributor_guide_require_changelog_updates(self):
        root = Path(__file__).resolve().parents[1]
        release_process = (root / "docs" / "release-process.md").read_text(
            encoding="utf-8"
        )
        contributing = (root / "CONTRIBUTING.md").read_text(encoding="utf-8")

        self.assertIn("CHANGELOG.md", release_process)
        self.assertIn("target version heading", release_process)
        self.assertIn("CHANGELOG.md", contributing)
        self.assertIn("user-visible", contributing)
