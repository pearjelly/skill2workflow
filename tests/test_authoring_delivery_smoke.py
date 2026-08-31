import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.authoring_delivery_smoke import run_authoring_delivery_smoke


class AuthoringDeliverySmokeTests(TestCase):
    def test_runs_the_local_authoring_to_controlled_runtime_journey(self):
        with TemporaryDirectory() as temporary:
            work_dir = Path(temporary) / "authoring-delivery"
            result = run_authoring_delivery_smoke(work_dir=work_dir, reset=True)
            bundle_path = Path(result["artifacts"]["bundle"])
            run_path = Path(result["artifacts"]["run"])
            audit_path = Path(result["artifacts"]["audit"])
            snapshot_path = Path(result["artifacts"]["snapshot"])
            audit_events = json.loads(audit_path.read_text(encoding="utf-8"))
            bundle_exists = bundle_path.is_file()
            run_exists = run_path.is_file()
            snapshot_exists = snapshot_path.is_file()

        self.assertEqual(
            result["schema_version"],
            "skill2workflow-authoring-delivery-evidence-0.1.0",
        )
        self.assertEqual(result["status"], "passed")
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["initial_run_status"], "waiting")
        self.assertEqual(result["final_run_status"], "completed")
        self.assertTrue(bundle_exists)
        self.assertTrue(run_exists)
        self.assertTrue(snapshot_exists)
        self.assertIn("run_waiting", [event["type"] for event in audit_events])
        self.assertIn("run_completed", [event["type"] for event in audit_events])
        self.assertNotIn("private authoring delivery instruction", json.dumps(result))
        self.assertNotIn("private authoring delivery instruction", json.dumps(audit_events))
