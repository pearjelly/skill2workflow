import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.pilot_scenarios import run_pilot_scenario_pack


class PilotScenarioPackTests(TestCase):
    def test_pilot_scenario_pack_runs_multiple_local_scenarios(self):
        repo_root = Path(__file__).resolve().parents[1]

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot-pack"
            result = run_pilot_scenario_pack(repo_root=repo_root, work_dir=work_dir, reset=True)

            index_path = Path(result["artifacts"]["index"])
            self.assertTrue(index_path.exists())
            pack_index = json.loads(index_path.read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["scenario_count"], 3)
        self.assertEqual(
            [item["id"] for item in result["scenarios"]],
            ["customer_support", "sales_renewal", "risk_exception"],
        )
        self.assertTrue(all(item["run_status"] == "completed" for item in result["scenarios"]))
        self.assertTrue(all(item["connector_request"]["mapped_body_matched"] for item in result["scenarios"]))
        self.assertTrue(
            all(item["snapshot_summary"]["run_status_counts"] == {"completed": 1} for item in result["scenarios"])
        )
        self.assertNotIn("local-secret-value", json.dumps(result))
        self.assertEqual(pack_index["scenario_count"], 3)
