from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class CliInputDocumentationTests(TestCase):
    def test_cli_json_input_boundary_documents_the_fixed_contract(self):
        guide = (ROOT / "docs" / "cli-input-boundary.md").read_text(encoding="utf-8")

        for phrase in (
            "8,388,608",
            "8 MiB",
            "grows between",
            "canonical 1 MiB",
            "2 MiB persisted-document",
            "exit status `1`",
        ):
            self.assertIn(phrase, guide)
