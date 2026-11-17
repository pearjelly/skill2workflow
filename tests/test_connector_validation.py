import copy
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.cli import main
from skill2workflow.compiler import validate_workflow_structured
from skill2workflow.control_plane import LocalControlPlane


class ConnectorRequestValidationTests(TestCase):
    def test_missing_requests_are_rejected_by_validator_cli_and_publication(self):
        original = json.loads(Path("examples/workflows/http-connector.workflow.json").read_text())
        for connector_id in ("http", "http_assert"):
            for request in (None, "not an object"):
                with self.subTest(connector=connector_id, request=request), TemporaryDirectory() as temporary:
                    workflow = copy.deepcopy(original)
                    index, node = next((i, n) for i, n in enumerate(workflow["nodes"]) if n["type"] == "tool_call")
                    node["connector"] = {"id": connector_id}
                    if request is not None:
                        node["connector"]["request"] = request
                    errors = validate_workflow_structured(workflow)
                    self.assertIn(
                        ("connector_request_missing", ["nodes", index, "connector", "request"]),
                        [(error["code"], error["path"]) for error in errors],
                    )
                    path = Path(temporary) / "workflow.json"
                    path.write_text(json.dumps(workflow))
                    stdout = StringIO()
                    with redirect_stdout(stdout):
                        self.assertEqual(main(["validate", str(path), "--format", "json"]), 1)
                    self.assertFalse(json.loads(stdout.getvalue())["valid"])
                    control = LocalControlPlane(Path(temporary) / "state")
                    with self.assertRaises(ValueError):
                        control.publish_workflow(workflow)
                    self.assertEqual(control.list_workflows(), [])
