from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class HumanApprovalDocumentationTests(TestCase):
    def test_human_approval_guide_publishes_the_narrow_service_contract(self):
        guide = (ROOT / "docs" / "human-approval.md").read_text(encoding="utf-8")

        for fragment in (
            "POST /runs/{run_id}/resume",
            'Authorization: Bearer <service-ingress-token>',
            '{"approved": true}',
            "exactly one JSON object",
            "Extra fields",
            "401",
            "404",
            "409",
            "LocalControlPlane.resume_published_run",
            "run_resumed",
            "does not implement multi-user RBAC",
        ):
            self.assertIn(fragment, guide)

        self.assertNotIn("tenant_access_token", guide)
        self.assertNotIn("LARK_BOT_ACCESS_TOKEN", guide)

    def test_current_docs_cross_link_the_stable_human_gate_route(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        service = (ROOT / "docs" / "service.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("docs/human-approval.md", readme)
        self.assertIn("/runs/{run_id}/resume", service)
        self.assertIn("human-approval.md", stability)
        self.assertIn("exact boolean body", changelog)
