from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ConnectorPackageDocsTests(TestCase):
    def test_loop_34_connector_package_boundary_is_documented(self):
        connectors = _read("docs/connectors.md")
        examples = _read("docs/examples.md")
        compatibility = _read("docs/workflow-dsl-compatibility.md")
        stability = _read("docs/stability.md")
        loading_boundary = _read("docs/external-connector-loading-boundary.md")
        docs_index = _read("docs/README.md")

        self.assertIn("## Connector Package Layout", connectors)
        self.assertIn("MANIFEST", connectors)
        self.assertIn("execute(binding, credential_provider=None, context=None)", connectors)
        self.assertIn("load_external_connector(Path(\"examples/connectors/local_echo_connector.py\"))", connectors)
        self.assertIn("Connector package smoke contract", connectors)
        self.assertIn("automatic connector discovery", connectors)
        self.assertIn("--connector-fixture", connectors)
        self.assertIn("long-running service", connectors)
        self.assertIn("connectors` inspection command", connectors)
        self.assertIn("2 MiB", connectors)
        self.assertIn("no-follow descriptor", connectors)

        self.assertIn("### Local Connector Package Shape", examples)
        self.assertIn("examples/connectors/local_echo_connector.py", examples)
        self.assertIn("runtime-generated smoke artifacts", examples)

        self.assertIn("Connector Package Compatibility", compatibility)
        self.assertIn("Workflow DSL `0.1.0` compatibility is separate from connector package", compatibility)
        self.assertIn("connector manifest version", compatibility)
        self.assertIn("run`, `resume`, and `bundle-run`", compatibility)
        self.assertIn("external-connector-loading-boundary.md", compatibility)

        self.assertIn("explicit local connector fixture loading", stability)
        self.assertIn("automatic connector discovery and product-specific connector packages", stability)
        self.assertIn("device/inode-bound no-follow descriptor", stability)

        self.assertIn("# External Connector Fixture Loading Boundary", loading_boundary)
        self.assertIn("regular, non-symbolic-link", loading_boundary)
        self.assertIn("2 MiB", loading_boundary)
        self.assertIn("not a Python sandbox", loading_boundary)
        self.assertIn("external-connector-loading-boundary.md", docs_index)

    def test_builtin_http_payload_boundary_is_documented(self):
        connectors = _read("docs/connectors.md")
        compatibility = _read("docs/workflow-dsl-compatibility.md")
        stability = _read("docs/stability.md")

        self.assertIn("### HTTP Payload Boundary", connectors)
        self.assertIn("1,048,576`-byte (`1 MiB`)", connectors)
        self.assertIn("http connector response body must be valid", connectors)
        self.assertIn("UTF-8", connectors)
        self.assertIn('response_mode` to `metadata`', connectors)
        self.assertIn('body_discarded: true', connectors)
        self.assertIn("http connector redirects are disabled", connectors)
        self.assertIn("rejects all `3xx` redirects", compatibility)
        self.assertIn("Built-in HTTP request and", compatibility)
        self.assertIn("UTF-8 response bodies are bounded to 1 MiB", compatibility)
        self.assertIn("response_mode` (`full` or `metadata`)", compatibility)
        self.assertIn("Built-in HTTP connector request/response payloads are bounded to 1 MiB", stability)
        self.assertIn("rejects every `3xx` redirect", stability)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
