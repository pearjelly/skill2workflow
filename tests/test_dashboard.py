import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.control_plane import LocalControlPlane
from unittest.mock import patch

from skill2workflow.dashboard import (
    RUN_DETAIL_SCHEMA_VERSION,
    build_control_snapshot,
    build_control_snapshot_from_control,
    build_recurring_schedule_list_from_store,
    build_recurring_schedule_dispatch_list_from_store,
    build_workflow_artifact_report_from_control,
    build_workflow_inventory_from_control,
    build_run_detail,
    build_run_detail_from_control,
    build_run_list,
    build_run_page_from_control,
    build_audit_event_page_from_control,
    build_support_bundle_from_control,
)
from skill2workflow.schedules import RecurringScheduleDispatcher, RecurringScheduleStore
from skill2workflow.telemetry import RuntimeTelemetry


class DashboardTests(TestCase):
    def test_workflow_inventory_is_bounded_redacted_and_storage_compatible(self):
        for storage in ("json", "sqlite"):
            with self.subTest(storage=storage), TemporaryDirectory() as tmp:
                control = LocalControlPlane(Path(tmp), storage=storage)
                control.publish_workflow(_workflow(version="1.0.0", node_title="v1"))
                control.publish_workflow(
                    _workflow(version="2.0.0", node_title="private title")
                )
                inventory = build_workflow_inventory_from_control(control, max_items=1)

            self.assertEqual(
                inventory["schema_version"],
                "skill2workflow-workflow-inventory-0.1.0",
            )
            self.assertEqual(inventory["summary"]["total"], 2)
            self.assertEqual(inventory["window"]["returned"], 1)
            self.assertTrue(inventory["window"]["truncated"])
            self.assertEqual(inventory["versions"][0]["version"], "2.0.0")
            self.assertNotIn("private title", json.dumps(inventory))

    def test_run_page_is_filtered_redacted_and_cursor_paged(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start"))
            control.run_published_workflow("workflow_dashboard", "1.0.0")
            control.run_published_workflow("workflow_dashboard", "1.0.0")
            page = build_run_page_from_control(
                control,
                max_items=1,
                status="completed",
                workflow_id="workflow_dashboard",
            )

        self.assertEqual(page["schema_version"], "skill2workflow-run-list-0.2.0")
        self.assertEqual(page["filters"], {"status": "completed", "workflow_id": "workflow_dashboard"})
        self.assertEqual(page["summary"]["total"], 2)
        self.assertEqual(page["window"]["returned"], 1)
        self.assertTrue(page["window"]["has_more"])
        self.assertTrue(page["window"]["next_cursor"])
        self.assertNotIn("context", json.dumps(page, ensure_ascii=False))

    def test_audit_event_page_is_cursor_paged_and_redacted(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            for event_type in ("run_started", "connector_failed", "run_completed"):
                control.store.append_audit(
                    {
                        "type": event_type,
                        "workflow_id": "workflow_private_audit",
                        "workflow_version": "0.1.0",
                        "run_id": "run_private_audit",
                        "timestamp": "2026-08-17T00:00:00Z",
                        "error": "private raw provider error",
                        "connector_metadata": {"secret": "private connector value"},
                    }
                )
            first = build_audit_event_page_from_control(
                control,
                max_items=2,
                workflow_id="workflow_private_audit",
            )
            second = build_audit_event_page_from_control(
                control,
                max_items=2,
                cursor=first["window"]["next_cursor"],
                workflow_id="workflow_private_audit",
            )

        serialized = json.dumps(first, ensure_ascii=False)
        self.assertEqual(first["schema_version"], "skill2workflow-audit-event-list-0.1.0")
        self.assertEqual(first["filters"]["workflow_id"], "workflow_private_audit")
        self.assertEqual([event["sequence"] for event in first["events"]], [2, 3])
        self.assertEqual([event["sequence"] for event in second["events"]], [1])
        self.assertTrue(first["window"]["truncated"])
        self.assertFalse(second["window"]["truncated"])
        self.assertNotIn("private raw provider error", serialized)
        self.assertNotIn("private connector value", serialized)
        self.assertTrue(first["events"][0]["has_error"])

    def test_sqlite_bounded_snapshot_does_not_call_unbounded_list_paths(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start v1"))
            control.publish_workflow(_workflow(version="1.1.0", node_title="Start v2"))
            control.run_published_workflow("workflow_dashboard", "1.0.0")
            control.run_published_workflow("workflow_dashboard", "1.1.0")

            original_audit_list = control.store.list_audit_events

            def bounded_audit_list(*args, **kwargs):
                if kwargs.get("limit") is None:
                    raise AssertionError("unbounded audit read")
                return original_audit_list(*args, **kwargs)

            with patch.object(
                control.store,
                "list_audit_events",
                side_effect=bounded_audit_list,
            ), patch.object(
                control.executor.store,
                "list",
                side_effect=AssertionError("unbounded run read"),
            ):
                snapshot = build_control_snapshot_from_control(control, max_items=1)

        self.assertEqual(snapshot["summary"]["workflow_count"], 2)
        self.assertEqual(snapshot["summary"]["run_count"], 2)
        self.assertEqual(len(snapshot["workflows"]), 1)
        self.assertEqual(len(snapshot["runs"]), 1)
        self.assertEqual(len(snapshot["audit_events"]), 1)
        self.assertTrue(snapshot["window"]["workflows"]["truncated"])
        self.assertTrue(snapshot["window"]["runs"]["truncated"])

    def test_json_bounded_snapshot_does_not_call_unbounded_list_paths(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start v1"))
            control.publish_workflow(_workflow(version="1.1.0", node_title="Start v2"))
            control.run_published_workflow("workflow_dashboard", "1.0.0")
            control.run_published_workflow("workflow_dashboard", "1.1.0")

            original_audit_list = control.store.list_audit_events

            def bounded_audit_list(*args, **kwargs):
                if kwargs.get("limit") is None:
                    raise AssertionError("unbounded audit read")
                return original_audit_list(*args, **kwargs)

            with patch.object(
                control.store,
                "list_audit_events",
                side_effect=bounded_audit_list,
            ), patch.object(
                control.executor.store,
                "list",
                side_effect=AssertionError("unbounded run read"),
            ):
                snapshot = build_control_snapshot_from_control(control, max_items=1)

        self.assertEqual(snapshot["summary"]["workflow_count"], 2)
        self.assertEqual(snapshot["summary"]["run_count"], 2)
        self.assertEqual(len(snapshot["workflows"]), 1)
        self.assertEqual(len(snapshot["runs"]), 1)
        self.assertEqual(len(snapshot["audit_events"]), 1)

    def test_bounded_snapshot_reports_total_and_returned_windows(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start v1"))
            control.publish_workflow(_workflow(version="1.1.0", node_title="Start v2"))
            control.run_published_workflow("workflow_dashboard", "1.0.0")
            control.run_published_workflow("workflow_dashboard", "1.1.0")

            snapshot = build_control_snapshot(state_dir, max_items=1)

        self.assertEqual(snapshot["summary"]["workflow_count"], 2)
        self.assertEqual(snapshot["summary"]["run_count"], 2)
        self.assertGreater(snapshot["summary"]["audit_event_count"], 1)
        self.assertEqual(len(snapshot["workflows"]), 1)
        self.assertEqual(len(snapshot["runs"]), 1)
        self.assertEqual(len(snapshot["audit_events"]), 1)
        self.assertEqual(snapshot["audit_events"][0]["type"], "run_completed")
        self.assertEqual(snapshot["window"]["max_items"], 1)
        self.assertEqual(
            snapshot["window"]["workflows"],
            {"total": 2, "returned": 1, "truncated": True},
        )
        self.assertEqual(
            snapshot["window"]["runs"],
            {"total": 2, "returned": 1, "truncated": True},
        )
        self.assertEqual(
            snapshot["window"]["audit_events"],
            {
                "total": snapshot["summary"]["audit_event_count"],
                "returned": 1,
                "truncated": True,
            },
        )

    def test_bounded_snapshot_rejects_non_positive_or_boolean_limit(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            for value in (0, -1, True):
                with self.subTest(value=value):
                    with self.assertRaisesRegex(ValueError, "max_items"):
                        build_control_snapshot(state_dir, max_items=value)

    def test_build_control_snapshot_summarizes_registry_runs_audit_and_versions(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start v1"))
            control.publish_workflow(_workflow(version="1.1.0", node_title="Start v2"))
            control.deprecate_workflow("workflow_dashboard", "1.0.0")
            run_state = control.run_published_workflow("workflow_dashboard", "1.1.0")

            snapshot = build_control_snapshot(state_dir)

        self.assertEqual(snapshot["schema_version"], "skill2workflow-control-snapshot-0.1.0")
        self.assertEqual(snapshot["summary"]["workflow_count"], 2)
        self.assertEqual(snapshot["summary"]["run_count"], 1)
        self.assertEqual(snapshot["summary"]["audit_event_count"], 5)
        self.assertEqual(snapshot["summary"]["connector_count"], 2)
        self.assertEqual(snapshot["summary"]["status_counts"], {"deprecated": 1, "published": 1})
        self.assertEqual(snapshot["workflows"][0]["workflow_id"], "workflow_dashboard")
        self.assertEqual(snapshot["runs"][0]["run_id"], run_state["run_id"])
        self.assertEqual(snapshot["runs"][0]["event_count"], len(run_state["events"]))
        self.assertEqual(
            [event["type"] for event in snapshot["audit_events"]],
            [
                "workflow_published",
                "workflow_published",
                "workflow_deprecated",
                "run_started",
                "run_completed",
            ],
        )
        comparison = snapshot["version_comparisons"][0]
        self.assertEqual(comparison["workflow_id"], "workflow_dashboard")
        self.assertEqual(comparison["versions"], ["1.0.0", "1.1.0"])
        self.assertTrue(comparison["checksum_changed"])
        self.assertEqual(comparison["node_count_delta"], 0)
        self.assertEqual(comparison["edge_count_delta"], 0)

    def test_build_control_snapshot_derives_operator_insights(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start v1"))
            control.publish_workflow(_workflow(version="1.1.0", node_title="Start v2"))
            control.publish_workflow(_approval_workflow(version="1.0.0"))
            control.publish_workflow(_failing_connector_workflow(version="1.0.0"))

            waiting_run = control.run_published_workflow("workflow_waiting", "1.0.0")
            failed_run = control.run_published_workflow("workflow_connector_failure", "1.0.0")
            snapshot = build_control_snapshot(state_dir)

        waiting_summary = next(run for run in snapshot["runs"] if run["run_id"] == waiting_run["run_id"])
        failed_summary = next(run for run in snapshot["runs"] if run["run_id"] == failed_run["run_id"])
        waiting_overlay = waiting_summary["node_overlays"]["review"]
        connector_overlay = failed_summary["node_overlays"]["call_api"]

        insights = snapshot["operator_insights"]
        self.assertEqual(insights["attention_counts"]["waiting_runs"], 1)
        self.assertEqual(insights["attention_counts"]["failed_runs"], 1)
        self.assertEqual(insights["attention_counts"]["connector_failures"], 1)
        self.assertEqual(insights["attention_counts"]["version_changes"], 1)
        self.assertEqual(insights["connector_event_counts"]["connector_started"], 1)
        self.assertEqual(insights["connector_event_counts"]["connector_failed"], 1)
        self.assertEqual(insights["version_changes"][0]["workflow_id"], "workflow_dashboard")
        self.assertEqual(insights["version_changes"][0]["versions"], ["1.0.0", "1.1.0"])

        attention = {(item["kind"], item.get("run_id")) for item in insights["attention_items"]}
        self.assertIn(("waiting_run", waiting_run["run_id"]), attention)
        self.assertIn(("failed_run", failed_run["run_id"]), attention)
        self.assertIn(("connector_failure", failed_run["run_id"]), attention)
        self.assertLessEqual(len(insights["recent_events"]), 5)
        self.assertEqual(insights["recent_events"][-1]["type"], "run_failed")
        self.assertEqual(waiting_overlay["status"], "waiting")
        self.assertEqual(waiting_overlay["current"], True)
        self.assertEqual(waiting_overlay["latest_event_type"], "human_gate_waiting")
        self.assertEqual(connector_overlay["status"], "failed")
        self.assertEqual(connector_overlay["connector_id"], "http")
        self.assertEqual(connector_overlay["connector_status"], "failed")
        self.assertEqual(connector_overlay["attempts"], 1)
        self.assertEqual(connector_overlay["audit_event_count"], 3)
        self.assertNotIn("output", connector_overlay)

    def test_interrupted_run_is_a_distinct_critical_attention_item(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start"))
            run = control.run_published_workflow("workflow_dashboard", "1.0.0")
            detail = control.get_run(run["run_id"])
            detail["status"] = "interrupted"
            detail["events"].append(
                {
                    "type": "run_interrupted",
                    "node_id": detail["current_node"],
                    "timestamp": "2026-08-11T00:00:00+00:00",
                }
            )
            control.executor.store.save(detail)

            insights = build_control_snapshot(state_dir)["operator_insights"]

        self.assertEqual(insights["attention_counts"]["interrupted_runs"], 1)
        self.assertIn(
            ("interrupted_run", run["run_id"]),
            {
                (item["kind"], item.get("run_id"))
                for item in insights["attention_items"]
            },
        )

    def test_run_detail_is_bounded_and_redacts_context_results_and_errors(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start"))
            run = control.run_published_workflow("workflow_dashboard", "1.0.0")
            detail = control.get_run(run["run_id"])
            detail["context"] = {
                "trigger": {
                    "input": "private-trigger-value",
                    "authorization": "private-auth-value",
                }
            }
            detail["node_results"]["start"]["output"] = "private-output-value"
            detail["events"].append(
                {
                    "type": "connector_failed",
                    "node_id": "start",
                    "timestamp": "2026-08-13T00:00:00+00:00",
                    "error": "private-provider-error",
                    "response": "private-provider-response",
                    "connector_id": {"secret": "nested-provider-secret"},
                }
            )
            for index in range(60):
                detail["events"].append(
                    {
                        "type": "private-event-type",
                        "node_id": "start",
                        "timestamp": f"2026-08-13T00:01:{index:02d}+00:00",
                        "secret": "private-event-value",
                    }
                )
            control.executor.store.save(detail)

            projected = build_run_detail(state_dir, run["run_id"], storage="sqlite")

        self.assertEqual(projected["schema_version"], RUN_DETAIL_SCHEMA_VERSION)
        self.assertEqual(projected["run"]["run_id"], run["run_id"])
        self.assertEqual(projected["window"], {
            "max_events": 50,
            "total": 64,
            "returned": 50,
            "truncated": True,
        })
        self.assertEqual(len(projected["events"]), 50)
        self.assertTrue(all("secret" not in event for event in projected["events"]))
        self.assertTrue(all("error" not in event for event in projected["events"]))
        self.assertNotIn("context", projected["run"])
        self.assertNotIn("output", json.dumps(projected, ensure_ascii=False))
        serialized = json.dumps(projected, ensure_ascii=False)
        for private_value in (
            "private-trigger-value",
            "private-auth-value",
            "private-output-value",
            "private-provider-error",
            "private-provider-response",
            "private-event-value",
            "nested-provider-secret",
        ):
            self.assertNotIn(private_value, serialized)
        self.assertIn("has_error", projected["run"]["node_overlays"]["start"])

    def test_run_detail_reads_only_the_bounded_audit_tail(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start"))
            run = control.run_published_workflow("workflow_dashboard", "1.0.0")
            original = control.store.list_audit_events

            def bounded_audit_list(*args, **kwargs):
                if kwargs.get("limit") is None:
                    raise AssertionError("run detail loaded the full audit history")
                return original(*args, **kwargs)

            with patch.object(
                control.store, "list_audit_events", side_effect=bounded_audit_list
            ):
                projected = build_run_detail_from_control(control, run["run_id"])

        self.assertEqual(projected["window"]["max_events"], 50)

    def test_sqlite_run_detail_uses_compact_projection_without_state_json(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start"))
            run = control.run_published_workflow("workflow_dashboard", "1.0.0")
            expected_event_count = len(control.get_run(run["run_id"])["events"])
            with control.executor.store._connection() as connection:
                connection.execute(
                    "update runs set state_json = ? where run_id = ?",
                    ("not-json", run["run_id"]),
                )

            projected = build_run_detail(state_dir, run["run_id"], storage="sqlite")

        self.assertEqual(projected["run"]["run_id"], run["run_id"])
        self.assertEqual(projected["run"]["status"], "completed")
        self.assertEqual(projected["window"]["total"], expected_event_count)
        self.assertIn("start", projected["run"]["node_overlays"])

    def test_run_list_is_bounded_and_redacted(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start"))
            first = control.run_published_workflow("workflow_dashboard", "1.0.0")
            second = control.run_published_workflow("workflow_dashboard", "1.0.0")
            state = control.get_run(first["run_id"])
            state["context"] = {"private_input": "private-list-input"}
            state["node_results"]["start"]["output"] = "private-list-output"
            control.executor.store.save(state)

            projected = build_run_list(state_dir, storage="sqlite", max_items=1)

        self.assertEqual(projected["schema_version"], "skill2workflow-run-list-0.1.0")
        self.assertEqual(projected["summary"]["total"], 2)
        self.assertEqual(sum(projected["summary"]["status_counts"].values()), 2)
        self.assertEqual(projected["window"], {
            "max_items": 1,
            "total": 2,
            "returned": 1,
            "truncated": True,
        })
        self.assertEqual(len(projected["runs"]), 1)
        self.assertEqual(
            set(projected["runs"][0]),
            {
                "run_id",
                "workflow_id",
                "workflow_version",
                "status",
                "current_node",
                "event_count",
                "node_result_count",
            },
        )
        serialized = json.dumps(projected, ensure_ascii=False)
        self.assertNotIn("private-list-input", serialized)
        self.assertNotIn("private-list-output", serialized)
        self.assertNotIn("context", serialized)
        self.assertNotEqual(projected["runs"][0]["run_id"], "")
        self.assertIn(projected["runs"][0]["run_id"], {first["run_id"], second["run_id"]})

    def test_recurring_schedule_list_is_bounded_and_excludes_trigger_input(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            store = RecurringScheduleStore(state_dir)
            store.add(_recurring_schedule_definition("schedule_active", enabled=True))
            store.add(_recurring_schedule_definition("schedule_disabled", enabled=False))

            with patch.object(store, "list", side_effect=AssertionError("unbounded schedule read")):
                projected = build_recurring_schedule_list_from_store(store, max_items=1)

        self.assertEqual(
            projected["schema_version"],
            "skill2workflow-recurring-schedule-list-0.1.0",
        )
        self.assertEqual(projected["summary"], {
            "total": 2,
            "status_counts": {"active": 1, "disabled": 1, "other": 0},
        })
        self.assertEqual(projected["window"], {
            "max_items": 1,
            "total": 2,
            "returned": 1,
            "truncated": True,
        })
        self.assertEqual(len(projected["schedules"]), 1)
        self.assertEqual(
            set(projected["schedules"][0]),
            {
                "schedule_id", "workflow_id", "workflow_version", "status", "enabled",
                "starts_at", "next_run_at", "interval_seconds", "missed_run_policy",
                "last_scheduled_for", "last_run_id", "last_trigger_id",
            },
        )
        serialized = json.dumps(projected, ensure_ascii=False)
        self.assertNotIn("private-schedule-input", serialized)
        self.assertNotIn("idempotency_key_prefix", serialized)

    def test_recurring_schedule_projection_uses_compact_store_summary(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            store = RecurringScheduleStore(state_dir)
            store.add(
                _recurring_schedule_definition(
                    "schedule_compact", enabled=True, input_value="private-schedule-input"
                )
            )
            with store._connection() as connection:
                connection.execute(
                    "update recurring_schedules set definition_json = ? where schedule_id = ?",
                    ("not-json", "schedule_compact"),
                )

            projected = build_recurring_schedule_list_from_store(store, max_items=1)

        self.assertEqual(projected["summary"]["total"], 1)
        self.assertEqual(projected["schedules"][0]["schedule_id"], "schedule_compact")

    def test_recurring_dispatch_list_is_bounded_and_excludes_lease_or_input_values(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start"))
            store = RecurringScheduleStore(state_dir)
            store.add(
                _recurring_schedule_definition(
                    "schedule_dispatch", enabled=True,
                    input_value="private-dispatch-input",
                )
            )
            dispatcher = RecurringScheduleDispatcher(
                state_dir, owner_id="private-dispatch-owner", lease_seconds=30
            )
            self.assertTrue(dispatcher.try_acquire(now_epoch=1000))
            dispatcher.dispatch_due("2026-08-11T00:00:00Z", now_epoch=1001)

            with patch.object(
                store,
                "list_dispatches",
                side_effect=AssertionError("unbounded dispatch read"),
            ):
                projected = build_recurring_schedule_dispatch_list_from_store(
                    store, max_items=1
                )

        self.assertEqual(
            projected["schema_version"],
            "skill2workflow-recurring-schedule-dispatch-list-0.1.0",
        )
        self.assertEqual(projected["summary"]["total"], 1)
        self.assertEqual(projected["window"]["returned"], 1)
        self.assertEqual(
            set(projected["dispatches"][0]),
            {
                "dispatch_id", "schedule_id", "scheduled_for", "status",
                "coalesced_occurrences", "run_id", "trigger_id", "error_type",
                "completed_at",
            },
        )
        serialized = json.dumps(projected, ensure_ascii=False)
        self.assertNotIn("private-dispatch-input", serialized)
        self.assertNotIn("private-dispatch-owner", serialized)
        self.assertNotIn("claim_expires_at", serialized)

    def test_remote_workflow_artifact_report_is_bounded_and_reuses_fixed_contract(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0", node_title="Private title"))
            workflows_dir = state_dir / "workflows"
            for index in range(5):
                (workflows_dir / f"orphan-{index}.json").write_text("{}", encoding="utf-8")

            projected = build_workflow_artifact_report_from_control(control, max_issues=2)

        self.assertEqual(
            projected["schema_version"],
            "skill2workflow-workflow-artifact-report-0.1.0",
        )
        self.assertEqual(projected["status"], "attention")
        self.assertEqual(projected["summary"]["issue_count"], 5)
        self.assertEqual(len(projected["issues"]), 2)
        self.assertTrue(projected["summary"]["truncated"])
        self.assertNotIn("Private title", json.dumps(projected, ensure_ascii=False))

    def test_support_bundle_is_fixed_and_redacted(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0", node_title="Start"))
            run = control.run_published_workflow("workflow_dashboard", "1.0.0")
            state = control.get_run(run["run_id"])
            state["context"] = {"private_input": "private-bundle-input"}
            state["node_results"]["start"]["output"] = "private-bundle-output"
            control.executor.store.save(state)
            RecurringScheduleStore(state_dir)
            bundle = build_support_bundle_from_control(
                control,
                RuntimeTelemetry(state_dir, monotonic=lambda: 2.0),
                service_status="ready",
                ready=True,
                scheduler_lease_owned=False,
            )

        self.assertEqual(bundle["schema_version"], "skill2workflow-support-bundle-0.1.0")
        self.assertEqual(
            set(bundle), {"schema_version", "service", "run_list", "observability"}
        )
        self.assertEqual(bundle["service"]["storage"], "sqlite")
        self.assertEqual(bundle["run_list"]["summary"]["total"], 1)
        self.assertEqual(bundle["observability"]["service_status"], "ready")
        self.assertIn("support_bundle", bundle["observability"]["http_requests"])
        self.assertNotIn("recurring_schedule_create", bundle["observability"]["http_requests"])
        self.assertNotIn("recurring_schedule_update", bundle["observability"]["http_requests"])
        self.assertNotIn("recurring_schedule_patch", bundle["observability"]["http_requests"])
        self.assertNotIn("recurring_schedule_delete", bundle["observability"]["http_requests"])
        serialized = json.dumps(bundle, ensure_ascii=False)
        self.assertNotIn("private-bundle-input", serialized)
        self.assertNotIn("private-bundle-output", serialized)
        self.assertNotIn("context", serialized)


def _workflow(version: str, node_title: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_dashboard",
            "name": "dashboard",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": node_title, "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }


def _recurring_schedule_definition(
    schedule_id: str, enabled: bool, input_value: str = "private-schedule-input"
):
    return {
        "schema_version": "skill2workflow-schedule-0.2.0",
        "schedule": {
            "id": schedule_id,
            "workflow_id": "workflow_dashboard",
            "version": "1.0.0",
            "starts_at": "2026-08-11T00:00:00Z",
            "interval_seconds": 60,
            "missed_run_policy": "latest",
            "enabled": enabled,
        },
        "trigger": {
            "idempotency_key_prefix": schedule_id,
            "input": {"private": input_value},
        },
    }


def _approval_workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_waiting",
            "name": "waiting",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "review"},
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
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
            {"id": "edge_review_end", "from": "review", "to": "end", "label": "next"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "failure"},
        ],
    }


def _failing_connector_workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_connector_failure",
            "name": "connector-failure",
            "version": version,
            "status": "draft",
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
                        "url": "ftp://example.test/not-called",
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
