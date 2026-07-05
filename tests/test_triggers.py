from unittest import TestCase

from skill2workflow.triggers import (
    normalize_trigger_request,
    trigger_audit_fields,
    trigger_response,
    trigger_run_context,
)


class TriggerTests(TestCase):
    def test_normalize_trigger_request_accepts_local_envelope(self):
        normalized = normalize_trigger_request(
            {
                "workflow_id": "workflow_control",
                "version": "1.0.0",
                "source": "local-test",
                "idempotency_key": "demo-1",
                "input": {
                    "customer_id": "customer_123",
                    "priority": "high",
                },
            }
        )

        self.assertTrue(normalized["trigger_id"].startswith("trigger_"))
        self.assertEqual(normalized["workflow_id"], "workflow_control")
        self.assertEqual(normalized["version"], "1.0.0")
        self.assertEqual(normalized["source"], "local-test")
        self.assertEqual(normalized["idempotency_key"], "demo-1")
        self.assertEqual(normalized["input_keys"], ["customer_id", "priority"])
        self.assertEqual(
            normalized["input"],
            {
                "customer_id": "customer_123",
                "priority": "high",
            },
        )

    def test_normalize_trigger_request_uses_safe_defaults(self):
        normalized = normalize_trigger_request({"workflow_id": "workflow_control", "version": "1.0.0"})

        self.assertEqual(normalized["source"], "local")
        self.assertEqual(normalized["idempotency_key"], "")
        self.assertEqual(normalized["input_keys"], [])

    def test_normalize_trigger_request_rejects_invalid_envelopes(self):
        with self.assertRaisesRegex(ValueError, "workflow_id is required"):
            normalize_trigger_request({"version": "1.0.0"})
        with self.assertRaisesRegex(ValueError, "version is required"):
            normalize_trigger_request({"workflow_id": "workflow_control"})
        with self.assertRaisesRegex(ValueError, "trigger input must be a JSON object"):
            normalize_trigger_request({"workflow_id": "workflow_control", "version": "1.0.0", "input": []})
        with self.assertRaisesRegex(ValueError, "trigger input must be JSON serializable"):
            normalize_trigger_request(
                {
                    "workflow_id": "workflow_control",
                    "version": "1.0.0",
                    "input": {"not_json": object()},
                }
            )

    def test_trigger_audit_fields_and_response_keep_compact_metadata(self):
        trigger = normalize_trigger_request(
            {
                "workflow_id": "workflow_control",
                "version": "1.0.0",
                "source": "local-test",
                "idempotency_key": "demo-1",
                "input": {"customer_id": "customer_123"},
            }
        )
        state = {
            "run_id": "run_123",
            "status": "completed",
            "workflow_id": "workflow_control",
            "workflow_version": "1.0.0",
        }

        self.assertEqual(
            trigger_audit_fields(trigger),
            {
                "trigger_id": trigger["trigger_id"],
                "trigger_source": "local-test",
                "idempotency_key": "demo-1",
                "input_keys": ["customer_id"],
            },
        )
        self.assertNotIn("input", trigger_audit_fields(trigger))
        self.assertNotIn("input", trigger_response(trigger, state))
        self.assertEqual(
            trigger_response(trigger, state),
            {
                "trigger_id": trigger["trigger_id"],
                "workflow_id": "workflow_control",
                "workflow_version": "1.0.0",
                "run_id": "run_123",
                "run_status": "completed",
                "source": "local-test",
                "idempotency_key": "demo-1",
                "input_keys": ["customer_id"],
            },
        )

    def test_trigger_run_context_carries_input_without_audit_leakage(self):
        trigger = normalize_trigger_request(
            {
                "workflow_id": "workflow_control",
                "version": "1.0.0",
                "source": "local-test",
                "idempotency_key": "demo-1",
                "input": {
                    "customer_id": "customer_123",
                    "priority": "high",
                },
            }
        )

        context = trigger_run_context(trigger)

        self.assertEqual(
            context,
            {
                "trigger": {
                    "trigger_id": trigger["trigger_id"],
                    "source": "local-test",
                    "idempotency_key": "demo-1",
                    "input_keys": ["customer_id", "priority"],
                },
                "input": {
                    "customer_id": "customer_123",
                    "priority": "high",
                },
            },
        )
        self.assertNotIn("input", trigger_audit_fields(trigger))
