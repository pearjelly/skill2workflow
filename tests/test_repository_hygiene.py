from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RepositoryHygieneContractTests(TestCase):
    def test_local_private_artifacts_are_ignored_at_the_repository_root(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        for pattern in (
            "/*-auth.png",
            "/*-authorization.png",
            "/credentials.json",
            "/*.sqlite",
            "/*.sqlite3",
            "/*.jsonl",
            "/*.pem",
            "/*.key",
            "/private/",
            "/secrets/",
        ):
            self.assertIn(pattern, ignore)

    def test_contributor_docs_require_repository_wide_hygiene_scan(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        credential_boundary = (
            ROOT / "docs" / "credential-boundary.md"
        ).read_text(encoding="utf-8")

        command = "python3 scripts/secret_hygiene.py --repository-root ."
        self.assertIn(command, contributing)
        self.assertIn(command, credential_boundary)
        normalized = " ".join(credential_boundary.split())
        self.assertIn("does not read rejected binary artifacts", normalized)
        self.assertIn("never reports a suspected secret prefix", normalized)
