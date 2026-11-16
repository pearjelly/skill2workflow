import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.cli import main
from skill2workflow.compiler import compile_ir_to_workflow
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.dashboard import build_run_detail_from_control
from skill2workflow.executor import LocalExecutor
from skill2workflow.parser import parse_skill_text
from skill2workflow.service_client import _validate_run_detail, ServiceActionError


class ExecutionSemanticsTests(TestCase):
    def test_legacy_unlabelled_completions_do_not_require_new_audit_events(self):
        workflow = compile_ir_to_workflow(parse_skill_text('## Steps\n1. Draft report\n'))
        for storage in ("json", "sqlite"):
            with self.subTest(storage=storage), TemporaryDirectory() as temporary:
                control = LocalControlPlane(Path(temporary), storage=storage)
                control.publish_workflow(workflow)
                state = control.executor.run(workflow)
                for event in state["events"]:
                    event.pop("execution", None)
                for result in state["node_results"].values():
                    result.pop("execution", None)
                control.executor.store.save(state)
                control._append_audit_batch([
                    {"type": kind, "run_id": state["run_id"], "workflow_id": state["workflow_id"],
                     "workflow_version": state["workflow_version"], "timestamp": state["events"][0]["timestamp"]}
                    for kind in ("run_started", "run_completed")
                ])
                self.assertEqual(control.inspect_run_audit(state["run_id"])["status"], "clean")

    def test_connector_attempt_and_result_are_enforced(self):
        workflow = compile_ir_to_workflow(parse_skill_text(
            '## Steps\n1. Fetch <!-- skill2workflow: http {"request":{"url":"https://example.invalid"}} -->\n'
        ))
        class Runtime:
            def execute_connector(self, node, **kwargs):
                return {"status": "completed", "output": {}, "connector": {"id": "http", "kind": "http"}}
        with TemporaryDirectory() as temporary:
            state = LocalExecutor(Path(temporary), connector_runtime=Runtime()).run(workflow)
        node_id = workflow["nodes"][1]["id"]
        self.assertEqual(state["node_results"][node_id]["execution"], "enforced")
        events = [event for event in state["events"] if event["node_id"] == node_id]
        self.assertTrue(any(event["type"] == "connector_completed" for event in events))
        self.assertTrue(all(event["execution"] == "enforced" for event in events))

    def test_descriptive_steps_cannot_look_like_enforced_work_in_state_audit_or_detail(self):
        workflow = compile_ir_to_workflow(parse_skill_text(
            '## Steps\n1. Draft report\n2. Verify report\n3. Ask user for approval\n'
        ))
        for storage in ("json", "sqlite"):
            with self.subTest(storage=storage), TemporaryDirectory() as temporary:
                control = LocalControlPlane(Path(temporary), storage=storage)
                control.publish_workflow(workflow)
                state = control.run_published_workflow(workflow["workflow"]["id"], workflow["workflow"]["version"])
                self.assertEqual(state["status"], "waiting")
                for node in workflow["nodes"][1:3]:
                    result = state["node_results"][node["id"]]
                    self.assertEqual(result["status"], "completed")
                    self.assertEqual(result["execution"], "descriptive")
                gate = workflow["nodes"][3]["id"]
                self.assertEqual(state["events"][-1]["execution"], "enforced")
                audits = control.list_audit_events(run_id=state["run_id"])
                completed = [event for event in audits if event["type"] == "node_completed"]
                self.assertTrue(any(event.get("execution") == "descriptive" for event in completed))
                detail = build_run_detail_from_control(control, state["run_id"])
                self.assertEqual(detail["schema_version"], "skill2workflow-run-detail-0.2.0")
                self.assertEqual(detail["run"]["node_overlays"][gate]["execution"], "enforced")
                _validate_run_detail(detail, state["run_id"])
                detail["run"]["node_overlays"][gate]["execution"] = "incorrect"
                with self.assertRaises(ServiceActionError):
                    _validate_run_detail(detail, state["run_id"])
                stdout = StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(main(["control-run", state["run_id"], "--state-dir", temporary, "--storage", storage]), 0)
                self.assertIn('"execution": "descriptive"', stdout.getvalue())
                resumed = control.resume_published_run(state["run_id"], approved=False)
                self.assertEqual(resumed["node_results"][gate]["execution"], "enforced")
                self.assertTrue(all(event.get("execution") == "enforced" for event in resumed["events"] if event["node_id"] == gate))

    def test_remote_schema_versions_preserve_the_legacy_closed_contract(self):
        root = Path(__file__).resolve().parents[1] / "schemas"
        old = json.loads((root / "run-detail-0.1.0.schema.json").read_text())
        new = json.loads((root / "run-detail-0.2.0.schema.json").read_text())
        self.assertNotIn("execution", old["$defs"]["overlay"]["properties"])
        self.assertIn("execution", new["$defs"]["overlay"]["properties"])
