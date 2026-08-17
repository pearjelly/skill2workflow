from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class CredentialFileDocumentationTests(TestCase):
    def test_local_credential_file_boundary_documents_the_contract(self):
        guide = (ROOT / "docs" / "credential-file-boundary.md").read_text(
            encoding="utf-8"
        )

        for phrase in (
            "2,097,152",
            "2 MiB",
            "regular, non-symlink",
            "device/inode",
            "growth races",
            "permission-bit requirement",
            "exactly-once provider effects",
        ):
            self.assertIn(phrase, guide)

    def test_public_credential_guides_link_to_the_local_file_boundary(self):
        for relative in ("docs/credential-boundary.md", "docs/connectors.md"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("credential-file-boundary.md", content)
