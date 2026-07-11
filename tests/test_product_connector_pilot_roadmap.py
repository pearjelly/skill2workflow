from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ProductConnectorPilotRoadmapTests(TestCase):
    def test_loop_37_product_connector_pilot_is_scoped(self):
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Active loop: Loop 39, Scoped Live Lark Task Connector", roadmap)
        self.assertIn("| Loop 36: First Product Connector Package Smoke | Complete |", roadmap)
        self.assertIn("| Loop 37: Product Connector Pilot Scenario | Complete |", roadmap)
        self.assertIn("| Loop 38: Live Connector Readiness Review | Complete |", roadmap)
        self.assertIn("| Loop 39: Scoped Live Lark Task Connector | Next |", roadmap)

        self.assertIn("sales renewal risk workflow", roadmap)
        self.assertIn("manual control gate", roadmap)
        self.assertIn(
            "python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot",
            roadmap,
        )
        self.assertIn("Loop 38 approved only scoped live `create_task` work", roadmap)
        self.assertIn("Credential handling and audit redaction rules are explicit", roadmap)
        self.assertIn("feature flag or equivalent explicit opt-in", roadmap)
