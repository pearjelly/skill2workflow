import json
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
