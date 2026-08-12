from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ReadmeFirstRunContractTests(TestCase):
    def test_readme_surfaces_public_project_entry_points_before_visuals(self):
        opening = (ROOT / "README.md").read_text(encoding="utf-8").split(
            "## Visual Overview", 1
        )[0]

        for link in (
            "[Documentation](docs/)",
            "[Changelog](CHANGELOG.md)",
            "[Security](SECURITY.md)",
            "[Support](SUPPORT.md)",
            "[Contributing](CONTRIBUTING.md)",
            "[Code of Conduct](CODE_OF_CONDUCT.md)",
        ):
            self.assertIn(link, opening)

    def test_readme_leads_with_current_product_and_safety_boundary(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        opening = readme.split("## Visual Overview", 1)[0]
        normalized = " ".join(opening.split())

        self.assertIn("Self-hosted Beta", normalized)
        self.assertIn("single-tenant", normalized)
        self.assertIn(
            "Workflow DSL remains the execution source of truth", normalized
        )
        self.assertIn("does not claim exactly-once execution", normalized)
        self.assertNotIn("does not include Node.js or npm", normalized)
        self.assertNotIn("starting with a small executable harness", normalized)
        self.assertNotIn("first executable slice", normalized)

    def test_readme_puts_a_runnable_controlled_journey_before_visuals(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        opening = readme.split("## Visual Overview", 1)[0]

        self.assertIn("## Fastest Controlled Journey", opening)
        self.assertIn("python -m pip install .", opening)
        self.assertIn("skill2workflow quickstart", opening)
        self.assertIn("docs/quickstart.md", opening)
        self.assertLess(
            readme.index("## Fastest Controlled Journey"),
            readme.index("## Visual Overview"),
        )

    def test_readme_core_loop_matches_the_current_runtime(self):
        opening = (ROOT / "README.md").read_text(encoding="utf-8").split(
            "## Visual Overview", 1
        )[0]
        normalized = " ".join(opening.split())

        self.assertIn(
            "SKILL.md -> Skill IR -> Workflow DSL -> Immutable publication",
            normalized,
        )
        self.assertIn(
            "Authenticated service -> Durable run -> Human decision -> Audit / recovery",
            normalized,
        )
