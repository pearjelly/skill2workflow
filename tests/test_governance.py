from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
SECURITY_REPORT_URL = (
    "https://github.com/pearjelly/skill2workflow/security/advisories/new"
)
SECURITY_POLICY_URL = (
    "https://github.com/pearjelly/skill2workflow/blob/main/SECURITY.md"
)


class OpenSourceGovernanceContractTests(TestCase):
    def test_security_policy_defines_private_reporting_and_product_boundary(self):
        policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        normalized = " ".join(policy.split())

        self.assertIn(SECURITY_REPORT_URL, normalized)
        self.assertIn("Do not open a public issue", normalized)
        self.assertIn("Self-hosted Beta", normalized)
        self.assertIn("single-tenant", normalized)
        self.assertIn("security response targets", normalized)
        self.assertIn("not service-level guarantees", normalized)
        self.assertIn("credentials", normalized)
        self.assertIn("customer data", normalized)

    def test_support_and_conduct_docs_define_maintainer_boundaries(self):
        support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
        conduct = (ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")

        self.assertIn("No emergency support", support)
        self.assertIn("SECURITY.md", support)
        self.assertIn("Self-hosted Beta", support)
        self.assertIn("Our Standards", conduct)
        self.assertIn("Enforcement", conduct)
        self.assertIn("detail-free moderation request", conduct)

    def test_issue_configuration_routes_security_away_from_public_forms(self):
        config = (
            ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"
        ).read_text(encoding="utf-8")
        bug = (
            ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml"
        ).read_text(encoding="utf-8")
        feature = (
            ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("blank_issues_enabled: false", config)
        self.assertIn(SECURITY_POLICY_URL, config)
        self.assertIn("Do not report security vulnerabilities", bug)
        for area in (
            "Runtime Service / Ingress",
            "Scheduling",
            "Backup / Migration / Retention",
            "Observability",
        ):
            self.assertIn(area, bug)
            self.assertIn(area, feature)

    def test_pull_request_template_requires_evidence_and_safety_review(self):
        template = (
            ROOT / ".github" / "pull_request_template.md"
        ).read_text(encoding="utf-8")

        for heading in (
            "## Problem and outcome",
            "## Verification",
            "## Compatibility and migration",
            "## Security and privacy",
        ):
            self.assertIn(heading, template)
        self.assertIn("Workflow DSL remains authoritative", template)
        self.assertIn("No secrets, credentials, or customer data", template)

    def test_contributor_entry_points_link_governance_docs(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

        for name in (
            "SECURITY.md",
            "SUPPORT.md",
            "CODE_OF_CONDUCT.md",
            "GOVERNANCE.md",
        ):
            self.assertIn(name, readme)
            self.assertIn(name, contributing)

    def test_governance_matches_the_current_maintainer_led_model(self):
        governance = (ROOT / "GOVERNANCE.md").read_text(encoding="utf-8")
        normalized = " ".join(governance.split())

        for phrase in (
            "@pearjelly",
            "single active maintainer",
            "public pull request",
            "Workflow DSL",
            "Roadmap",
            "private security",
            "version and release",
            "CODEOWNERS is review routing, not authorization",
            "Self-hosted Beta",
        ):
            self.assertIn(phrase, normalized)

    def test_codeowners_routes_default_and_critical_boundary_review(self):
        codeowners = (ROOT / ".github" / "CODEOWNERS").read_text(
            encoding="utf-8"
        )

        for rule in (
            "* @pearjelly",
            "/.github/ @pearjelly",
            "/LICENSE @pearjelly",
            "/SECURITY.md @pearjelly",
            "/pyproject.toml @pearjelly",
            "/schemas/ @pearjelly",
            "/src/skill2workflow/ @pearjelly",
        ):
            self.assertIn(rule, codeowners)
