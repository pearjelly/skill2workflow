import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.lark_task_pilot import run_lark_task_pilot


class LarkTaskPilotTests(TestCase):
    def test_lark_task_pilot_runs_sales_renewal_flow_with_control_gate(self):
        repo_root = Path(__file__).resolve().parents[1]

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "lark-task-pilot"
            result = run_lark_task_pilot(repo_root=repo_root, work_dir=work_dir, reset=True)

            workflow_path = Path(result["artifacts"]["workflow"])
            trigger_path = Path(result["artifacts"]["trigger_response"])
            run_path = Path(result["artifacts"]["run"])
            audit_path = Path(result["artifacts"]["audit"])
            snapshot_path = Path(result["artifacts"]["snapshot"])
            overlay_path = Path(result["artifacts"]["litegraph_overlay"])
            connectors_path = Path(result["artifacts"]["connectors"])
            self.assertTrue(workflow_path.exists())
            self.assertTrue(trigger_path.exists())
            self.assertTrue(run_path.exists())
            self.assertTrue(audit_path.exists())
            self.assertTrue(snapshot_path.exists())
            self.assertTrue(overlay_path.exists())
            self.assertTrue(connectors_path.exists())

            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            run_state = json.loads(run_path.read_text(encoding="utf-8"))
            audit_events = json.loads(audit_path.read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["scenario"]["id"], "sales_renewal_risk_followup")
        self.assertEqual(result["workflow_id"], "workflow_lark_task_pilot")
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["default_connector_ids"], ["manual", "http"])
        self.assertEqual(result["connector_ids"], ["manual", "http", "lark_task"])

        self.assertEqual(result["gate_summary"], {"node_id": "review_renewal_risk", "resumed": True, "approved": True})
        self.assertEqual(result["trigger_summary"]["source"], "local-webhook")
        self.assertEqual(
            result["trigger_summary"]["input_keys"],
            ["account_id", "account_name", "due_at", "owner_open_id", "renewal_risk"],
        )

        self.assertEqual(result["connector_summary"]["connector_id"], "lark_task")
        self.assertEqual(result["connector_summary"]["operation"], "create_task")
        self.assertEqual(result["connector_summary"]["mode"], "dry_run")
        self.assertEqual(result["connector_summary"]["credential_handles"], ["lark_bot_access_token"])
        self.assertEqual(
            result["connector_summary"]["input_mapping_keys"],
            ["account_name", "due_at", "owner_open_id", "renewal_risk"],
        )
        self.assertTrue(result["connector_summary"]["task_title_present"])
        self.assertTrue(result["connector_summary"]["task_description_present"])
        self.assertTrue(result["connector_summary"]["assignee_present"])
        self.assertTrue(result["connector_summary"]["due_at_present"])
        self.assertEqual(result["snapshot_summary"]["run_status_counts"], {"completed": 1})
        self.assertEqual(result["snapshot_summary"]["connector_count"], 3)

        node_ids = [node["id"] for node in workflow["nodes"]]
        self.assertEqual(node_ids, ["start", "review_renewal_risk", "create_lark_task", "failure", "end"])
        create_node = next(node for node in workflow["nodes"] if node["id"] == "create_lark_task")
        self.assertEqual(create_node["connector"]["id"], "lark_task")
        self.assertEqual(create_node["connector"]["operation"], "create_task")
        self.assertEqual(create_node["connector"]["mode"], "dry_run")

        self.assertEqual(run_state["node_results"]["review_renewal_risk"]["status"], "approved")
        connector_node_result = run_state["node_results"]["create_lark_task"]
        encoded_connector_result = json.dumps(connector_node_result, ensure_ascii=False)
        encoded_audit = json.dumps(audit_events, ensure_ascii=False)
        for raw_value in (
            "ACME Global",
            "High renewal risk because executive sponsor changed",
            "ou_lark_task_owner",
            "2026-08-15T09:00:00Z",
            "local-lark-secret",
        ):
            self.assertNotIn(raw_value, encoded_connector_result)
            self.assertNotIn(raw_value, encoded_audit)

        self.assertIn("run_waiting", [event["type"] for event in audit_events])
        self.assertIn("run_resumed", [event["type"] for event in audit_events])
        self.assertIn("connector_completed", [event["type"] for event in audit_events])
