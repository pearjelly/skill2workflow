from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ExternalConnectorResultBoundaryDocsTests(TestCase):
    def test_boundary_guide_and_connector_contract_are_linked(self):
        guide = (ROOT / "docs" / "external-connector-result-boundary.md").read_text(
            encoding="utf-8"
        )
        connectors = (ROOT / "docs" / "connectors.md").read_text(encoding="utf-8")
        for phrase in (
            "1 MiB",
            "allow_nan=false",
            "ConnectorExecutionError",
            "durable run state",
        ):
            self.assertIn(phrase, guide)
        self.assertIn("external-connector-result-boundary.md", connectors)
        self.assertIn("normalized result envelope is bounded to 1 MiB", connectors)
