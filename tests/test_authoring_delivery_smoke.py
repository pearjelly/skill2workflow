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
            damaged_verification_path = Path(
                result["artifacts"]["damaged_authoring_verification"]
            )
            repair_path = Path(result["artifacts"]["authoring_repair"])
            run_path = Path(result["artifacts"]["run"])
            audit_path = Path(result["artifacts"]["audit"])
            rejected_run_path = Path(result["artifacts"]["rejected_run"])
            rejected_audit_path = Path(result["artifacts"]["rejected_audit"])
            snapshot_path = Path(result["artifacts"]["snapshot"])
            audit_events = json.loads(audit_path.read_text(encoding="utf-8"))
            damaged_verification = json.loads(
                damaged_verification_path.read_text(encoding="utf-8")
            )
            repair = json.loads(repair_path.read_text(encoding="utf-8"))
            rejected_audit_events = json.loads(
                rejected_audit_path.read_text(encoding="utf-8")
            )
            bundle_exists = bundle_path.is_file()
            damaged_verification_exists = damaged_verification_path.is_file()
            repair_exists = repair_path.is_file()
            run_exists = run_path.is_file()
            rejected_run_exists = rejected_run_path.is_file()
            snapshot_exists = snapshot_path.is_file()

        self.assertEqual(
            result["schema_version"],
            "skill2workflow-authoring-delivery-evidence-0.1.0",
        )
        self.assertEqual(result["status"], "passed")
        self.assertTrue(all(result["checks"].values()))
        self.assertFalse(result["damaged_authoring_valid"])
        self.assertTrue(result["repaired_authoring_valid"])
        self.assertEqual(result["initial_run_status"], "waiting")
        self.assertEqual(result["final_run_status"], "completed")
        self.assertEqual(result["rejected_initial_run_status"], "waiting")
        self.assertEqual(result["rejected_final_run_status"], "failed")
        self.assertTrue(bundle_exists)
        self.assertTrue(damaged_verification_exists)
        self.assertTrue(repair_exists)
        self.assertTrue(run_exists)
        self.assertTrue(rejected_run_exists)
        self.assertTrue(snapshot_exists)
        self.assertIn("run_waiting", [event["type"] for event in audit_events])
        self.assertIn("run_completed", [event["type"] for event in audit_events])
        self.assertIn("run_waiting", [event["type"] for event in rejected_audit_events])
        self.assertIn("run_resumed", [event["type"] for event in rejected_audit_events])
        self.assertIn("run_failed", [event["type"] for event in rejected_audit_events])
        self.assertFalse(damaged_verification["valid"])
        self.assertEqual(repair["status"], "repaired")
        self.assertFalse(repair["previous_valid"])
        self.assertNotIn("private authoring delivery instruction", json.dumps(result))
        self.assertNotIn("private authoring delivery instruction", json.dumps(audit_events))
        self.assertNotIn(
            "private authoring delivery instruction", json.dumps(damaged_verification)
        )
        self.assertNotIn("private authoring delivery instruction", json.dumps(repair))
        self.assertNotIn(
            "private authoring delivery instruction", json.dumps(rejected_audit_events)
        )
