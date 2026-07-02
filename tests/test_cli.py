import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.cli import main


class CliTests(TestCase):
    def test_visualize_command_writes_litegraph_json(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            run_state_path = tmp_path / "run.json"
            output_path = tmp_path / "graph.json"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            run_state_path.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "current_node": "end",
                        "node_results": {"end": {"status": "completed"}},
                    }
                ),
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "visualize",
                    str(workflow_path),
                    "--run-state",
                    str(run_state_path),
                    "-o",
                    str(output_path),
                ]
            )

            graph = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(graph["version"], "skill2workflow-litegraph-0.1.0")
        self.assertEqual(graph["nodes"][-1]["properties"]["run_status"], "completed")

    def test_control_plane_commands_publish_list_and_run_published_workflow(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            state_dir = tmp_path / "state"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")

            with redirect_stdout(StringIO()):
                publish_exit = main(["publish", str(workflow_path), "--state-dir", str(state_dir)])
                workflows_exit = main(["workflows", "--state-dir", str(state_dir)])
                run_exit = main(
                    [
                        "run-published",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                    ]
                )

            from skill2workflow.control_plane import LocalControlPlane

            control = LocalControlPlane(state_dir)
            workflow_records = control.list_workflows()
            run_summary = control.list_runs()[0]

        self.assertEqual(publish_exit, 0)
        self.assertEqual(workflows_exit, 0)
        self.assertEqual(run_exit, 0)
        self.assertEqual(workflow_records[0]["workflow_id"], "workflow_demo")
        self.assertEqual(workflow_records[0]["status"], "published")
        self.assertEqual(run_summary["workflow_version"], "0.1.0")

    def test_validate_command_can_emit_structured_json_errors(self):
        with TemporaryDirectory() as tmp:
            workflow_path = Path(tmp) / "workflow.json"
            invalid = _workflow()
            invalid["edges"][0]["to"] = "missing"
            workflow_path.write_text(json.dumps(invalid), encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["validate", str(workflow_path), "--format", "json"])

        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(payload["valid"], False)
        self.assertEqual(payload["schema_version"], "0.1.0")
        self.assertIn("errors", payload)
        self.assertTrue(any(error["code"] == "edge_target_missing" for error in payload["errors"]))


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {"id": "workflow_demo", "name": "demo", "version": "0.1.0", "status": "draft"},
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }
