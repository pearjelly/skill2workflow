import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.control_plane import LocalControlPlane


class ControlPlaneTests(TestCase):
    def test_publish_workflow_persists_immutable_version_and_audit(self):
        workflow = _workflow(version="1.0.0")

        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            record = control.publish_workflow(workflow)
            stored = control.get_workflow("workflow_control", "1.0.0")
            audit_events = control.list_audit_events()

            changed = _workflow(version="1.0.0")
            changed["nodes"][0]["title"] = "Changed Start"
            with self.assertRaisesRegex(ValueError, "immutable"):
                control.publish_workflow(changed)

        self.assertEqual(record["workflow_id"], "workflow_control")
        self.assertEqual(record["version"], "1.0.0")
        self.assertEqual(record["status"], "published")
        self.assertEqual(stored["workflow"]["status"], "published")
        self.assertEqual(audit_events[0]["type"], "workflow_published")
        self.assertEqual(audit_events[0]["workflow_id"], "workflow_control")
        self.assertIn("checksum", record)

    def test_deprecate_updates_registry_without_mutating_published_artifact(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            control.publish_workflow(_workflow(version="1.0.0"))

            record = control.deprecate_workflow("workflow_control", "1.0.0")
            stored = control.get_workflow("workflow_control", "1.0.0")
            audit_types = [event["type"] for event in control.list_audit_events()]

        self.assertEqual(record["status"], "deprecated")
        self.assertEqual(stored["workflow"]["status"], "published")
        self.assertEqual(audit_types, ["workflow_published", "workflow_deprecated"])

    def test_run_published_workflow_binds_run_to_immutable_version_and_audit(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            control.publish_workflow(_workflow(version="2.0.0"))

            run_state = control.run_published_workflow("workflow_control", "2.0.0")
            run_summary = control.list_runs()[0]
            audit_events = control.list_audit_events()
            audit_types = [event["type"] for event in audit_events]

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(run_state["workflow_id"], "workflow_control")
        self.assertEqual(run_state["workflow_version"], "2.0.0")
        self.assertEqual(run_summary["workflow_version"], "2.0.0")
        self.assertIn("run_started", audit_types)
        self.assertIn("run_completed", audit_types)
        self.assertEqual(audit_events[1]["run_id"], run_state["run_id"])

    def test_run_published_workflow_can_use_sqlite_run_storage(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="2.0.0"))

            run_state = control.run_published_workflow("workflow_control", "2.0.0")
            run_summary = LocalControlPlane(state_dir, storage="sqlite").list_runs()[0]

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(run_summary["run_id"], run_state["run_id"])
        self.assertEqual(run_summary["workflow_id"], "workflow_control")

    def test_sqlite_storage_persists_workflow_registry_and_audit_events(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")

            record = control.publish_workflow(_workflow(version="3.0.0"))
            deprecated = control.deprecate_workflow("workflow_control", "3.0.0")
            records = LocalControlPlane(state_dir, storage="sqlite").list_workflows()
            audit_types = [event["type"] for event in control.list_audit_events()]

            with sqlite3.connect(state_dir / "control.sqlite3") as connection:
                workflow_rows = connection.execute("select workflow_id, version, status from workflow_versions").fetchall()
                audit_rows = connection.execute("select event_type from audit_events order by sequence").fetchall()

        self.assertEqual(record["workflow_id"], "workflow_control")
        self.assertEqual(deprecated["status"], "deprecated")
        self.assertEqual(records[0]["status"], "deprecated")
        self.assertEqual(workflow_rows, [("workflow_control", "3.0.0", "deprecated")])
        self.assertEqual([row[0] for row in audit_rows], ["workflow_published", "workflow_deprecated"])
        self.assertEqual(audit_types, ["workflow_published", "workflow_deprecated"])

    def test_sqlite_storage_imports_existing_json_registry_and_audit(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            json_control = LocalControlPlane(state_dir)
            json_control.publish_workflow(_workflow(version="4.0.0"))

            sqlite_control = LocalControlPlane(state_dir, storage="sqlite")
            records = sqlite_control.list_workflows()
            audit_types_before_run = [event["type"] for event in sqlite_control.list_audit_events()]
            run_state = sqlite_control.run_published_workflow("workflow_control", "4.0.0")
            audit_types_after_run = [event["type"] for event in sqlite_control.list_audit_events()]

        self.assertEqual(records[0]["workflow_id"], "workflow_control")
        self.assertEqual(records[0]["version"], "4.0.0")
        self.assertEqual(audit_types_before_run, ["workflow_published"])
        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(audit_types_after_run, ["workflow_published", "run_started", "run_completed"])

    def test_resume_published_run_records_resume_and_terminal_audit(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_approval_workflow(version="5.0.0"))

            waiting = control.run_published_workflow("workflow_control", "5.0.0")
            completed = control.resume_published_run(waiting["run_id"], approved=True)
            detail = control.get_run(waiting["run_id"])
            audit_events = control.list_audit_events(run_id=waiting["run_id"])
            completed_events = control.list_audit_events(event_type="run_completed")

        self.assertEqual(waiting["status"], "waiting")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(detail["status"], "completed")
        self.assertEqual(
            [event["type"] for event in audit_events],
            ["run_started", "run_waiting", "run_resumed", "run_completed"],
        )
        self.assertEqual(completed_events[0]["run_id"], waiting["run_id"])

    def test_audit_events_can_filter_by_workflow_version_and_run_id(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="6.0.0"))
            control.publish_workflow(_workflow(version="7.0.0"))

            first = control.run_published_workflow("workflow_control", "6.0.0")
            second = control.run_published_workflow("workflow_control", "7.0.0")
            version_events = control.list_audit_events(workflow_id="workflow_control", version="6.0.0")
            run_events = control.list_audit_events(run_id=second["run_id"])

        self.assertTrue(all(event.get("workflow_version") == "6.0.0" for event in version_events))
        self.assertEqual([event["type"] for event in run_events], ["run_started", "run_completed"])
        self.assertEqual(run_events[0]["run_id"], second["run_id"])
        self.assertNotEqual(first["run_id"], second["run_id"])

    def test_connector_registry_returns_placeholder_connectors(self):
        with TemporaryDirectory() as tmp:
            connectors = LocalControlPlane(Path(tmp)).list_connectors()

        connector_ids = {connector["id"] for connector in connectors}
        self.assertIn("manual", connector_ids)
        self.assertIn("http", connector_ids)
        self.assertTrue(all(connector["status"] == "placeholder" for connector in connectors))


def _workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_control",
            "name": "control",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }


def _approval_workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_control",
            "name": "control",
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
