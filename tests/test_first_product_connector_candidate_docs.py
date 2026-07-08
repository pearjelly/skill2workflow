from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class FirstProductConnectorCandidateDocsTests(TestCase):
    def test_loop_35_lark_task_candidate_decision_is_documented(self):
        decision = _read("docs/first-product-connector-candidate.md")
        roadmap = _read("ROADMAP.md")

        self.assertIn("# First Product Connector Candidate", decision)
        self.assertIn("Selected candidate: Lark/Feishu Task Connector", decision)
        self.assertIn("| Lark/Feishu task | Selected |", decision)
        self.assertIn("| GitHub Issues | Deferred |", decision)
        self.assertIn("| Slack message or workflow notification | Deferred |", decision)

        self.assertIn("## Minimum First Action Surface", decision)
        self.assertIn("operation: `create_task`", decision)
        self.assertIn("no live Lark API call in Loop 36", decision)

        self.assertIn("## Package Layout", decision)
        self.assertIn("examples/connectors/lark_task_connector.py", decision)
        self.assertIn("execute(binding, credential_provider=None, context=None)", decision)
        self.assertIn("load_external_connector(Path(\"examples/connectors/lark_task_connector.py\"))", decision)

        self.assertIn("## Credential Handles And Secret Boundaries", decision)
        self.assertIn("lark_bot_access_token", decision)
        self.assertIn("resolved credential values must never be returned", decision)

        self.assertIn("## Local Or Dry-Run Smoke", decision)
        self.assertIn(
            "python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector",
            decision,
        )

        self.assertIn("## Compact Audit Metadata", decision)
        self.assertIn("task_title_present", decision)
        self.assertIn("credential_handles", decision)

        self.assertIn("## Conditions Before Loop 36", decision)
        self.assertIn("No automatic discovery", decision)
        self.assertIn("No OAuth", decision)

        self.assertIn("| Loop 35: First Product Connector Candidate | Complete |", roadmap)
        self.assertIn("| Loop 36: First Product Connector Package Smoke | Next |", roadmap)
        self.assertIn("Lark/Feishu task connector", roadmap)
        self.assertIn("docs/first-product-connector-candidate.md", roadmap)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
