import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.demo import run_demo_bootstrap


class DemoBootstrapTests(TestCase):
    def test_demo_bootstrap_generates_repeatable_local_onboarding_artifacts(self):
        repo_root = Path(__file__).resolve().parents[1]

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "demo"
            result = run_demo_bootstrap(repo_root=repo_root, work_dir=work_dir, reset=True)

            workflow_path = Path(result["artifacts"]["workflow"])
            litegraph_path = Path(result["artifacts"]["litegraph"])
            snapshot_path = Path(result["artifacts"]["snapshot"])
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

            self.assertTrue(result["ok"])
            self.assertEqual(result["workflow_id"], "workflow_approval_flow")
            self.assertEqual(result["workflow_version"], "0.1.0")
            self.assertEqual(result["run_status"], "completed")
            self.assertTrue(workflow_path.exists())
            self.assertTrue(litegraph_path.exists())
            self.assertTrue(snapshot_path.exists())
            self.assertEqual(snapshot["summary"]["workflow_count"], 1)
            self.assertEqual(snapshot["summary"]["run_count"], 1)
            self.assertEqual(snapshot["summary"]["run_status_counts"], {"completed": 1})
            self.assertIn("operator_insights", snapshot)
            self.assertEqual(result["commands"]["ui_url"], "http://localhost:4173/web/control.html")

    def test_demo_bootstrap_reset_replaces_previous_demo_state(self):
        repo_root = Path(__file__).resolve().parents[1]

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "demo"
            work_dir.mkdir()
            stale_file = work_dir / "stale.txt"
            stale_file.write_text("old", encoding="utf-8")

            run_demo_bootstrap(repo_root=repo_root, work_dir=work_dir, reset=True)

            self.assertFalse(stale_file.exists())
            self.assertTrue((work_dir / "artifacts" / "workflow.json").exists())
