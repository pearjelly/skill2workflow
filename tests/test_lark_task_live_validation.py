import json
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.lark_task_live_validation import run_lark_task_live_validation


ROOT = Path(__file__).resolve().parents[1]


class LarkTaskLiveValidationTests(TestCase):
    def test_live_validation_requires_confirmation_switch_token_and_identity(self):
        cases = [
            ({}, False, "run_validation", "ou_test", "live validation requires --confirm-live-create"),
            ({"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, True, "run_validation", "ou_test", "LARK_BOT_ACCESS_TOKEN is required"),
            ({"LARK_BOT_ACCESS_TOKEN": "secret"}, True, "run_validation", "ou_test", "SKILL2WORKFLOW_LARK_TASK_LIVE=1 is required"),
            ({"SKILL2WORKFLOW_LARK_TASK_LIVE": "1", "LARK_BOT_ACCESS_TOKEN": "secret"}, True, "", "ou_test", "validation run id is required"),
            ({"SKILL2WORKFLOW_LARK_TASK_LIVE": "1", "LARK_BOT_ACCESS_TOKEN": "secret"}, True, "run_validation", "", "assignee open id is required"),
        ]

        for environment, confirmed, run_id, assignee, expected in cases:
            with self.subTest(expected=expected), patch.dict(os.environ, environment, clear=True):
                with self.assertRaisesRegex(ValueError, expected):
                    run_lark_task_live_validation(
                        ROOT,
                        title="Validation title",
                        description="Validation description",
                        assignee_open_id=assignee,
                        validation_run_id=run_id,
                        confirmed=confirmed,
                        transport=lambda request, timeout: None,
                    )

    def test_live_validation_returns_only_compact_metadata(self):
        transport = _FakeTransport()
        environment = {
            "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
            "LARK_BOT_ACCESS_TOKEN": "live-validation-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            result = run_lark_task_live_validation(
                ROOT,
                title="Validation title",
                description="Validation description",
                assignee_open_id="ou_validation",
                validation_run_id="run_validation",
                confirmed=True,
                transport=transport,
            )

        self.assertEqual(
            result,
            {
                "ok": True,
                "connector_id": "lark_task",
                "operation": "create_task",
                "mode": "live",
                "credential_status": "resolved",
                "idempotency_key_present": True,
                "provider_status": "completed",
                "lark_task_id_present": True,
                "assignee_present": True,
            },
        )
        encoded = json.dumps(result)
        for forbidden in (
            "live-validation-secret",
            "Validation title",
            "Validation description",
            "ou_validation",
            "task-guid-must-not-leak",
        ):
            self.assertNotIn(forbidden, encoded)


class _FakeResponse:
    status = 200

    def read(self):
        return json.dumps(
            {"code": 0, "msg": "success", "data": {"task": {"guid": "task-guid-must-not-leak"}}}
        ).encode("utf-8")

    def close(self):
        return None


class _FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        return _FakeResponse()
