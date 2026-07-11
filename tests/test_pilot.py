import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.pilot import run_pilot_playbook


class PilotPlaybookTests(TestCase):
    def test_pilot_playbook_generates_runnable_local_pilot_artifacts(self):
        repo_root = Path(__file__).resolve().parents[1]

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            result = run_pilot_playbook(repo_root=repo_root, work_dir=work_dir, reset=True)

            workflow_path = Path(result["artifacts"]["workflow"])
            snapshot_path = Path(result["artifacts"]["snapshot"])
            overlay_path = Path(result["artifacts"]["litegraph_overlay"])
            run_path = Path(result["artifacts"]["run"])
            self.assertTrue(workflow_path.exists())
            self.assertTrue(snapshot_path.exists())
            self.assertTrue(overlay_path.exists())
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            graph = json.loads(overlay_path.read_text(encoding="utf-8"))
            run_detail = json.loads(run_path.read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["workflow_id"], "workflow_customer_support_pilot")
        self.assertEqual(result["workflow_version"], "0.1.0")
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["trigger_response"]["source"], "local-webhook")
        self.assertEqual(result["trigger_response"]["input_keys"], ["customer_id", "priority", "ticket_id"])
        self.assertEqual(result["snapshot_summary"]["run_status_counts"], {"completed": 1})
        self.assertEqual(run_detail["context"]["input"]["ticket_id"], "ticket_123")
        self.assertEqual(run_detail["context"]["trigger"]["source"], "local-webhook")
        self.assertNotIn("local-secret-value", json.dumps(run_detail))
        self.assertIn("node_overlays", snapshot["runs"][0])
        self.assertEqual(snapshot["runs"][0]["node_overlays"]["call_support_api"]["connector_status"], "completed")
        self.assertEqual(
            graph["extra"]["run_overlay"]["trigger"]["input_keys"],
            ["customer_id", "priority", "ticket_id"],
        )
        self.assertNotIn("ticket_123", json.dumps(graph["extra"]["run_overlay"]))
        self.assertTrue(result["connector_request"]["authorization_present"])
        self.assertTrue(result["connector_request"]["credential_header_matched"])
        self.assertTrue(result["connector_request"]["mapped_body_matched"])
        self.assertIn("ticket_id", result["connector_request"]["body_keys"])
        self.assertNotIn("local-secret-value", json.dumps(result))

    def test_pilot_playbook_reset_replaces_previous_workspace(self):
        repo_root = Path(__file__).resolve().parents[1]

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            work_dir.mkdir()
            stale_file = work_dir / "stale.txt"
            stale_file.write_text("old", encoding="utf-8")

            run_pilot_playbook(repo_root=repo_root, work_dir=work_dir, reset=True)

            self.assertFalse(stale_file.exists())
            self.assertTrue((work_dir / "artifacts" / "workflow.json").exists())

    def test_pilot_playbook_no_reset_reuses_existing_published_artifact(self):
        repo_root = Path(__file__).resolve().parents[1]

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            first = run_pilot_playbook(repo_root=repo_root, work_dir=work_dir, reset=True)
            second = run_pilot_playbook(repo_root=repo_root, work_dir=work_dir, reset=False)

        self.assertEqual(first["workflow_id"], second["workflow_id"])
        self.assertEqual(second["run_status"], "completed")
