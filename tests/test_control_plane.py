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
