import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.cli import main
from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow_notices, validate_workflow_structured
from skill2workflow.executor import LocalExecutor
from skill2workflow.parser import parse_skill_text


class DslNoticeTests(TestCase):
    def test_reserved_fields_warn_without_becoming_execution_policy(self):
        workflow = compile_ir_to_workflow(parse_skill_text('## Steps\n1. Draft report\n'))
        workflow.update(guards=[{"id": "g", "description": "Never execute"}],
                        state_schema={"type": "object"}, checkpoints=[{"id": "cp"}])
        workflow["nodes"][1].update(guard="Never execute", requires=["unavailable"], produces=["report"])
        workflow["edges"][0]["condition"] = {"expr": "false"}
        self.assertEqual(validate_workflow_structured(workflow), [])
        notices = validate_workflow_notices(workflow)
        paths = [notice["path"] for notice in notices]
        for path in (["guards"], ["state_schema"], ["checkpoints"], ["nodes", 1, "guard"],
                     ["nodes", 1, "requires"], ["nodes", 1, "produces"], ["edges", 0, "condition"]):
            self.assertIn(path, paths)
        self.assertTrue(all(notice["severity"] == "notice" for notice in notices))
        with TemporaryDirectory() as temporary:
            self.assertEqual(LocalExecutor(Path(temporary) / "state").run(workflow)["status"], "completed")
            path = Path(temporary) / "workflow.json"
            path.write_text(json.dumps(workflow))
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["validate", str(path), "--format", "json"]), 0)
            report = json.loads(stdout.getvalue())
            self.assertTrue(report["valid"])
            self.assertEqual(report["notices"], notices)
