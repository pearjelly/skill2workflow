import json
import subprocess
import sys
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ObservabilityDashboardTests(TestCase):
    def test_dashboard_is_importable_and_uses_fixed_metrics(self):
        dashboard = json.loads(
            (ROOT / "examples/observability/grafana-dashboard.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(dashboard["uid"], "skill2workflow-service")
        self.assertEqual(dashboard["schemaVersion"], 39)
        self.assertEqual(len(dashboard["panels"]), 8)
        serialized = json.dumps(dashboard, ensure_ascii=False)
        for metric in (
            "skill2workflow_service_ready",
            "skill2workflow_scheduler_lease_owned",
            "skill2workflow_service_inflight_requests",
            "skill2workflow_schedule_dispatches",
            "skill2workflow_http_requests_total",
            "skill2workflow_runs",
            "skill2workflow_service_uptime_seconds",
        ):
            self.assertIn(metric, serialized)
        for forbidden in ("Authorization", "Bearer ", "customer", "run_id", "workflow_id"):
            self.assertNotIn(forbidden.lower(), serialized.lower())

    def test_dashboard_guide_defines_import_and_read_only_boundary(self):
        guide = (ROOT / "docs/grafana-dashboard.md").read_text(encoding="utf-8")
        self.assertIn("grafana-dashboard.json", guide)
        self.assertIn("Prometheus data source", guide)
        self.assertIn("read-only views", guide)
        self.assertIn("scripts/observability_dashboard_smoke.py", guide)

    def test_dashboard_smoke_produces_passing_evidence(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/observability_dashboard_smoke.py")],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(evidence["panel_count"], 8)
        self.assertTrue(all(evidence["checks"].values()))
