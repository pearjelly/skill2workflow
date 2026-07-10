from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class LiveConnectorReadinessTests(TestCase):
    def test_lark_live_connector_readiness_decision_is_documented(self):
        decision = _read("docs/lark-live-connector-readiness.md")
        roadmap = _read("ROADMAP.md")
        connectors = _read("docs/connectors.md")

        self.assertIn("# Lark/Feishu Live Connector Readiness Review", decision)
        self.assertIn(
            "Decision: proceed to a scoped live `create_task` implementation in Loop 39",
            decision,
        )
        self.assertIn("## Evidence From Prior Loops", decision)
        self.assertIn("Loop 36 package-level dry-run smoke", decision)
        self.assertIn("Loop 37 pilot-workflow dry-run smoke", decision)
        self.assertIn("python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot", decision)

        self.assertIn("## Approved Live Action Surface", decision)
        self.assertIn("operation: `create_task`", decision)
        self.assertIn("mode: `live`", decision)
        self.assertIn("connector id: `lark_task`", decision)
        self.assertIn("examples/connectors/lark_task_connector.py remains dry-run-only in Loop 38", decision)
        self.assertIn("No OAuth", decision)
        self.assertIn("No hosted callback", decision)
        self.assertIn("No automatic connector discovery", decision)

        self.assertIn("## Credential Model", decision)
        self.assertIn("credential handle: `lark_bot_access_token`", decision)
        self.assertIn("resolved only through the credential provider", decision)
        self.assertIn("not Workflow DSL", decision)
        self.assertIn("not trigger input", decision)
        self.assertIn("not run state", decision)
        self.assertIn("not audit events", decision)

        self.assertIn("## Idempotency And Duplicate Prevention", decision)
        self.assertIn("idempotency key", decision)
        self.assertIn("workflow_id + version + run_id + node_id", decision)
        self.assertIn("duplicate task creation", decision)
        self.assertIn("safe failure", decision)

        self.assertIn("## Failure Modes", decision)
        self.assertIn("401 or 403", decision)
        self.assertIn("rate limit", decision)
        self.assertIn("network timeout", decision)
        self.assertIn("validation error", decision)
        self.assertIn("failed connector result", decision)
        self.assertIn("without raw response payload leakage", decision)

        self.assertIn("## Audit Redaction", decision)
        self.assertIn("task_title_present", decision)
        self.assertIn("task_description_present", decision)
        self.assertIn("assignee_present", decision)
        self.assertIn("due_at_present", decision)
        self.assertIn("lark_task_id_present", decision)
        self.assertIn("credential_handles", decision)
        self.assertIn("raw task values", decision)
        self.assertIn("resolved credential values", decision)

        self.assertIn("## Local Test Strategy", decision)
        self.assertIn("fake Lark HTTP receiver", decision)
        self.assertIn("no live network in CI", decision)
        self.assertIn("mode `dry_run` remains the default", decision)

        self.assertIn("## Rollback Boundaries", decision)
        self.assertIn("feature flag", decision)
        self.assertIn("default remains dry-run", decision)
        self.assertIn("revert Loop 39 without changing Workflow DSL compatibility", decision)

        self.assertIn("docs/lark-live-connector-readiness.md", connectors)
        self.assertIn("Loop 38 readiness review approved only a scoped live `create_task` follow-up", connectors)

        self.assertIn("| Loop 38: Live Connector Readiness Review | Complete |", roadmap)
        self.assertIn("Active loop: Loop 39, Scoped Live Lark Task Connector", roadmap)
        self.assertIn("| Loop 39: Scoped Live Lark Task Connector | Next |", roadmap)
        self.assertIn("Loop 38 approved only scoped live `create_task` work", roadmap)


def _read(path: str) -> str:
    file_path = ROOT / path
    if not file_path.exists():
        raise AssertionError(f"expected documented file to exist: {path}")
    return file_path.read_text(encoding="utf-8")
