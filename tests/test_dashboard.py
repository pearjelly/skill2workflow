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

    def test_build_control_snapshot_derives_operator_insights(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start v1"))
            control.publish_workflow(_workflow(version="1.1.0", node_title="Start v2"))
            control.publish_workflow(_approval_workflow(version="1.0.0"))
            control.publish_workflow(_failing_connector_workflow(version="1.0.0"))

            waiting_run = control.run_published_workflow("workflow_waiting", "1.0.0")
            failed_run = control.run_published_workflow("workflow_connector_failure", "1.0.0")
            snapshot = build_control_snapshot(state_dir)

        insights = snapshot["operator_insights"]
        self.assertEqual(insights["attention_counts"]["waiting_runs"], 1)
        self.assertEqual(insights["attention_counts"]["failed_runs"], 1)
        self.assertEqual(insights["attention_counts"]["connector_failures"], 1)
        self.assertEqual(insights["attention_counts"]["version_changes"], 1)
        self.assertEqual(insights["connector_event_counts"]["connector_started"], 1)
        self.assertEqual(insights["connector_event_counts"]["connector_failed"], 1)
        self.assertEqual(insights["version_changes"][0]["workflow_id"], "workflow_dashboard")
        self.assertEqual(insights["version_changes"][0]["versions"], ["1.0.0", "1.1.0"])

        attention = {(item["kind"], item.get("run_id")) for item in insights["attention_items"]}
        self.assertIn(("waiting_run", waiting_run["run_id"]), attention)
        self.assertIn(("failed_run", failed_run["run_id"]), attention)
        self.assertIn(("connector_failure", failed_run["run_id"]), attention)
        self.assertLessEqual(len(insights["recent_events"]), 5)
        self.assertEqual(insights["recent_events"][-1]["type"], "run_failed")


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


def _approval_workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_waiting",
            "name": "waiting",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "review"},
            {
                "id": "review",
                "type": "human_gate",
                "title": "Review",
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
            {"id": "edge_review_end", "from": "review", "to": "end", "label": "next"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "failure"},
        ],
    }


def _failing_connector_workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_connector_failure",
            "name": "connector-failure",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "call_api"},
            {
                "id": "call_api",
                "type": "tool_call",
                "title": "Call API",
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {
                        "method": "POST",
                        "url": "ftp://example.test/not-called",
                    },
                },
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_call", "from": "start", "to": "call_api", "label": "next"},
            {"id": "edge_call_end", "from": "call_api", "to": "end", "label": "next"},
            {"id": "edge_call_failure", "from": "call_api", "to": "failure", "label": "failure"},
        ],
    }
