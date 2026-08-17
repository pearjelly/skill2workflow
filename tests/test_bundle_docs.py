import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class WorkflowBundleDocumentationTests(TestCase):
    def test_bundle_guide_and_manifest_contract_are_present(self):
        guide = (ROOT / "docs" / "workflow-bundles.md").read_text(encoding="utf-8")
        schema = json.loads(
            (ROOT / "schemas" / "workflow-bundle-0.1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )

        for phrase in (
            "bundle-create",
            "bundle-verify",
            "deterministic ZIP",
            "never contains",
            "8 MiB",
            "2 MiB",
            "does not add remote upload",
        ):
            self.assertIn(phrase, guide)
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "skill2workflow-workflow-bundle-0.1.0",
        )
        self.assertFalse(schema["additionalProperties"])

    def test_docs_index_surfaces_the_product_entry_paths(self):
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        for link in (
            "quickstart.md",
            "authoring.md",
            "workflow-dsl-contract.md",
            "workflow-bundles.md",
            "service.md",
            "security-boundary.md",
        ):
            self.assertIn(link, index)
