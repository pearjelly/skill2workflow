from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.control_plane import LocalControlPlane
from unittest.mock import patch

from skill2workflow.dashboard import (
    build_control_snapshot,
    build_control_snapshot_from_control,
)


class DashboardTests(TestCase):
    def test_sqlite_bounded_snapshot_does_not_call_unbounded_list_paths(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start v1"))
            control.publish_workflow(_workflow(version="1.1.0", node_title="Start v2"))
            control.run_published_workflow("workflow_dashboard", "1.0.0")
            control.run_published_workflow("workflow_dashboard", "1.1.0")

            with patch.object(
                control.store,
                "load_index",
                side_effect=AssertionError("unbounded workflow read"),
            ), patch.object(
                control.store,
                "list_audit_events",
                side_effect=AssertionError("unbounded audit read"),
            ), patch.object(
                control.executor.store,
                "list",
                side_effect=AssertionError("unbounded run read"),
            ):
                snapshot = build_control_snapshot_from_control(control, max_items=1)

        self.assertEqual(snapshot["summary"]["workflow_count"], 2)
        self.assertEqual(snapshot["summary"]["run_count"], 2)
        self.assertEqual(len(snapshot["workflows"]), 1)
        self.assertEqual(len(snapshot["runs"]), 1)
        self.assertEqual(len(snapshot["audit_events"]), 1)
        self.assertTrue(snapshot["window"]["workflows"]["truncated"])
        self.assertTrue(snapshot["window"]["runs"]["truncated"])

    def test_bounded_snapshot_reports_total_and_returned_windows(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start v1"))
            control.publish_workflow(_workflow(version="1.1.0", node_title="Start v2"))
            control.run_published_workflow("workflow_dashboard", "1.0.0")
            control.run_published_workflow("workflow_dashboard", "1.1.0")

            snapshot = build_control_snapshot(state_dir, max_items=1)

        self.assertEqual(snapshot["summary"]["workflow_count"], 2)
        self.assertEqual(snapshot["summary"]["run_count"], 2)
        self.assertGreater(snapshot["summary"]["audit_event_count"], 1)
        self.assertEqual(len(snapshot["workflows"]), 1)
        self.assertEqual(len(snapshot["runs"]), 1)
        self.assertEqual(len(snapshot["audit_events"]), 1)
        self.assertEqual(snapshot["audit_events"][0]["type"], "run_completed")
        self.assertEqual(snapshot["window"]["max_items"], 1)
        self.assertEqual(
            snapshot["window"]["workflows"],
            {"total": 2, "returned": 1, "truncated": True},
        )
        self.assertEqual(
            snapshot["window"]["runs"],
            {"total": 2, "returned": 1, "truncated": True},
        )
        self.assertEqual(
            snapshot["window"]["audit_events"],
            {
                "total": snapshot["summary"]["audit_event_count"],
                "returned": 1,
                "truncated": True,
            },
        )

    def test_bounded_snapshot_rejects_non_positive_or_boolean_limit(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            for value in (0, -1, True):
                with self.subTest(value=value):
                    with self.assertRaisesRegex(ValueError, "max_items"):
                        build_control_snapshot(state_dir, max_items=value)

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

        waiting_summary = next(run for run in snapshot["runs"] if run["run_id"] == waiting_run["run_id"])
        failed_summary = next(run for run in snapshot["runs"] if run["run_id"] == failed_run["run_id"])
        waiting_overlay = waiting_summary["node_overlays"]["review"]
        connector_overlay = failed_summary["node_overlays"]["call_api"]

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
        self.assertEqual(waiting_overlay["status"], "waiting")
        self.assertEqual(waiting_overlay["current"], True)
        self.assertEqual(waiting_overlay["latest_event_type"], "human_gate_waiting")
        self.assertEqual(connector_overlay["status"], "failed")
        self.assertEqual(connector_overlay["connector_id"], "http")
        self.assertEqual(connector_overlay["connector_status"], "failed")
        self.assertEqual(connector_overlay["attempts"], 1)
        self.assertEqual(connector_overlay["audit_event_count"], 3)
        self.assertNotIn("output", connector_overlay)

    def test_interrupted_run_is_a_distinct_critical_attention_item(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start"))
            run = control.run_published_workflow("workflow_dashboard", "1.0.0")
            detail = control.get_run(run["run_id"])
            detail["status"] = "interrupted"
            detail["events"].append(
                {
                    "type": "run_interrupted",
                    "node_id": detail["current_node"],
                    "timestamp": "2026-08-11T00:00:00+00:00",
                }
            )
            control.executor.store.save(detail)

            insights = build_control_snapshot(state_dir)["operator_insights"]

        self.assertEqual(insights["attention_counts"]["interrupted_runs"], 1)
        self.assertIn(
            ("interrupted_run", run["run_id"]),
            {
                (item["kind"], item.get("run_id"))
                for item in insights["attention_items"]
            },
        )


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
