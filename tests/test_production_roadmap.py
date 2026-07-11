from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ProductionRoadmapTests(TestCase):
    def test_roadmap_uses_a_rolling_production_readiness_path(self):
        roadmap = _read("ROADMAP.md")

        headings = [
            "## Product Direction",
            "## Status At A Glance",
            "## Production Readiness Path",
            "## Active Loop",
            "## Rolling Loop Queue",
            "## Capability Baseline",
            "## Delivery History",
            "## Release Direction",
            "## Deferred Work",
            "## Roadmap Rules",
        ]
        positions = [roadmap.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))

        self.assertIn("self-hosted, single-tenant workflow runtime for one team", roadmap)
        self.assertIn("- Current maturity: Local Evaluation", roadmap)
        self.assertIn("- Active loop: Loop 39, Scoped Live Lark Task Connector", roadmap)
        self.assertIn("- Next maturity gate: Controlled Live Pilot", roadmap)

        self.assertIn("### Local Evaluation", roadmap)
        self.assertIn("**Status:** Achieved.", roadmap)
        self.assertIn("### Controlled Live Pilot", roadmap)
        self.assertIn("**Target loops:** 39-40.", roadmap)
        self.assertIn("### Self-hosted Beta", roadmap)
        self.assertIn("**Target loops:** 41-43.", roadmap)
        self.assertIn("### Production Baseline", roadmap)
        self.assertIn("**Status:** Directional; no loop numbers assigned.", roadmap)

        self.assertIn(
            "| Loop 40: Controlled Live Connector Pilot | Candidate |",
            roadmap,
        )
        self.assertIn(
            "| Loop 41: Self-hosted Runtime Service Boundary | Candidate |",
            roadmap,
        )
        self.assertIn(
            "| Loop 42: Authenticated Ingress And Production Credentials | Candidate |",
            roadmap,
        )
        self.assertIn(
            "| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Candidate |",
            roadmap,
        )

        self.assertIn("SQLite is the minimum production persistence baseline", roadmap)
        self.assertIn("single-instance and single-tenant", roadmap)
        self.assertIn("must not claim exactly-once execution", roadmap)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
