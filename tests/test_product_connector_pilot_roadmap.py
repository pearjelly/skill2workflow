from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ProductConnectorPilotRoadmapTests(TestCase):
    def test_loop_37_product_connector_pilot_is_scoped(self):
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Active loop: Loop 37, Product Connector Pilot Scenario", roadmap)
        self.assertIn("| Loop 36: First Product Connector Package Smoke | Complete |", roadmap)
        self.assertIn("| Loop 37: Product Connector Pilot Scenario | Next |", roadmap)
        self.assertIn("| Loop 38: Live Connector Readiness Review | Candidate |", roadmap)

        self.assertIn("sales renewal risk follow-up", roadmap)
        self.assertIn("controlled decision point", roadmap)
        self.assertIn(
            "python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot",
            roadmap,
        )
        self.assertIn("do not call the live Lark/Feishu API", roadmap)
        self.assertIn("Credential values remain outside Workflow DSL", roadmap)
