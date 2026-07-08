import json
from pathlib import Path
from unittest import TestCase

from skill2workflow.connectors import ConnectorExecutionError, ConnectorRuntime, validate_connector_manifest
from skill2workflow.credentials import StaticCredentialProvider
from skill2workflow.external_connectors import load_external_connector


ROOT = Path(__file__).resolve().parents[1]


class LarkTaskConnectorTests(TestCase):
    def test_lark_task_manifest_is_explicit_external_connector(self):
        connector = _load_lark_task_connector()

        self.assertEqual(validate_connector_manifest(connector.manifest), [])
        self.assertEqual(connector.manifest["id"], "lark_task")
        self.assertEqual(connector.manifest["kind"], "lark_task")
        self.assertEqual(connector.manifest["execution_contract"]["mode"], "external")
        self.assertEqual(
            connector.manifest["execution_contract"]["entrypoint"],
            "examples/connectors/lark_task_connector.py:execute",
        )
        self.assertEqual([manifest["id"] for manifest in ConnectorRuntime().list_connectors()], ["manual", "http"])
        self.assertEqual(
            [manifest["id"] for manifest in ConnectorRuntime([connector]).list_connectors()],
            ["manual", "http", "lark_task"],
        )

    def test_lark_task_dry_run_returns_compact_metadata_without_payload_values(self):
        runtime = ConnectorRuntime([_load_lark_task_connector()])

        result = runtime.execute_connector(
            _lark_task_node(),
            credential_provider=StaticCredentialProvider({"lark_bot_access_token": "local-lark-secret"}),
            context={
                "input": {
                    "title": "Renewal risk follow-up",
                    "description": "Customer ACME needs executive review",
                    "assignee_open_id": "ou_123456",
                    "due_at": "2026-07-09T09:00:00Z",
                }
            },
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["connector"], {"id": "lark_task", "kind": "lark_task"})
        self.assertEqual(result["credentials"], {"status": "resolved", "handles": ["lark_bot_access_token"]})
        self.assertEqual(
            result["input_mapping"],
            {"status": "applied", "input_keys": ["assignee_open_id", "description", "due_at", "title"]},
        )
        self.assertEqual(
            result["audit"],
            {
                "operation": "create_task",
                "mode": "dry_run",
                "task_title_present": True,
                "task_description_present": True,
                "assignee_present": True,
                "due_at_present": True,
            },
        )
        self.assertEqual(result["output"]["operation"], "create_task")
        self.assertEqual(result["output"]["mode"], "dry_run")
        self.assertTrue(result["output"]["task_title_present"])

        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("local-lark-secret", encoded)
        self.assertNotIn("Renewal risk follow-up", encoded)
        self.assertNotIn("Customer ACME needs executive review", encoded)
        self.assertNotIn("ou_123456", encoded)
        self.assertNotIn("2026-07-09T09:00:00Z", encoded)

    def test_lark_task_rejects_live_mode_and_missing_credentials(self):
        runtime = ConnectorRuntime([_load_lark_task_connector()])

        with self.assertRaisesRegex(ConnectorExecutionError, "lark_task connector only supports mode dry_run"):
            runtime.execute_connector(_lark_task_node(mode="live"))

        with self.assertRaisesRegex(ConnectorExecutionError, "credential handle not found: lark_bot_access_token"):
            runtime.execute_connector(_lark_task_node(), context={"input": {"title": "Task"}})


def _load_lark_task_connector():
    return load_external_connector(ROOT / "examples" / "connectors" / "lark_task_connector.py")


def _lark_task_node(operation="create_task", mode="dry_run"):
    return {
        "id": "create_lark_task",
        "type": "tool_call",
        "connector": {
            "id": "lark_task",
            "kind": "lark_task",
            "operation": operation,
            "mode": mode,
            "request": {
                "body": {"source": "unit-test"},
                "input_mapping": [
                    {"from": "/input/title", "to": "/body/title", "required": True},
                    {"from": "/input/description", "to": "/body/description", "required": False},
                    {"from": "/input/assignee_open_id", "to": "/body/assignee_open_id", "required": False},
                    {"from": "/input/due_at", "to": "/body/due_at", "required": False},
                ],
            },
            "credentials": [
                {
                    "target": "header",
                    "name": "Authorization",
                    "handle": "lark_bot_access_token",
                    "prefix": "Bearer ",
                }
            ],
        },
    }
