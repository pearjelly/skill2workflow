import io
import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.schedules import RecurringScheduleStore
from skill2workflow.telemetry import (
    TELEMETRY_EVENT_SCHEMA_VERSION,
    OperationalEventLogger,
    RuntimeTelemetry,
)


class RuntimeTelemetryTests(TestCase):
    def test_cancelled_runs_have_a_fixed_aggregate_status(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_waiting_workflow())
            waiting = control.run_published_workflow("workflow_waiting", "0.1.0")
            control.cancel_published_run(waiting["run_id"])
            RecurringScheduleStore(state_dir)

            rendered = RuntimeTelemetry(state_dir).render(
                service_status="ready",
                ready=True,
                scheduler_lease_owned=False,
            )

        self.assertIn('skill2workflow_runs{status="cancelled"} 1', rendered)
        self.assertNotIn('skill2workflow_runs{status="other"} 1', rendered)

    def test_metrics_are_aggregate_low_cardinality_and_private_value_free(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            control.trigger_workflow(
                {
                    "workflow_id": "workflow_private_customer_48392",
                    "version": "0.1.0",
                    "source": "telemetry-test",
                    "idempotency_key": "private-idempotency-value",
                    "input": {"customer": "private-customer-value"},
                }
            )
            RecurringScheduleStore(state_dir).add(_schedule())
            telemetry = RuntimeTelemetry(state_dir, monotonic=lambda: 15.25)
            telemetry.observe_http("workflow_trigger", 200)
            telemetry.observe_http("control_snapshot", 200)
            telemetry.observe_http("audit_consistency", 200)
            telemetry.observe_http("recurring_schedule_dispatch_list", 200)
            telemetry.observe_http("workflow_artifact_report", 200)
            telemetry.observe_http("backup_readiness", 200)
            telemetry.observe_http("retention_readiness", 200)
            telemetry.observe_http("operational_readiness", 200)
            telemetry.observe_http("audit_integrity", 200)
            telemetry.observe_http("runtime_info", 200)
            telemetry.observe_http("workflow_release", 200)
            telemetry.observe_http("workflow_promotion", 200)
            telemetry.observe_http("workflow_deprecation", 200)
            telemetry.observe_http("workflow_inventory", 200)
            telemetry.observe_http("workflow_diff", 200)
            telemetry.observe_http("support_bundle", 200)
            telemetry.observe_http("run_list", 200)
            telemetry.observe_http("run_detail", 200)
            telemetry.observe_http("run_resume", 409)
            telemetry.observe_http("unknown-private-route", 418)

            rendered = telemetry.render(
                service_status="ready",
                ready=True,
                scheduler_lease_owned=True,
            )

        for line in (
            "skill2workflow_service_ready 1",
            "skill2workflow_scheduler_lease_owned 1",
            'skill2workflow_workflows{status="published"} 1',
            'skill2workflow_runs{status="completed"} 1',
            "skill2workflow_audit_events 3",
            "skill2workflow_recurring_schedules 1",
            'skill2workflow_http_requests_total{route="workflow_trigger",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="control_snapshot",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="recurring_schedule_list",status_class="2xx"} 0',
            'skill2workflow_http_requests_total{route="recurring_schedule_action",status_class="2xx"} 0',
            'skill2workflow_http_requests_total{route="recurring_schedule_dispatch_list",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="workflow_artifact_report",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="backup_readiness",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="retention_readiness",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="operational_readiness",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="audit_integrity",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="runtime_info",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="workflow_release",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="workflow_promotion",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="workflow_deprecation",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="workflow_inventory",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="workflow_diff",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="support_bundle",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="run_list",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="run_detail",status_class="2xx"} 1',
            'skill2workflow_http_requests_total{route="run_resume",status_class="4xx"} 1',
            'skill2workflow_http_requests_total{route="unknown",status_class="4xx"} 1',
        ):
            self.assertIn(line, rendered)
        self.assertTrue(rendered.endswith("\n"))
        for forbidden in (
            "workflow_private_customer_48392",
            "private-idempotency-value",
            "private-customer-value",
            "unknown-private-route",
            str(state_dir),
        ):
            self.assertNotIn(forbidden, rendered)

    def test_aggregate_support_bundle_contract_is_fixed_and_value_free(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            control.trigger_workflow(
                {
                    "workflow_id": "workflow_private_customer_48392",
                    "version": "0.1.0",
                    "source": "support-bundle-test",
                    "idempotency_key": "private-idempotency-value",
                    "input": {"customer": "private-customer-value"},
                }
            )
            RecurringScheduleStore(state_dir)
            telemetry = RuntimeTelemetry(state_dir, monotonic=lambda: 4.0)
            aggregate = telemetry.aggregate(
                service_status="ready",
                ready=True,
                scheduler_lease_owned=False,
            )

        self.assertEqual(
            set(aggregate),
            {
                "service_status", "ready", "scheduler_lease_owned", "uptime_seconds",
                "workflow_status_counts", "run_status_counts", "dispatch_status_counts",
                "audit_event_count", "recurring_schedule_count", "http_requests",
            },
        )
        self.assertEqual(
            set(aggregate["http_requests"]),
            {
                "health", "readiness", "metrics", "control_snapshot", "recurring_schedule_list",
                "recurring_schedule_action", "recurring_schedule_dispatch_list",
                "workflow_artifact_report",
                "backup_readiness",
                "retention_readiness",
                "operational_readiness",
                "audit_integrity",
                "runtime_info",
                "audit_consistency",
                "support_bundle", "run_list", "run_detail", "workflow_trigger", "run_cancel",
                "workflow_release", "workflow_promotion", "workflow_deprecation", "workflow_inventory", "workflow_diff", "run_resume", "unknown",
            },
        )
        serialized = json.dumps(aggregate, ensure_ascii=False)
        for forbidden in (
            "workflow_private_customer_48392",
            "private-idempotency-value",
            "private-customer-value",
            str(state_dir),
        ):
            self.assertNotIn(forbidden, serialized)

    def test_operational_events_have_strict_allowlisted_ndjson_shapes(self):
        stream = io.StringIO()
        fixed_now = lambda: datetime(2026, 8, 11, 0, 0, tzinfo=timezone.utc)
        logger = OperationalEventLogger(stream=stream, now=fixed_now)

        logger.lifecycle("ready")
        logger.request_completed(
            method="POST-with-private-suffix",
            route="/webhooks/private-workflow/value",
            status_code=201,
            duration_ms=12.7,
        )
        events = [json.loads(line) for line in stream.getvalue().splitlines()]

        self.assertEqual(
            set(events[0]),
            {"schema_version", "timestamp", "event_type", "service", "status"},
        )
        self.assertEqual(events[0]["schema_version"], TELEMETRY_EVENT_SCHEMA_VERSION)
        self.assertEqual(events[0]["status"], "ready")
        self.assertEqual(
            set(events[1]),
            {
                "schema_version",
                "timestamp",
                "event_type",
                "service",
                "method",
                "route",
                "status_code",
                "status_class",
                "duration_ms",
            },
        )
        self.assertEqual(events[1]["method"], "OTHER")
        self.assertEqual(events[1]["route"], "unknown")
        self.assertNotIn("private", stream.getvalue())

    def test_unknown_persisted_statuses_collapse_into_other_without_leaking(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            control.trigger_workflow(
                {
                    "workflow_id": "workflow_private_customer_48392",
                    "version": "0.1.0",
                    "idempotency_key": "unknown-status-test",
                }
            )
            RecurringScheduleStore(state_dir)
            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection, connection:
                connection.execute(
                    "update workflow_versions set status = ?",
                    ("private-workflow-status-49382",),
                )
            with closing(sqlite3.connect(state_dir / "runs.sqlite3")) as connection, connection:
                connection.execute(
                    "update runs set status = ?",
                    ("private-run-status-49382",),
                )

            rendered = RuntimeTelemetry(state_dir).render(
                service_status="ready",
                ready=True,
                scheduler_lease_owned=False,
            )

        self.assertIn('skill2workflow_workflows{status="other"} 1', rendered)
        self.assertIn('skill2workflow_runs{status="other"} 1', rendered)
        self.assertNotIn("private-workflow-status-49382", rendered)
        self.assertNotIn("private-run-status-49382", rendered)

    def test_real_process_observability_smoke_proves_auth_metrics_and_logs(self):
        with TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/observability_smoke.py",
                    "--work-dir",
                    str(Path(tmp) / "smoke"),
                ],
                cwd=str(Path(__file__).resolve().parents[1]),
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertTrue(evidence["checks"]["unauthenticated_metrics_denied"])
        self.assertTrue(evidence["checks"]["authenticated_metrics_exported"])
        self.assertTrue(evidence["checks"]["aggregate_state_visible"])
        self.assertTrue(evidence["checks"]["low_cardinality_labels"])
        self.assertTrue(evidence["checks"]["private_values_absent"])
        self.assertTrue(evidence["checks"]["structured_lifecycle_logs"])


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_private_customer_48392",
            "name": "Private telemetry fixture",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}
        ],
    }


def _schedule():
    return {
        "schema_version": "skill2workflow-schedule-0.2.0",
        "schedule": {
            "id": "schedule_private_customer_48392",
            "workflow_id": "workflow_private_customer_48392",
            "version": "0.1.0",
            "starts_at": "2099-01-01T00:00:00+00:00",
            "interval_seconds": 3600,
            "missed_run_policy": "latest",
        },
        "trigger": {"input": {}},
    }


def _waiting_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_waiting",
            "name": "Waiting telemetry fixture",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "on_success": "review"},
            {
                "id": "review",
                "type": "human_gate",
                "connector": {"id": "manual", "kind": "manual"},
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure"},
            {"id": "end", "type": "end"},
        ],
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
            {"id": "edge_review_end", "from": "review", "to": "end", "label": "approved"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "rejected"},
        ],
    }
