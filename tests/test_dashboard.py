from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.dashboard import build_control_snapshot


class DashboardTests(TestCase):
    def test_build_control_snapshot_summarizes_registry_runs_audit_and_versions(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start v1"))
            control.publish_workflow(_workflow(version="1.1.0", node_title="Start v2"))
            control.deprecate_workflow("workflow_dashboard", "1.0.0")
            run_state = control.run_published_workflow("workflow_dashboard", "1.1.0")

            snapshot = build_control_snapshot(state_dir)

        self.assertEqual(snapshot["schema_version"], "skill2workflow-control-snapshot-0.1.0")
        self.assertEqual(snapshot["summary"]["workflow_count"], 2)
        self.assertEqual(snapshot["summary"]["run_count"], 1)
        self.assertEqual(snapshot["summary"]["audit_event_count"], 5)
        self.assertEqual(snapshot["summary"]["connector_count"], 2)
        self.assertEqual(snapshot["summary"]["status_counts"], {"deprecated": 1, "published": 1})
        self.assertEqual(snapshot["workflows"][0]["workflow_id"], "workflow_dashboard")
        self.assertEqual(snapshot["runs"][0]["run_id"], run_state["run_id"])
        self.assertEqual(snapshot["runs"][0]["event_count"], len(run_state["events"]))
        self.assertEqual(
            [event["type"] for event in snapshot["audit_events"]],
            [
                "workflow_published",
                "workflow_published",
                "workflow_deprecated",
                "run_started",
                "run_completed",
            ],
        )
        comparison = snapshot["version_comparisons"][0]
        self.assertEqual(comparison["workflow_id"], "workflow_dashboard")
        self.assertEqual(comparison["versions"], ["1.0.0", "1.1.0"])
        self.assertTrue(comparison["checksum_changed"])
        self.assertEqual(comparison["node_count_delta"], 0)
        self.assertEqual(comparison["edge_count_delta"], 0)


def _workflow(version: str, node_title: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_dashboard",
            "name": "dashboard",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": node_title, "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }
