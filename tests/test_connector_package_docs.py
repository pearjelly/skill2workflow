from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ConnectorPackageDocsTests(TestCase):
    def test_loop_34_connector_package_boundary_is_documented(self):
        connectors = _read("docs/connectors.md")
        examples = _read("docs/examples.md")
        compatibility = _read("docs/workflow-dsl-compatibility.md")
        stability = _read("docs/stability.md")

        self.assertIn("## Connector Package Layout", connectors)
        self.assertIn("MANIFEST", connectors)
        self.assertIn("execute(binding, credential_provider=None, context=None)", connectors)
        self.assertIn("load_external_connector(Path(\"examples/connectors/local_echo_connector.py\"))", connectors)
        self.assertIn("Connector package smoke contract", connectors)
        self.assertIn("automatic connector discovery", connectors)

        self.assertIn("### Local Connector Package Shape", examples)
        self.assertIn("examples/connectors/local_echo_connector.py", examples)
        self.assertIn("runtime-generated smoke artifacts", examples)

        self.assertIn("Connector Package Compatibility", compatibility)
        self.assertIn("Workflow DSL `0.1.0` compatibility is separate from connector package conventions", compatibility)
        self.assertIn("connector manifest version", compatibility)

        self.assertIn("explicit local connector fixture loading", stability)
        self.assertIn("automatic connector discovery and product-specific connector packages", stability)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
