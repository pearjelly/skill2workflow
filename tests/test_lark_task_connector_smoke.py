import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.lark_task_connector_smoke import run_lark_task_connector_smoke


class LarkTaskConnectorSmokeTests(TestCase):
    def test_lark_task_connector_smoke_runs_explicit_dry_run_package(self):
        repo_root = Path(__file__).resolve().parents[1]

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "lark-task-connector"
            result = run_lark_task_connector_smoke(repo_root=repo_root, work_dir=work_dir, reset=True)

            workflow_path = Path(result["artifacts"]["workflow"])
            run_path = Path(result["artifacts"]["run"])
            audit_path = Path(result["artifacts"]["audit"])
            snapshot_path = Path(result["artifacts"]["snapshot"])
            connectors_path = Path(result["artifacts"]["connectors"])
            trigger_path = Path(result["artifacts"]["trigger_response"])
            self.assertTrue(workflow_path.exists())
            self.assertTrue(run_path.exists())
            self.assertTrue(audit_path.exists())
            self.assertTrue(snapshot_path.exists())
            self.assertTrue(connectors_path.exists())
            self.assertTrue(trigger_path.exists())
            audit_events = json.loads(audit_path.read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["default_connector_ids"], ["manual", "http"])
        self.assertEqual(result["connector_ids"], ["manual", "http", "lark_task"])
        self.assertEqual(result["workflow_id"], "workflow_lark_task_connector_smoke")
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["connector_summary"]["connector_id"], "lark_task")
        self.assertEqual(result["connector_summary"]["operation"], "create_task")
        self.assertEqual(result["connector_summary"]["mode"], "dry_run")
        self.assertTrue(result["connector_summary"]["task_title_present"])
        self.assertTrue(result["connector_summary"]["task_description_present"])
        self.assertTrue(result["connector_summary"]["assignee_present"])
        self.assertTrue(result["connector_summary"]["due_at_present"])
        self.assertEqual(result["connector_summary"]["credential_handles"], ["lark_bot_access_token"])
        self.assertEqual(
            result["connector_summary"]["input_mapping_keys"],
            ["assignee_open_id", "description", "due_at", "title"],
        )
        self.assertEqual(result["snapshot_summary"]["run_status_counts"], {"completed": 1})
        self.assertEqual(result["snapshot_summary"]["connector_count"], 3)

        encoded_result = json.dumps(result, ensure_ascii=False)
        encoded_audit = json.dumps(audit_events, ensure_ascii=False)
        self.assertNotIn("local-lark-secret", encoded_result)
        self.assertNotIn("local-lark-secret", encoded_audit)
        self.assertNotIn("Renewal risk follow-up", encoded_audit)
        self.assertNotIn("Customer ACME needs executive review", encoded_audit)
        self.assertNotIn("ou_lark_task_owner", encoded_audit)
        self.assertNotIn("2026-07-09T09:00:00Z", encoded_audit)
