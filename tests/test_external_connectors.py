import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.external_connectors import (
    MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES,
    load_external_connector,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "connectors" / "local_echo_connector.py"


class ExternalConnectorLoaderTests(TestCase):
    def test_loader_executes_a_regular_fixture_without_changing_contract(self):
        connector = load_external_connector(FIXTURE)

        self.assertEqual(connector.manifest["id"], "local_echo")
        self.assertTrue(callable(connector.executor))

    def test_loader_rejects_a_symbolic_link_before_execution(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            link = root / "connector.py"
            try:
                os.symlink(FIXTURE, link)
            except (AttributeError, OSError):
                self.skipTest("symbolic links are unavailable")

            with self.assertRaisesRegex(
                ValueError, "external connector file must be a regular non-symlink file"
            ):
                load_external_connector(link)

    def test_loader_rejects_non_regular_paths(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaisesRegex(
                ValueError, "external connector file must be a regular non-symlink file"
            ):
                load_external_connector(directory)

    def test_loader_bounds_source_before_compiling(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "oversized.py"
            path.write_bytes(b"#" * (MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES + 1))

            with self.assertRaisesRegex(
                ValueError,
                f"external connector file exceeds {MAX_EXTERNAL_CONNECTOR_FIXTURE_BYTES} bytes",
            ):
                load_external_connector(path)

    def test_loader_rejects_invalid_utf8_without_executing_source(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.py"
            path.write_bytes(b"MANIFEST = {}\n\xff")

            with self.assertRaisesRegex(
                ValueError, "external connector file must be UTF-8"
            ):
                load_external_connector(path)

    def test_loader_normalizes_syntax_errors(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "syntax.py"
            path.write_text("def broken(:\n", encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError, "external connector file has invalid Python syntax"
            ):
                load_external_connector(path)
