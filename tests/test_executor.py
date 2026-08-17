import json
import sqlite3
import threading
import urllib.error
from datetime import datetime, timedelta, timezone
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.connectors import (
    EXTERNAL_CONNECTOR_DURABLE_FAILURE,
    ConnectorExecutionError,
    ConnectorRuntime,
    ExternalConnector,
)
from skill2workflow.credentials import StaticCredentialProvider
from skill2workflow.external_connectors import load_external_connector
from skill2workflow.executor import LocalExecutor


class ExecutorTests(TestCase):
    def test_bounded_run_listing_does_not_call_unbounded_store_list(self):
        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp), storage="json")
            executor.run(_approval_workflow())
            with patch.object(
                executor.store,
                "list",
                side_effect=AssertionError("unbounded run read"),
            ):
                summaries = executor.list_runs(limit=1)

        self.assertEqual(len(summaries), 1)

    def test_workflow_timeout_includes_human_gate_wait_and_fails_on_resume(self):
        clock = _TestClock()
        workflow = _approval_workflow()
        workflow["policies"] = {"workflow_timeout_ms": 5}

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp), storage="sqlite", clock=clock)
            waiting = executor.run(workflow)
            self.assertEqual(waiting["status"], "waiting")
            self.assertEqual(waiting["execution"]["workflow_timeout_ms"], 5)
            self.assertNotEqual(waiting["execution"]["workflow_deadline_at"], "")
            clock.advance(5)
            failed = executor.resume(waiting["run_id"], approved=True)

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "workflow_timeout")
        self.assertEqual(failed["events"][-1]["error_code"], "workflow_timeout")
        self.assertEqual(failed["execution"]["workflow_deadline_at"], "")

    def test_workflow_timeout_after_connector_return_does_not_run_successor(self):
        clock = _TestClock()
        runtime = _AdvancingConnectorRuntime(clock, milliseconds=10)
        workflow = _http_connector_workflow("https://unused.invalid")
        workflow["policies"] = {"workflow_timeout_ms": 5}

        with TemporaryDirectory() as tmp:
            state = LocalExecutor(
                Path(tmp),
                connector_runtime=runtime,
                clock=clock,
            ).run(workflow)

        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["error_code"], "workflow_timeout")
        self.assertEqual(state["node_results"]["call_api"]["error_code"], "workflow_timeout")
        self.assertEqual(runtime.calls, 1)

    def test_workflow_deadline_survives_restart_before_late_resume(self):
        clock = _TestClock()
        workflow = _approval_workflow()
        workflow["policies"] = {"workflow_timeout_ms": 5}

        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            waiting = LocalExecutor(state_dir, storage="sqlite", clock=clock).run(workflow)
            clock.advance(5)
            failed = LocalExecutor(state_dir, storage="sqlite", clock=clock).resume(
                waiting["run_id"], approved=False
            )

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "workflow_timeout")
        self.assertEqual(failed["node_results"]["review"]["approved"], False)

    def test_workflow_deadline_sweeper_expires_waiting_run_without_successor(self):
        clock = _TestClock()
        workflow = _approval_workflow()
        workflow["policies"] = {"workflow_timeout_ms": 5}

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp), storage="sqlite", clock=clock)
            waiting = executor.run(workflow)
            clock.advance(5)
            expired = executor.expire_workflow_deadlines()
            failed = executor.get_run(waiting["run_id"])
            repeated = executor.expire_workflow_deadlines()

        self.assertEqual(len(expired), 1)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "workflow_timeout")
        self.assertEqual(failed["events"][-1]["source"], "deadline_sweeper")
        self.assertEqual(repeated, [])

    def test_default_timeout_fails_closed_at_a_safe_point_and_persists_fixed_error(self):
        clock = _TestClock()
        runtime = _AdvancingConnectorRuntime(clock, milliseconds=10)
        workflow = _http_connector_workflow("https://unused.invalid")
        workflow["policies"] = {"default_timeout_ms": 5}

        with TemporaryDirectory() as tmp:
            state = LocalExecutor(
                Path(tmp),
                storage="sqlite",
                connector_runtime=runtime,
                clock=clock,
            ).run(workflow)
            persisted = LocalExecutor(Path(tmp), storage="sqlite").get_run(state["run_id"])

        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["error_code"], "execution_timeout")
        self.assertEqual(state["node_results"]["call_api"]["error_code"], "execution_timeout")
        self.assertEqual(state["events"][-1]["type"], "run_failed")
        self.assertEqual(state["events"][-1]["error_code"], "execution_timeout")
        self.assertEqual(persisted["error_code"], "execution_timeout")
        self.assertEqual(persisted["execution"]["timeout_ms"], 5)
        self.assertEqual(persisted["execution"]["deadline_at"], "")
        self.assertEqual(runtime.calls, 1)

    def test_default_timeout_pauses_while_waiting_for_human_gate(self):
        clock = _TestClock()
        workflow = _approval_workflow()
        workflow["policies"] = {"default_timeout_ms": 5}

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp), clock=clock)
            waiting = executor.run(workflow)
            clock.advance(1000)
            self.assertEqual(waiting["status"], "waiting")
            self.assertEqual(waiting["execution"]["deadline_at"], "")
            completed = executor.resume(waiting["run_id"], approved=True)

        self.assertEqual(completed["status"], "completed")
        self.assertNotIn("error_code", completed)

    def test_node_timeout_fails_after_connector_return_without_successor(self):
        clock = _TestClock()
        runtime = _AdvancingConnectorRuntime(clock, milliseconds=10)
        workflow = _http_connector_workflow("https://unused.invalid")
        workflow["nodes"][1]["timeout_ms"] = 5

        with TemporaryDirectory() as tmp:
            state = LocalExecutor(
                Path(tmp),
                storage="sqlite",
                connector_runtime=runtime,
                clock=clock,
            ).run(workflow)
            persisted = LocalExecutor(Path(tmp), storage="sqlite").get_run(state["run_id"])

        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["error_code"], "node_timeout")
        self.assertEqual(state["node_results"]["call_api"]["error_code"], "node_timeout")
        self.assertEqual(state["events"][-1]["error_code"], "node_timeout")
        self.assertEqual(state["execution"]["node_deadline_at"], "")
        self.assertEqual(persisted["error_code"], "node_timeout")
        self.assertEqual(runtime.calls, 1)

    def test_node_timeout_is_paused_while_human_gate_waits(self):
        clock = _TestClock()
        workflow = _approval_workflow()
        workflow["nodes"][1]["timeout_ms"] = 5

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp), clock=clock)
            waiting = executor.run(workflow)
            clock.advance(1000)
            completed = executor.resume(waiting["run_id"], approved=True)

        self.assertEqual(waiting["status"], "waiting")
        self.assertEqual(waiting["execution"]["node_deadline_at"], "")
        self.assertEqual(completed["status"], "completed")
        self.assertNotIn("error_code", completed)

    def test_malformed_persisted_deadline_fails_closed(self):
        workflow = _approval_workflow()
        workflow["policies"] = {"default_timeout_ms": 5}

        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            executor = LocalExecutor(state_dir, storage="sqlite")
            waiting = executor.run(workflow)
            corrupted = executor.get_run(waiting["run_id"])
            corrupted["status"] = "running"
            corrupted["execution"]["started_at"] = "2026-08-13T00:00:00+00:00"
            corrupted["execution"]["deadline_at"] = "not-a-timestamp"
            executor.store.save(corrupted)

            restarted = LocalExecutor(state_dir, storage="sqlite")
            failed = restarted._drive(restarted.get_run(waiting["run_id"]))

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "execution_timeout")
        self.assertEqual(failed["execution"]["deadline_at"], "")

    def test_connector_failure_routes_to_declared_fallback_without_retrying_side_effect(self):
        workflow = _http_connector_workflow("https://unused.invalid")
        workflow["nodes"][1]["on_fallback"] = "fallback"
        workflow["nodes"].insert(
            2,
            {
                "id": "fallback",
                "type": "step",
                "title": "Fallback handling",
                "on_success": "end",
                "on_failure": "failure",
            },
        )
        workflow["edges"].extend(
            [
                {"id": "edge_call_fallback", "from": "call_api", "to": "fallback", "label": "fallback"},
                {"id": "edge_fallback_end", "from": "fallback", "to": "end", "label": "next"},
            ]
        )
        runtime = _FailingConnectorRuntime()

        with TemporaryDirectory() as tmp:
            state = LocalExecutor(Path(tmp), connector_runtime=runtime).run(workflow)

        self.assertEqual(state["status"], "completed")
        self.assertEqual(runtime.calls, 1)
        self.assertEqual(state["node_results"]["call_api"]["status"], "failed")
        self.assertEqual(state["node_results"]["call_api"]["fallback_target"], "fallback")
        self.assertEqual(state["current_node"], "end")
        self.assertEqual(
            [event["type"] for event in state["events"] if event.get("node_id") == "call_api"],
            ["node_started", "connector_started", "connector_failed", "node_failed", "node_fallback"],
        )

    def test_run_pauses_at_human_gate_and_resume_completes(self):
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {
                "id": "workflow_approval",
                "name": "approval",
                "version": "0.1.0",
                "status": "published",
            },
            "entry": "start",
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "title": "Start",
                    "on_success": "review",
                },
                {
                    "id": "review",
                    "type": "human_gate",
                    "title": "Review",
                    "on_success": "end",
                    "on_failure": "failure",
                },
                {"id": "failure", "type": "failure", "title": "Failure"},
                {"id": "end", "type": "end", "title": "End"},
            ],
            "edges": [],
        }

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            self.assertEqual(waiting["status"], "waiting")
            self.assertEqual(waiting["current_node"], "review")

            completed = executor.resume(waiting["run_id"], approved=True)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["current_node"], "end")

    def test_resume_records_human_gate_result_and_terminal_result(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            completed = executor.resume(waiting["run_id"], approved=True)

        review_result = completed["node_results"]["review"]
        self.assertEqual(review_result["status"], "approved")
        self.assertEqual(review_result["title"], "Review")
        self.assertEqual(review_result["approved"], True)
        self.assertIn("timestamp", review_result)
        self.assertEqual(completed["node_results"]["end"]["status"], "completed")
        self.assertEqual(completed["node_results"]["end"]["title"], "End")

    def test_resume_rejection_records_human_gate_result_and_fails(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            failed = executor.resume(waiting["run_id"], approved=False)

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["current_node"], "failure")
        review_result = failed["node_results"]["review"]
        self.assertEqual(review_result["status"], "rejected")
        self.assertEqual(review_result["title"], "Review")
        self.assertEqual(review_result["approved"], False)
        self.assertIn("timestamp", review_result)
        self.assertEqual(failed["node_results"]["failure"]["status"], "failed")

    def test_list_runs_returns_control_plane_summaries(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            summary = executor.list_runs()[0]
            detail = executor.get_run(waiting["run_id"])

        self.assertEqual(
            summary,
            {
                "run_id": waiting["run_id"],
                "workflow_id": "workflow_approval",
                "workflow_version": "0.1.0",
                "status": "waiting",
                "current_node": "review",
                "event_count": 3,
                "node_result_count": 1,
            },
        )
        self.assertEqual(detail["run_id"], waiting["run_id"])
        self.assertIn("workflow", detail)
        self.assertIn("events", detail)
        self.assertIn("node_results", detail)

    def test_run_persists_initial_context(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            state = executor.run(
                workflow,
                context={
                    "trigger": {
                        "trigger_id": "trigger_demo",
                        "source": "local-test",
                        "idempotency_key": "demo-1",
                        "input_keys": ["customer_id"],
                    },
                    "input": {"customer_id": "customer_123"},
                },
            )
            detail = executor.get_run(state["run_id"])

        self.assertEqual(state["context"]["input"]["customer_id"], "customer_123")
        self.assertEqual(state["context"]["trigger"]["trigger_id"], "trigger_demo")
        self.assertEqual(detail["context"]["input"]["customer_id"], "customer_123")
        self.assertEqual(detail["context"]["trigger"]["input_keys"], ["customer_id"])

    def test_sqlite_storage_persists_run_state_and_event_rows_across_instances(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            waiting = LocalExecutor(state_dir, storage="sqlite").run(workflow)

            restarted = LocalExecutor(state_dir, storage="sqlite")
            detail = restarted.get_run(waiting["run_id"])
            completed = restarted.resume(waiting["run_id"], approved=True)
            summary = restarted.list_runs()[0]

            db_path = state_dir / "runs.sqlite3"
            with closing(sqlite3.connect(db_path)) as connection, connection:
                event_rows = connection.execute(
                    "select event_type, node_id from run_events where run_id = ? order by sequence",
                    (waiting["run_id"],),
                ).fetchall()

        self.assertEqual(detail["status"], "waiting")
        self.assertEqual(detail["current_node"], "review")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["event_count"], len(event_rows))
        self.assertEqual(
            [row[0] for row in event_rows],
            [
                "node_started",
                "node_completed",
                "human_gate_waiting",
                "human_gate_resumed",
                "run_completed",
            ],
        )

    def test_http_connector_executes_request_and_records_events(self):
        server = _ConnectorTestServer()
        workflow = _http_connector_workflow(server.url)

        try:
            with TemporaryDirectory() as tmp:
                state = LocalExecutor(Path(tmp), storage="sqlite").run(workflow)

                with closing(sqlite3.connect(Path(tmp) / "runs.sqlite3")) as connection, connection:
                    event_rows = connection.execute(
                        "select event_type, node_id from run_events where run_id = ? order by sequence",
                        (state["run_id"],),
                    ).fetchall()
        finally:
            server.close()

        call_result = state["node_results"]["call_api"]
        self.assertEqual(state["status"], "completed")
        self.assertEqual(server.requests[0]["path"], "/connector")
        self.assertEqual(server.requests[0]["body"], {"account_id": "acct_123"})
        self.assertEqual(call_result["status"], "completed")
        self.assertEqual(call_result["connector"]["id"], "http")
        self.assertEqual(call_result["connector"]["kind"], "http")
        self.assertEqual(call_result["output"]["status_code"], 200)
        self.assertEqual(json.loads(call_result["output"]["body"]), {"ok": True})
        self.assertIn(("connector_started", "call_api"), event_rows)
        self.assertIn(("connector_completed", "call_api"), event_rows)

    def test_required_input_mapping_failure_uses_connector_failure_path(self):
        server = _ConnectorTestServer()
        workflow = _mapped_http_connector_workflow(server.url)

        try:
            with TemporaryDirectory() as tmp:
                state = LocalExecutor(Path(tmp)).run(workflow, context={"input": {}})
        finally:
            server.close()

        call_result = state["node_results"]["call_api"]
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["current_node"], "failure")
        self.assertEqual(server.requests, [])
        self.assertEqual(call_result["status"], "failed")
        self.assertIn("required input mapping value missing: /input/customer_id", call_result["error"])

    def test_http_connector_credentials_do_not_persist_resolved_values(self):
        server = _ConnectorTestServer()
        workflow = _credential_connector_workflow(server.url)

        try:
            with TemporaryDirectory() as tmp:
                state = LocalExecutor(
                    Path(tmp),
                    credential_provider=StaticCredentialProvider({"demo_api_token": "secret-token"}),
                ).run(workflow)
        finally:
            server.close()

        self.assertEqual(state["status"], "completed")
        self.assertEqual(server.requests[0]["headers"]["Authorization"], "Bearer secret-token")
        self.assertNotIn("secret-token", json.dumps(state["node_results"]))
        self.assertNotIn("secret-token", json.dumps(state["events"]))
        self.assertNotIn("secret-token", json.dumps(state["context"]))

    def test_http_transport_failure_persists_fixed_value_free_error(self):
        private_marker = "private-provider-detail-should-not-leak"
        workflow = _http_connector_workflow("https://provider.example/private")

        with TemporaryDirectory() as tmp:
            with patch(
                "skill2workflow.connectors._open_http_request",
                side_effect=urllib.error.URLError(private_marker),
            ):
                state = LocalExecutor(Path(tmp), storage="sqlite").run(workflow)
            persisted = LocalExecutor(Path(tmp), storage="sqlite").get_run(
                state["run_id"]
            )

        for result in (
            state["node_results"]["call_api"],
            persisted["node_results"]["call_api"],
        ):
            self.assertEqual(result["error"], "http connector request failed")
        self.assertNotIn(private_marker, json.dumps(state, ensure_ascii=False))
        self.assertNotIn(private_marker, json.dumps(persisted, ensure_ascii=False))

    def test_unexpected_external_connector_failure_persists_fixed_value_free_error(self):
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "connectors"
            / "local_echo_connector.py"
        )
        fixture = load_external_connector(fixture_path)
        private_marker = "private-provider-detail-should-not-leak"

        def execute(_binding, credential_provider=None, context=None):
            raise RuntimeError(f"provider request failed: {private_marker}")

        runtime = ConnectorRuntime([ExternalConnector(fixture.manifest, execute)])
        workflow = _http_connector_workflow("https://unused.invalid")
        workflow["nodes"][1]["connector"] = {
            "id": "local_echo",
            "kind": "local_echo",
            "request": {},
        }

        with TemporaryDirectory() as tmp:
            state = LocalExecutor(
                Path(tmp), storage="sqlite", connector_runtime=runtime
            ).run(workflow)
            persisted = LocalExecutor(Path(tmp), storage="sqlite").get_run(
                state["run_id"]
            )

        for result in (
            state["node_results"]["call_api"],
            persisted["node_results"]["call_api"],
        ):
            self.assertEqual(result["error"], EXTERNAL_CONNECTOR_DURABLE_FAILURE)
        self.assertNotIn(private_marker, json.dumps(state, ensure_ascii=False))
        self.assertNotIn(private_marker, json.dumps(persisted, ensure_ascii=False))

    def test_external_connector_error_text_is_sanitized_before_durable_persistence(self):
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "connectors"
            / "local_echo_connector.py"
        )
        fixture = load_external_connector(fixture_path)
        private_marker = "provider-response-detail-should-not-be-persisted"

        def execute(_binding, credential_provider=None, context=None):
            return {
                "status": "failed",
                "connector": {"id": "local_echo", "kind": "local_echo"},
                "error": private_marker,
                "output": {},
            }

        runtime = ConnectorRuntime([ExternalConnector(fixture.manifest, execute)])
        workflow = _http_connector_workflow("https://unused.invalid")
        workflow["nodes"][1]["connector"] = {
            "id": "local_echo",
            "kind": "local_echo",
            "request": {},
        }
        workflow["nodes"][1]["retry"] = {"max_attempts": 1}

        with TemporaryDirectory() as tmp:
            state = LocalExecutor(
                Path(tmp), storage="sqlite", connector_runtime=runtime
            ).run(workflow)
            persisted = LocalExecutor(Path(tmp), storage="sqlite").get_run(
                state["run_id"]
            )

        for snapshot in (state, persisted):
            result = snapshot["node_results"]["call_api"]
            self.assertEqual(result["error"], EXTERNAL_CONNECTOR_DURABLE_FAILURE)
            self.assertEqual(result["last_error"], EXTERNAL_CONNECTOR_DURABLE_FAILURE)
            self.assertNotIn(private_marker, json.dumps(snapshot, ensure_ascii=False))
            for event in snapshot["events"]:
                if event["type"] in {
                    "connector_failed",
                    "node_retrying",
                    "node_failed",
                }:
                    self.assertEqual(event["error"], EXTERNAL_CONNECTOR_DURABLE_FAILURE)

    def test_explicit_external_connector_error_text_is_sanitized_before_persistence(self):
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "connectors"
            / "local_echo_connector.py"
        )
        fixture = load_external_connector(fixture_path)
        private_marker = "explicit-provider-detail-should-not-be-persisted"

        def execute(_binding, credential_provider=None, context=None):
            raise ConnectorExecutionError(private_marker)

        runtime = ConnectorRuntime([ExternalConnector(fixture.manifest, execute)])
        workflow = _http_connector_workflow("https://unused.invalid")
        workflow["nodes"][1]["connector"] = {
            "id": "local_echo",
            "kind": "local_echo",
            "request": {},
        }

        with TemporaryDirectory() as tmp:
            state = LocalExecutor(
                Path(tmp), storage="sqlite", connector_runtime=runtime
            ).run(workflow)

        self.assertEqual(
            state["node_results"]["call_api"]["error"],
            EXTERNAL_CONNECTOR_DURABLE_FAILURE,
        )
        self.assertNotIn(private_marker, json.dumps(state, ensure_ascii=False))

    def test_external_connector_metadata_is_projected_before_durable_persistence(self):
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "connectors"
            / "local_echo_connector.py"
        )
        fixture = load_external_connector(fixture_path)
        private_marker = "provider-value=private-secret"

        def execute(_binding, credential_provider=None, context=None):
            return {
                "status": "completed",
                "connector": {"id": "local_echo", "kind": private_marker},
                "output": {
                    "operation": "create_task",
                    "provider_status": "completed",
                    "task_title_present": True,
                    "body_keys": ["customer_id", private_marker],
                    "provider_message": private_marker,
                },
                "audit": {
                    "operation": "create_task",
                    "provider_status": "completed",
                    "task_title_present": True,
                    "raw_provider_message": private_marker,
                },
                "input_mapping": {
                    "status": "applied",
                    "input_keys": ["customer_id", private_marker],
                    "mapped_value": private_marker,
                },
                "credentials": {
                    "status": "resolved",
                    "handles": ["safe_token_handle", private_marker],
                    "resolved_value": private_marker,
                },
            }

        runtime = ConnectorRuntime([ExternalConnector(fixture.manifest, execute)])
        workflow = _http_connector_workflow("https://unused.invalid")
        workflow["nodes"][1]["connector"] = {
            "id": "local_echo",
            "kind": "local_echo",
            "request": {},
        }

        for storage in ("json", "sqlite"):
            with self.subTest(storage=storage), TemporaryDirectory() as tmp:
                state = LocalExecutor(
                    Path(tmp), storage=storage, connector_runtime=runtime
                ).run(workflow)
                persisted = LocalExecutor(Path(tmp), storage=storage).get_run(
                    state["run_id"]
                )

            for snapshot in (state, persisted):
                encoded = json.dumps(snapshot, ensure_ascii=False)
                self.assertNotIn(private_marker, encoded)
                result = snapshot["node_results"]["call_api"]
                self.assertEqual(
                    result["connector"],
                    {"id": "local_echo", "kind": "local_echo"},
                )
                self.assertEqual(
                    result["output"],
                    {
                        "operation": "create_task",
                        "provider_status": "completed",
                        "task_title_present": True,
                        "body_keys": ["customer_id"],
                    },
                )
                self.assertEqual(
                    result["audit"],
                    {
                        "operation": "create_task",
                        "provider_status": "completed",
                        "task_title_present": True,
                    },
                )
                self.assertEqual(
                    result["input_mapping"],
                    {"status": "applied", "input_keys": ["customer_id"]},
                )
                self.assertEqual(
                    result["credentials"],
                    {"status": "resolved", "handles": ["safe_token_handle"]},
                )
                completed = [
                    event
                    for event in snapshot["events"]
                    if event["type"] in {"connector_completed", "node_completed"}
                ]
                self.assertTrue(completed)
                self.assertTrue(
                    any(
                        event.get("connector_metadata") == result["audit"]
                        for event in completed
                    )
                )

    def test_retry_policy_retries_failed_connector_and_records_recovery(self):
        server = _FlakyConnectorTestServer()
        workflow = _http_connector_workflow(server.url)
        workflow["nodes"][1]["retry"] = {"max_attempts": 1}

        try:
            with TemporaryDirectory() as tmp:
                state = LocalExecutor(Path(tmp), storage="sqlite").run(workflow)
        finally:
            server.close()

        event_types = [event["type"] for event in state["events"]]
        call_result = state["node_results"]["call_api"]
        self.assertEqual(state["status"], "completed")
        self.assertEqual(len(server.requests), 2)
        self.assertEqual(call_result["status"], "completed")
        self.assertEqual(call_result["attempts"], 2)
        self.assertEqual(call_result["max_attempts"], 1)
        self.assertIn("last_error", call_result)
        self.assertIn("node_retrying", event_types)
        self.assertIn("node_recovered", event_types)

    def test_retry_policy_applies_bounded_backoff_and_records_delay(self):
        workflow = _http_connector_workflow("https://unused.invalid")
        workflow["nodes"][1]["retry"] = {"max_attempts": 1, "backoff_ms": 250}
        runtime = _SequenceConnectorRuntime(
            [
                {"status": "failed", "error": "temporary", "output": {}},
                {"status": "completed", "output": {"ok": True}},
            ]
        )
        sleeps = []

        with TemporaryDirectory() as tmp:
            state = LocalExecutor(
                Path(tmp),
                connector_runtime=runtime,
                sleeper=sleeps.append,
            ).run(workflow)

        retry_event = next(event for event in state["events"] if event["type"] == "node_retrying")
        result = state["node_results"]["call_api"]
        self.assertEqual(sleeps, [0.25])
        self.assertEqual(retry_event["backoff_ms"], 250)
        self.assertEqual(result["backoff_ms"], 250)
        self.assertEqual(state["status"], "completed")

    def test_retry_backoff_is_resolved_from_default_and_clamped(self):
        workflow = _http_connector_workflow("https://unused.invalid")
        workflow["policies"] = {"default_retry": {"max_attempts": 1, "backoff_ms": 999999}}
        runtime = _SequenceConnectorRuntime(
            [
                {"status": "failed", "error": "temporary", "output": {}},
                {"status": "completed", "output": {"ok": True}},
            ]
        )
        sleeps = []

        with TemporaryDirectory() as tmp:
            state = LocalExecutor(
                Path(tmp),
                connector_runtime=runtime,
                sleeper=sleeps.append,
            ).run(workflow)

        self.assertEqual(sleeps, [60.0])
        self.assertEqual(state["node_results"]["call_api"]["backoff_ms"], 60000)

    def test_connector_receives_ephemeral_execution_identity_without_persisting_it(self):
        runtime = _CapturingConnectorRuntime()
        original_context = {
            "input": {"title": "Durable title"},
            "_execution": {"workflow_id": "forged"},
        }

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp), connector_runtime=runtime)
            state = executor.run(_http_connector_workflow("https://unused.invalid"), context=original_context)
            persisted = executor.get_run(state["run_id"])

        self.assertEqual(len(runtime.contexts), 1)
        self.assertEqual(
            runtime.contexts[0]["_execution"],
            {
                "workflow_id": "workflow_connector",
                "workflow_version": "0.1.0",
                "run_id": state["run_id"],
                "node_id": "call_api",
            },
        )
        self.assertEqual(runtime.contexts[0]["input"], {"title": "Durable title"})
        self.assertEqual(state["context"], original_context)
        self.assertEqual(persisted["context"], original_context)


class _TestClock:
    def __init__(self):
        self.current = datetime(2026, 8, 13, tzinfo=timezone.utc)

    def __call__(self):
        return self.current.isoformat()

    def advance(self, milliseconds):
        self.current += timedelta(milliseconds=milliseconds)


class _AdvancingConnectorRuntime:
    def __init__(self, clock, milliseconds):
        self.clock = clock
        self.milliseconds = milliseconds
        self.calls = 0

    def execute_connector(self, node, credential_provider=None, context=None):
        self.calls += 1
        self.clock.advance(self.milliseconds)
        return {
            "status": "completed",
            "connector": {"id": "http", "kind": "http"},
            "output": {"ok": True},
        }


class _CapturingConnectorRuntime:
    def __init__(self):
        self.contexts = []

    def execute_connector(self, node, credential_provider=None, context=None):
        self.contexts.append(context)
        return {
            "status": "completed",
            "connector": {"id": "http", "kind": "http"},
            "output": {},
        }


class _SequenceConnectorRuntime:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def execute_connector(self, node, credential_provider=None, context=None):
        self.calls += 1
        result = dict(self.results.pop(0))
        result.setdefault("connector", {"id": "http", "kind": "http"})
        return result


class _FailingConnectorRuntime:
    def __init__(self):
        self.calls = 0

    def execute_connector(self, node, credential_provider=None, context=None):
        self.calls += 1
        return {
            "status": "failed",
            "connector": {"id": "http", "kind": "http"},
            "error": "provider unavailable",
            "output": {},
        }


def _approval_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_approval",
            "name": "approval",
            "version": "0.1.0",
            "status": "published",
        },
        "entry": "start",
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "title": "Start",
                "on_success": "review",
            },
            {
                "id": "review",
                "type": "human_gate",
                "title": "Review",
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [],
    }


def _http_connector_workflow(url: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_connector",
            "name": "connector",
            "version": "0.1.0",
            "status": "published",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "call_api"},
            {
                "id": "call_api",
                "type": "tool_call",
                "title": "Call API",
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {
                        "method": "POST",
                        "url": url,
                        "headers": {"Content-Type": "application/json"},
                        "body": {"account_id": "acct_123"},
                        "timeout_ms": 2000,
                    },
                },
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_call", "from": "start", "to": "call_api", "label": "next"},
            {"id": "edge_call_end", "from": "call_api", "to": "end", "label": "next"},
            {"id": "edge_call_failure", "from": "call_api", "to": "failure", "label": "failure"},
        ],
    }


def _credential_connector_workflow(url: str):
    workflow = _http_connector_workflow(url)
    workflow["nodes"][1]["connector"]["credentials"] = [
        {
            "target": "header",
            "name": "Authorization",
            "handle": "demo_api_token",
            "prefix": "Bearer ",
        }
    ]
    return workflow


def _mapped_http_connector_workflow(url: str):
    workflow = _http_connector_workflow(url)
    request = workflow["nodes"][1]["connector"]["request"]
    request["body"] = {"source": "static"}
    request["input_mapping"] = [
        {"from": "/input/customer_id", "to": "/body/customer_id", "required": True},
    ]
    return workflow


class _ConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw_body) if raw_body else None
        self.server.requests.append({"path": self.path, "headers": dict(self.headers.items()), "body": body})
        payload = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


class _FlakyConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw_body) if raw_body else None
        self.server.requests.append({"path": self.path, "headers": dict(self.headers.items()), "body": body})

        if len(self.server.requests) == 1:
            payload = json.dumps({"error": "temporary"}).encode("utf-8")
            self.send_response(503)
        else:
            payload = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


class _ConnectorTestServer:
    def __init__(self):
        self._server = HTTPServer(("127.0.0.1", 0), _ConnectorRequestHandler)
        self._server.requests = []
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/connector"

    @property
    def requests(self):
        return self._server.requests

    def close(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class _FlakyConnectorTestServer(_ConnectorTestServer):
    def __init__(self):
        self._server = HTTPServer(("127.0.0.1", 0), _FlakyConnectorRequestHandler)
        self._server.requests = []
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
