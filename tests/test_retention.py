import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.retention import (
    RETENTION_POLICY_SCHEMA_VERSION,
    apply_state_retention,
    inspect_state_retention,
    normalize_retention_policy,
)
from skill2workflow.schedules import RecurringScheduleStore


class StateRetentionTests(TestCase):
    def test_policy_requires_aware_cutoff_and_exact_safe_terminal_statuses(self):
        normalized = normalize_retention_policy(_policy())

        self.assertEqual(normalized["schema_version"], "skill2workflow-retention-policy-0.1.0")
        self.assertEqual(
            normalize_retention_policy(_policy_v2())["schema_version"],
            "skill2workflow-retention-policy-0.2.0",
        )
        self.assertEqual(
            normalize_retention_policy(_policy_v3())["schema_version"],
            RETENTION_POLICY_SCHEMA_VERSION,
        )
        self.assertEqual(normalized["retention"]["delete_before"], "2026-01-01T00:00:00+00:00")
        invalid = [
            {},
            {**_policy(), "unknown": True},
            {
                **_policy(),
                "retention": {**_policy()["retention"], "delete_before": "2026-01-01"},
            },
            {
                **_policy(),
                "retention": {
                    **_policy()["retention"],
                    "terminal_run_statuses": ["completed", "failed", "waiting"],
                },
            },
            {
                **_policy(),
                "retention": {
                    **_policy()["retention"],
                    "terminal_dispatch_statuses": ["completed", "claimed"],
                },
            },
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    normalize_retention_policy(payload)

    def test_v2_policy_disposes_cancelled_runs_and_their_cancellation_ledger(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            control = LocalControlPlane(source, storage="sqlite")
            control.publish_workflow(_waiting_workflow())
            waiting = control.run_published_workflow("workflow_cancel_retention", "0.1.0")
            control.cancel_published_run(waiting["run_id"])
            RecurringScheduleStore(source)
            with closing(sqlite3.connect(source / "runs.sqlite3")) as connection, connection:
                connection.execute(
                    "update runs set updated_at = '2025-01-01 00:00:00' where run_id = ?",
                    (waiting["run_id"],),
                )
                connection.commit()
            output = root / "retained"

            plan = inspect_state_retention(source, _policy_v2())
            result = apply_state_retention(source, output, _policy_v2())
            with closing(sqlite3.connect(output / "runs.sqlite3")) as connection, connection:
                run_count = connection.execute(
                    "select count(*) from runs where run_id = ?", (waiting["run_id"],)
                ).fetchone()[0]
                cancellation_count = connection.execute(
                    "select count(*) from run_cancellations where run_id = ?",
                    (waiting["run_id"],),
                ).fetchone()[0]

        self.assertEqual(plan["eligible_terminal_runs"], 1)
        self.assertEqual(plan["eligible_run_cancellations"], 1)
        self.assertEqual(result["deleted_terminal_runs"], 1)
        self.assertEqual(result["deleted_run_cancellations"], 1)
        self.assertEqual(run_count, 0)
        self.assertEqual(cancellation_count, 0)

    def test_v3_policy_disposes_interrupted_runs_and_execution_ledger(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            _populate_retention_state(source)
            run_id = "run_old_interrupted_private"
            state = {
                "run_id": run_id,
                "workflow_id": "workflow_retention_private",
                "workflow_version": "0.1.0",
                "status": "interrupted",
                "current_node": "private-node",
                "context": {"customer": "private-interrupted-value"},
                "events": [{"type": "run_interrupted", "node_id": "private-node"}],
            }
            with closing(sqlite3.connect(source / "runs.sqlite3")) as connection, connection:
                connection.execute(
                    "insert into runs values (?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        "workflow_retention_private",
                        "0.1.0",
                        "interrupted",
                        "private-node",
                        json.dumps(state),
                        "2025-01-01 00:00:00",
                    ),
                )
                connection.execute(
                    "insert into run_events values (?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        1,
                        "run_interrupted",
                        "private-node",
                        "2025-01-01T00:00:00+00:00",
                        "{}",
                    ),
                )
                connection.execute(
                    "insert into run_executions values (?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        "private-owner",
                        "private-execution",
                        "interrupted",
                        "2025-01-01T00:00:00+00:00",
                        "2025-01-01T00:00:00+00:00",
                    ),
                )
            with closing(sqlite3.connect(source / "control.sqlite3")) as connection, connection:
                connection.execute(
                    """
                    insert into audit_events (
                        event_type, workflow_id, workflow_version, run_id,
                        timestamp, payload_json
                    ) values (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "run_interrupted",
                        "workflow_retention_private",
                        "0.1.0",
                        run_id,
                        "2025-01-01T00:00:00+00:00",
                        "{}",
                    ),
                )
            output = root / "retained"

            plan = inspect_state_retention(source, _policy_v3())
            result = apply_state_retention(source, output, _policy_v3())
            with closing(sqlite3.connect(output / "runs.sqlite3")) as connection, connection:
                run = connection.execute(
                    "select 1 from runs where run_id = ?", (run_id,)
                ).fetchone()
                ticket = connection.execute(
                    "select 1 from run_executions where run_id = ?", (run_id,)
                ).fetchone()

        self.assertEqual(plan["eligible_run_executions"], 1)
        self.assertEqual(result["deleted_run_executions"], 1)
        self.assertIsNone(run)
        self.assertIsNone(ticket)

    def test_plan_is_read_only_and_reports_only_eligible_aggregate_counts(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            expected = _populate_retention_state(state_dir)
            before = _database_bytes(state_dir)

            plan = inspect_state_retention(state_dir, _policy())

        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["strategy"], "copy_on_write")
        self.assertTrue(plan["source_preserved"])
        self.assertEqual(len(plan["policy_sha256"]), 64)
        self.assertEqual(plan["eligible_terminal_runs"], 1)
        self.assertEqual(plan["eligible_run_events"], 1)
        self.assertEqual(plan["eligible_run_audit_events"], 1)
        self.assertEqual(plan["eligible_terminal_dispatches"], 1)
        self.assertEqual(plan["preserved_nonterminal_runs"], 1)
        self.assertEqual(plan["preserved_claimed_dispatches"], 1)
        self.assertEqual(before, expected)
        self.assertNotIn("old-completed-private", json.dumps(plan))

    def test_apply_publishes_verified_copy_and_preserves_protected_and_source_state(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            before = _populate_retention_state(source)
            output = root / "retained"
            plan = inspect_state_retention(source, _policy())

            result = apply_state_retention(source, output, _policy())

            self.assertEqual(_database_bytes(source), before)
            with closing(sqlite3.connect(output / "runs.sqlite3")) as connection, connection:
                runs = dict(connection.execute("select run_id, status from runs"))
                events = {row[0] for row in connection.execute("select run_id from run_events")}
            with closing(sqlite3.connect(output / "control.sqlite3")) as connection, connection:
                audit_runs = {row[0] for row in connection.execute("select run_id from audit_events")}
            with closing(sqlite3.connect(output / "scheduler.sqlite3")) as connection, connection:
                dispatches = dict(
                    connection.execute("select dispatch_id, status from schedule_dispatches")
                )
            output_bytes = b"".join(_database_bytes(output).values())

        self.assertEqual(result["status"], "retained_copy_created")
        self.assertEqual(result["policy_sha256"], plan["policy_sha256"])
        self.assertEqual(result["deleted_terminal_runs"], 1)
        self.assertEqual(result["deleted_run_events"], 1)
        self.assertEqual(result["deleted_run_audit_events"], 1)
        self.assertEqual(result["deleted_terminal_dispatches"], 1)
        self.assertNotIn("run_old_completed_private", runs)
        self.assertNotIn("run_old_completed_private", events)
        self.assertNotIn("run_old_completed_private", audit_runs)
        self.assertEqual(runs["run_old_waiting_private"], "waiting")
        self.assertEqual(runs["run_new_failed_private"], "failed")
        self.assertEqual(dispatches["dispatch_old_claimed_private"], "claimed")
        self.assertEqual(dispatches["dispatch_new_failed_private"], "failed")
        self.assertNotIn("dispatch_old_completed_private", dispatches)
        self.assertNotIn(b"private-old-customer-value", output_bytes)
        self.assertNotIn(b"run_old_completed_private", output_bytes)
        self.assertNotIn(b"dispatch_old_completed_private", output_bytes)

    def test_apply_rejects_active_service_existing_or_nested_output_and_is_atomic_on_failure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            before = _populate_retention_state(source)
            with closing(sqlite3.connect(source / "scheduler.sqlite3")) as connection, connection:
                connection.execute(
                    "insert into scheduler_leases values (?, ?, ?)",
                    ("recurring-dispatcher", "active", 4_000_000_000),
                )
            with self.assertRaisesRegex(ValueError, "active scheduler lease"):
                apply_state_retention(source, root / "active-output", _policy())
            with closing(sqlite3.connect(source / "scheduler.sqlite3")) as connection, connection:
                connection.execute("delete from scheduler_leases")
            before = _database_bytes(source)

            existing = root / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(ValueError, "must not already exist"):
                apply_state_retention(source, existing, _policy())
            with self.assertRaisesRegex(ValueError, "outside"):
                apply_state_retention(source, source / "nested", _policy())

            output = root / "failed-output"
            with patch(
                "skill2workflow.retention._purge_retained_copy",
                side_effect=OSError("injected private failure"),
            ):
                with self.assertRaisesRegex(OSError, "injected private failure"):
                    apply_state_retention(source, output, _policy())

            self.assertFalse(output.exists())
            self.assertEqual(_database_bytes(source), before)

    def test_real_process_retention_smoke_proves_disposal_and_service_cutover(self):
        with TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/retention_smoke.py",
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
        self.assertTrue(evidence["checks"]["active_service_blocked"])
        self.assertTrue(evidence["checks"]["source_preserved"])
        self.assertTrue(evidence["checks"]["terminal_data_removed"])
        self.assertTrue(evidence["checks"]["protected_state_preserved"])
        self.assertTrue(evidence["checks"]["retained_service_ready"])
        self.assertTrue(evidence["checks"]["retained_service_trigger"])
        self.assertTrue(evidence["checks"]["private_values_absent"])


def _policy():
    return {
        "schema_version": "skill2workflow-retention-policy-0.1.0",
        "retention": {
            "delete_before": "2026-01-01T00:00:00Z",
            "terminal_run_statuses": ["completed", "failed"],
            "terminal_dispatch_statuses": [
                "completed",
                "failed",
                "skipped",
                "uncertain",
            ],
        },
    }


def _policy_v2():
    return {
        "schema_version": "skill2workflow-retention-policy-0.2.0",
        "retention": {
            "delete_before": "2026-01-01T00:00:00Z",
            "terminal_run_statuses": ["completed", "failed", "cancelled"],
            "terminal_dispatch_statuses": [
                "completed",
                "failed",
                "skipped",
                "uncertain",
            ],
        },
    }


def _policy_v3():
    return {
        "schema_version": "skill2workflow-retention-policy-0.3.0",
        "retention": {
            "delete_before": "2026-01-01T00:00:00Z",
            "terminal_run_statuses": [
                "completed",
                "failed",
                "cancelled",
                "interrupted",
            ],
            "terminal_dispatch_statuses": [
                "completed",
                "failed",
                "skipped",
                "uncertain",
            ],
        },
    }


def _populate_retention_state(state_dir: Path):
    LocalControlPlane(state_dir, storage="sqlite")
    RecurringScheduleStore(state_dir)
    runs = [
        ("run_old_completed_private", "completed", "2025-01-01 00:00:00"),
        ("run_old_waiting_private", "waiting", "2025-01-01 00:00:00"),
        ("run_new_failed_private", "failed", "2027-01-01 00:00:00"),
    ]
    with closing(sqlite3.connect(state_dir / "runs.sqlite3")) as connection, connection:
        for run_id, status, updated_at in runs:
            state = {
                "run_id": run_id,
                "workflow_id": "workflow_retention_private",
                "workflow_version": "0.1.0",
                "status": status,
                "current_node": "private-node",
                "context": {
                    "customer": (
                        "private-old-customer-value"
                        if run_id == "run_old_completed_private"
                        else "private-protected-customer-value"
                    )
                },
                "events": [],
            }
            connection.execute(
                "insert into runs values (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    "workflow_retention_private",
                    "0.1.0",
                    status,
                    "private-node",
                    json.dumps(state),
                    updated_at,
                ),
            )
            connection.execute(
                "insert into run_events values (?, ?, ?, ?, ?, ?)",
                (run_id, 1, "private-event", "private-node", updated_at, "{}"),
            )
    with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection, connection:
        for index, (run_id, _, timestamp) in enumerate(runs, start=1):
            connection.execute(
                "insert into audit_events values (?, ?, ?, ?, ?, ?, ?)",
                (index, "run_event", "workflow_retention_private", "0.1.0", run_id, timestamp, "{}"),
            )
    dispatches = [
        ("dispatch_old_completed_private", "completed", "2025-01-01T00:00:00+00:00"),
        ("dispatch_old_claimed_private", "claimed", "2025-01-01T00:00:00+00:00"),
        ("dispatch_new_failed_private", "failed", "2027-01-01T00:00:00+00:00"),
    ]
    with closing(sqlite3.connect(state_dir / "scheduler.sqlite3")) as connection, connection:
        for dispatch_id, status, scheduled_for in dispatches:
            connection.execute(
                "insert into schedule_dispatches values (?, ?, ?, ?, ?, ?, ?)",
                (
                    dispatch_id,
                    f"schedule-{dispatch_id}",
                    scheduled_for,
                    status,
                    "owner-private",
                    0,
                    json.dumps({"dispatch_id": dispatch_id, "status": status}),
                ),
            )
    return _database_bytes(state_dir)


def _database_bytes(state_dir: Path):
    return {
        name: (state_dir / name).read_bytes()
        for name in ("control.sqlite3", "runs.sqlite3", "scheduler.sqlite3")
    }


def _waiting_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_cancel_retention",
            "name": "Cancellation retention",
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
