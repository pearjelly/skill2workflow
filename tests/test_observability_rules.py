import json
import subprocess
import sys
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ObservabilityRulesTests(TestCase):
    def test_alert_guide_defines_operator_boundary_and_verification(self):
        guide = (ROOT / "docs/prometheus-alerts.md").read_text(encoding="utf-8")
        self.assertIn("prometheus-alerts.yml", guide)
        self.assertIn("promtool check rules", guide)
        self.assertIn("do not cancel runs", guide)
        self.assertIn("change service lifecycle state", guide)
        self.assertIn("scripts/observability_rules_smoke.py", guide)

    def test_prometheus_rule_pack_is_fixed_and_value_free(self):
        rules = (ROOT / "examples/observability/prometheus-alerts.yml").read_text(
            encoding="utf-8"
        )
        for alert in (
            "Skill2WorkflowServiceNotReady",
            "Skill2WorkflowSchedulerLeaseLost",
            "Skill2WorkflowUncertainDispatch",
            "Skill2WorkflowBusinessRequestSaturation",
            "Skill2WorkflowHttp5xxResponses",
        ):
            self.assertIn(f"alert: {alert}", rules)
        self.assertEqual(rules.count("- alert:"), 5)
        self.assertIn('status="uncertain"', rules)
        self.assertIn('status_class="5xx"', rules)
        for forbidden in ("Authorization", "Bearer ", "customer", "run_id"):
            self.assertNotIn(forbidden.lower(), rules.lower())

    def test_rule_smoke_produces_passing_value_free_evidence(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/observability_rules_smoke.py")],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(evidence["alert_count"], 5)
        self.assertTrue(all(evidence["checks"].values()))
