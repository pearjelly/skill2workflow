from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ProductConnectorPilotRoadmapTests(TestCase):
    def test_loop_40_controlled_pilot_is_complete_and_scoped(self):
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Active loop: None; Loop 138 is complete with bounded readiness registry checks", roadmap)
        self.assertIn("| Loop 36: First Product Connector Package Smoke | Complete |", roadmap)
        self.assertIn("| Loop 37: Product Connector Pilot Scenario | Complete |", roadmap)
        self.assertIn("| Loop 38: Live Connector Readiness Review | Complete |", roadmap)
        self.assertIn("| Loop 39: Scoped Live Lark Task Connector | Complete |", roadmap)
        self.assertIn("| Loop 40: Controlled Live Connector Pilot | Complete |", roadmap)
        self.assertIn("| Loop 41: Self-hosted Runtime Service Boundary | Complete |", roadmap)
        self.assertIn("docs/pilot-evidence/loop-40/", roadmap)
        self.assertIn("Live behavior remains limited to the fixed `create_task` action.", roadmap)
        self.assertIn("one scoped live connector validation", roadmap)
        self.assertIn("not the controlled real-team business-workflow pilot required for Loop 40", roadmap)
