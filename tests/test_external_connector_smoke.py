import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.external_connector_smoke import run_external_connector_smoke


class ExternalConnectorSmokeTests(TestCase):
    def test_external_connector_smoke_runs_explicit_local_fixture(self):
        repo_root = Path(__file__).resolve().parents[1]

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "external-connector"
            result = run_external_connector_smoke(repo_root=repo_root, work_dir=work_dir, reset=True)

            workflow_path = Path(result["artifacts"]["workflow"])
            run_path = Path(result["artifacts"]["run"])
            audit_path = Path(result["artifacts"]["audit"])
            snapshot_path = Path(result["artifacts"]["snapshot"])
            self.assertTrue(workflow_path.exists())
            self.assertTrue(run_path.exists())
            self.assertTrue(audit_path.exists())
            self.assertTrue(snapshot_path.exists())
            audit_events = json.loads(audit_path.read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["default_connector_ids"], ["manual", "http"])
        self.assertEqual(result["connector_ids"], ["manual", "http", "local_echo"])
        self.assertEqual(result["workflow_id"], "workflow_external_connector_smoke")
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["connector_summary"]["credential_handles"], ["demo_api_token"])
        self.assertEqual(result["connector_summary"]["input_mapping_keys"], ["customer_id"])
        self.assertEqual(result["snapshot_summary"]["run_status_counts"], {"completed": 1})
        self.assertEqual(result["snapshot_summary"]["connector_count"], 3)
        self.assertNotIn("local-secret-value", json.dumps(result))
        self.assertNotIn("customer_123", json.dumps(audit_events))
