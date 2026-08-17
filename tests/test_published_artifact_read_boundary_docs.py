from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class PublishedArtifactReadBoundaryDocumentationTests(TestCase):
    def test_boundary_guide_records_the_fixed_contract(self):
        guide = (ROOT / "docs" / "published-artifact-read-boundary.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "Loop 172",
            "2,097,152-byte (2 MiB)",
            "regular non-symlink file",
            "O_NOFOLLOW",
            "device/inode",
            "one byte beyond",
            "SQLite backup",
        ):
            self.assertIn(phrase, guide)

    def test_public_docs_link_the_boundary(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("docs/published-artifact-read-boundary.md", readme)
        self.assertIn("published-artifact-read-boundary.md", stability)
        self.assertIn("Loop 172: Bounded Published Workflow Artifact Reads", roadmap)
        self.assertIn("immutable Workflow artifact publication and reads", changelog)
