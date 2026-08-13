import hashlib
import json
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.backup import (
    BACKUP_RETENTION_PLAN_SCHEMA_VERSION,
    BACKUP_RETENTION_POLICY_SCHEMA_VERSION,
    BACKUP_LIST_SCHEMA_VERSION,
    BACKUP_SCHEMA_VERSION,
    STATE_LAYOUT_VERSION,
    build_backup_retention_plan,
    create_state_backup,
    inspect_state_backup_readiness,
    list_state_backups,
    normalize_backup_retention_policy,
    restore_state_backup,
    verify_state_backup,
)
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.schedules import RecurringScheduleDispatcher, RecurringScheduleStore


class StateBackupTests(TestCase):
    def test_backup_preserves_and_validates_cancellation_ledger(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_waiting_workflow())
            waiting = control.run_published_workflow("workflow_cancel_backup", "0.1.0")
            control.cancel_published_run(waiting["run_id"])
            RecurringScheduleStore(state_dir)
            backup_dir = root / "backup"
            restored_dir = root / "restored"

            create_state_backup(state_dir, backup_dir)
            restore_state_backup(backup_dir, restored_dir)
            with closing(sqlite3.connect(restored_dir / "runs.sqlite3")) as connection, connection:
                cancellation = connection.execute(
                    "select run_id, status from run_cancellations"
                ).fetchone()

        self.assertEqual(cancellation[0], waiting["run_id"])
        self.assertIn(cancellation[1], {"requested", "applied"})

    def test_backup_round_trip_preserves_trigger_idempotency_replay_safety(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            request = {
                "workflow_id": "workflow_backup",
                "version": "0.1.0",
                "source": "backup-test",
                "idempotency_key": "backup-event-001",
                "input": {"private_case": "must-not-be-in-ledger"},
            }
            first = control.trigger_workflow(request)
            RecurringScheduleStore(state_dir)
            backup_dir = root / "backup"
            restored_dir = root / "restored"
            create_state_backup(state_dir, backup_dir)
            restore_state_backup(backup_dir, restored_dir)
            restored = LocalControlPlane(restored_dir, storage="sqlite")
            replay = restored.trigger_workflow(request)
            with closing(sqlite3.connect(restored_dir / "control.sqlite3")) as connection:
                ledger = connection.execute(
                    "select status, response_json from trigger_idempotency"
                ).fetchall()

        self.assertEqual(replay, first)
        self.assertEqual(ledger[0][0], "completed")
        self.assertNotIn("must-not-be-in-ledger", json.dumps(ledger))

    def test_backup_rejects_malformed_optional_cancellation_ledger(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            _populate_state(state_dir)
            with closing(sqlite3.connect(state_dir / "runs.sqlite3")) as connection, connection:
                connection.execute("drop table run_cancellations")
                connection.execute("create table run_cancellations (run_id text)")
                connection.commit()

            with self.assertRaisesRegex(ValueError, "run_cancellations"):
                inspect_state_backup_readiness(state_dir)

    def test_backup_rejects_malformed_optional_trigger_idempotency_ledger(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            _populate_state(state_dir)
            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection, connection:
                connection.execute("drop table trigger_idempotency")
                connection.execute("create table trigger_idempotency (workflow_id text)")
                connection.commit()

            with self.assertRaisesRegex(ValueError, "trigger_idempotency"):
                inspect_state_backup_readiness(state_dir)

    def test_real_process_smoke_restores_snapshot_and_starts_service(self):
        with TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/backup_restore_smoke.py",
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
        self.assertTrue(evidence["checks"]["active_lease_blocked"])
        self.assertTrue(evidence["checks"]["verified_before_restore"])
        self.assertTrue(evidence["checks"]["point_in_time_snapshot"])
        self.assertTrue(evidence["checks"]["restored_service_ready"])
        self.assertTrue(evidence["checks"]["tampering_rejected"])
        self.assertTrue(evidence["checks"]["credentials_excluded"])

    def test_round_trip_preserves_control_runs_schedules_and_workflow_artifacts(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            expected = _populate_state(state_dir)
            backup_dir = root / "backup"
            restored_dir = root / "restored"

            created = create_state_backup(state_dir, backup_dir)
            verified = verify_state_backup(backup_dir)
            restored = restore_state_backup(backup_dir, restored_dir)

            control = LocalControlPlane(restored_dir, storage="sqlite")
            recurring = RecurringScheduleStore(restored_dir)
            restored_workflow = control.get_workflow("workflow_backup", "0.1.0")
            restored_run_ids = sorted(run["run_id"] for run in control.list_runs())
            restored_dispatches = recurring.list_dispatches("schedule_backup")

        self.assertEqual(created["schema_version"], BACKUP_SCHEMA_VERSION)
        self.assertEqual(created["state_layout_version"], STATE_LAYOUT_VERSION)
        self.assertEqual(created["status"], "created")
        self.assertEqual(verified["status"], "valid")
        self.assertEqual(restored["status"], "restored")
        self.assertEqual(restored_workflow, expected["workflow"])
        self.assertEqual(restored_run_ids, expected["run_ids"])
        self.assertEqual(len(restored_dispatches), 1)
        self.assertEqual(restored_dispatches[0]["status"], "completed")

    def test_backup_refuses_active_lease_or_output_inside_state(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            dispatcher = RecurringScheduleDispatcher(
                state_dir,
                owner_id="active-service",
                lease_seconds=30,
            )
            self.assertTrue(dispatcher.try_acquire(now_epoch=time.time()))
            try:
                with self.assertRaisesRegex(ValueError, "active scheduler lease"):
                    create_state_backup(state_dir, root / "active-backup")
            finally:
                dispatcher.release()

            with self.assertRaisesRegex(ValueError, "outside the state directory"):
                create_state_backup(state_dir, state_dir / "backup")

        self.assertFalse((root / "active-backup").exists())

    def test_backup_excludes_credentials_tokens_and_unreferenced_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            (state_dir / "ingress.token").write_text("must-not-be-backed-up", encoding="utf-8")
            credential_dir = state_dir / "credentials"
            credential_dir.mkdir()
            (credential_dir / "provider-key").write_text("must-not-be-backed-up", encoding="utf-8")
            (state_dir / "unrelated.txt").write_text("not-runtime-state", encoding="utf-8")
            backup_dir = root / "backup"

            create_state_backup(state_dir, backup_dir)
            manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
            paths = {entry["path"] for entry in manifest["files"]}
            serialized = json.dumps(manifest)

        self.assertNotIn("ingress.token", paths)
        self.assertFalse(any(path.startswith("credentials/") for path in paths))
        self.assertNotIn("unrelated.txt", paths)
        self.assertNotIn("must-not-be-backed-up", serialized)
        self.assertEqual(
            {"control.sqlite3", "runs.sqlite3", "scheduler.sqlite3"},
            {path for path in paths if path.endswith(".sqlite3")},
        )

    def test_tampering_is_rejected_before_restore_creates_destination(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            backup_dir = root / "backup"
            restored_dir = root / "restored"
            create_state_backup(state_dir, backup_dir)
            with (backup_dir / "runs.sqlite3").open("ab") as handle:
                handle.write(b"tampered")

            with self.assertRaisesRegex(ValueError, "size|checksum"):
                verify_state_backup(backup_dir)
            with self.assertRaisesRegex(ValueError, "size|checksum"):
                restore_state_backup(backup_dir, restored_dir)

        self.assertFalse(restored_dir.exists())

    def test_rehashed_workflow_tampering_still_conflicts_with_control_checksum(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            backup_dir = root / "backup"
            create_state_backup(state_dir, backup_dir)
            manifest_path = backup_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            workflow_entry = next(
                entry for entry in manifest["files"] if entry["kind"] == "workflow_artifact"
            )
            workflow_path = backup_dir / workflow_entry["path"]
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            workflow["workflow"]["name"] = "tampered but rehashed"
            workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
            workflow_entry["size_bytes"] = workflow_path.stat().st_size
            workflow_entry["sha256"] = hashlib.sha256(workflow_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "workflow artifact checksum"):
                verify_state_backup(backup_dir)

    def test_restore_rejects_existing_destination_and_unsafe_manifest_path(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            backup_dir = root / "backup"
            create_state_backup(state_dir, backup_dir)
            existing = root / "existing"
            existing.mkdir()

            with self.assertRaisesRegex(ValueError, "must not already exist"):
                restore_state_backup(backup_dir, existing)

            manifest_path = backup_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"][0]["path"] = "../escape.sqlite3"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe backup path"):
                verify_state_backup(backup_dir)

    def test_manifest_requires_the_current_sqlite_state_layout(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            backup_dir = root / "backup"
            create_state_backup(state_dir, backup_dir)
            manifest_path = backup_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["state_layout_version"], STATE_LAYOUT_VERSION)
            manifest["state_layout_version"] = "unsupported-layout"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "state_layout_version"):
                verify_state_backup(backup_dir)

    def test_manifest_cannot_claim_synthesized_scheduler_for_current_layout(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            backup_dir = root / "backup"
            create_state_backup(state_dir, backup_dir)
            manifest_path = backup_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["scheduler_database_synthesized"] = True
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "synthesized scheduler"):
                verify_state_backup(backup_dir)

    def test_restore_rechecks_each_copied_file_and_remains_atomic_on_race(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            backup_dir = root / "backup"
            restored_dir = root / "restored"
            create_state_backup(state_dir, backup_dir)
            copyfile = shutil.copyfile

            def copy_then_tamper(source, destination):
                result = copyfile(source, destination)
                if Path(destination).name == "runs.sqlite3":
                    with Path(destination).open("ab") as handle:
                        handle.write(b"changed-during-restore")
                return result

            with patch("skill2workflow.backup.shutil.copyfile", side_effect=copy_then_tamper):
                with self.assertRaisesRegex(ValueError, "changed during restore"):
                    restore_state_backup(backup_dir, restored_dir)

        self.assertFalse(restored_dir.exists())

    def test_backup_is_owner_only_and_clears_expired_lease_from_snapshot(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            expired = RecurringScheduleDispatcher(
                state_dir,
                owner_id="expired-owner",
                lease_seconds=2,
            )
            self.assertTrue(expired.try_acquire(now_epoch=1))
            backup_dir = root / "backup"
            restored_dir = root / "restored"

            create_state_backup(state_dir, backup_dir, now_epoch=10)
            restore_state_backup(backup_dir, restored_dir)
            replacement = RecurringScheduleDispatcher(
                restored_dir,
                owner_id="replacement-owner",
                lease_seconds=2,
            )
            acquired = replacement.try_acquire(now_epoch=10)
            file_modes = {
                stat.S_IMODE(path.stat().st_mode)
                for path in backup_dir.rglob("*")
                if path.is_file()
            }
            replacement.release()

        self.assertTrue(acquired)
        self.assertEqual(file_modes, {0o600})

    def test_verify_rejects_overexposed_backup_subdirectory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            backup_dir = root / "backup"
            create_state_backup(state_dir, backup_dir)
            (backup_dir / "workflows").chmod(0o755)

            with self.assertRaisesRegex(ValueError, "group or others"):
                verify_state_backup(backup_dir)

    def test_backup_list_is_bounded_and_reports_integrity_without_paths(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            parent = root / "backups"
            parent.mkdir()
            parent.chmod(0o700)
            _populate_state(state_dir)
            for name, timestamp in (
                ("backup_old", "2026-08-14T00:00:01+00:00"),
                ("backup_middle", "2026-08-14T00:00:02+00:00"),
                ("backup_new", "2026-08-14T00:00:03+00:00"),
            ):
                backup_dir = parent / name
                create_state_backup(state_dir, backup_dir)
                manifest_path = backup_dir / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["created_at"] = timestamp
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                manifest_path.chmod(0o600)

            result = list_state_backups(parent, limit=2)

        self.assertEqual(result["schema_version"], BACKUP_LIST_SCHEMA_VERSION)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["window"], {"max_items": 2, "returned": 2, "truncated": True})
        self.assertEqual([item["name"] for item in result["backups"]], ["backup_middle", "backup_new"])
        self.assertTrue(all(item["status"] == "valid" for item in result["backups"]))
        self.assertTrue(all("path" not in item for item in result["backups"]))

    def test_backup_list_reports_invalid_selected_sets_and_rejects_bad_limits(self):
        with TemporaryDirectory() as tmp:
            parent = Path(tmp) / "backups"
            parent.mkdir()
            parent.chmod(0o700)
            invalid = parent / "broken"
            invalid.mkdir()
            invalid.chmod(0o700)
            manifest = invalid / "manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            manifest.chmod(0o600)

            result = list_state_backups(parent, limit=1)
            for limit in (0, -1, 1001, True, "2"):
                with self.assertRaisesRegex(ValueError, "backup list limit"):
                    list_state_backups(parent, limit=limit)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["backups"][0]["status"], "invalid")
        self.assertEqual(result["backups"][0]["name"], "broken")

    def test_backup_retention_plan_preserves_minimum_and_invalid_sets(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            parent = root / "backups"
            parent.mkdir()
            parent.chmod(0o700)
            _populate_state(state_dir)
            for name, timestamp in (
                ("backup_old", "2026-08-14T00:00:01+00:00"),
                ("backup_middle", "2026-08-14T00:00:02+00:00"),
                ("backup_recent", "2026-08-14T00:00:03+00:00"),
                ("backup_new", "2026-08-14T00:00:04+00:00"),
            ):
                backup_dir = parent / name
                create_state_backup(state_dir, backup_dir)
                manifest_path = backup_dir / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["created_at"] = timestamp
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                manifest_path.chmod(0o600)
            invalid = parent / "broken"
            invalid.mkdir()
            invalid.chmod(0o700)
            (invalid / "manifest.json").write_text("{}", encoding="utf-8")
            (invalid / "manifest.json").chmod(0o600)

            result = build_backup_retention_plan(
                parent,
                {
                    "schema_version": BACKUP_RETENTION_POLICY_SCHEMA_VERSION,
                    "retention": {
                        "expire_before": "2026-08-14T00:00:03Z",
                        "minimum_keep": 2,
                    },
                },
            )

        self.assertEqual(result["schema_version"], BACKUP_RETENTION_PLAN_SCHEMA_VERSION)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["blocking_reasons"], [])
        self.assertEqual(result["summary"]["valid_backups"], 4)
        self.assertEqual(result["summary"]["invalid_backups"], 1)
        self.assertEqual(result["summary"]["eligible_backups"], 2)
        self.assertEqual(
            [item["name"] for item in result["candidates"]],
            ["backup_old", "backup_middle"],
        )
        preserved = {item["name"]: item["reason"] for item in result["preserved"]}
        self.assertEqual(preserved["backup_recent"], "minimum_keep")
        self.assertEqual(preserved["backup_new"], "minimum_keep")
        self.assertEqual(preserved["broken"], "invalid_backup")

    def test_backup_retention_plan_blocks_truncated_inventory_and_rejects_policy_shape(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            parent = root / "backups"
            parent.mkdir()
            parent.chmod(0o700)
            _populate_state(state_dir)
            for name in ("backup_old", "backup_new"):
                create_state_backup(state_dir, parent / name)
            policy = {
                "schema_version": BACKUP_RETENTION_POLICY_SCHEMA_VERSION,
                "retention": {
                    "expire_before": "2026-08-14T00:00:03Z",
                    "minimum_keep": 1,
                },
            }
            result = build_backup_retention_plan(parent, policy, limit=1)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["blocking_reasons"], ["inventory_truncated"])
            self.assertIsNone(result["summary"]["eligible_backups"])
            self.assertEqual(result["candidates"], [])

            for invalid_policy in (
                {},
                {
                    "schema_version": BACKUP_RETENTION_POLICY_SCHEMA_VERSION,
                    "retention": {
                        "expire_before": "2026-08-14T00:00:03Z",
                        "minimum_keep": 0,
                    },
                },
                {
                    "schema_version": BACKUP_RETENTION_POLICY_SCHEMA_VERSION,
                    "retention": {
                        "expire_before": "2026-08-14T00:00:03",
                        "minimum_keep": 1,
                    },
                },
            ):
                with self.assertRaisesRegex(ValueError, "backup retention"):
                    normalize_backup_retention_policy(invalid_policy)


def _populate_state(state_dir: Path):
    control = LocalControlPlane(state_dir, storage="sqlite")
    workflow = _workflow()
    control.publish_workflow(workflow)
    first = control.trigger_workflow(
        {
            "workflow_id": "workflow_backup",
            "version": "0.1.0",
            "source": "backup-test",
            "idempotency_key": "before-backup",
            "input": {"record": "preserved"},
        }
    )
    RecurringScheduleStore(state_dir).add(
        {
            "schema_version": "skill2workflow-schedule-0.2.0",
            "schedule": {
                "id": "schedule_backup",
                "workflow_id": "workflow_backup",
                "version": "0.1.0",
                "starts_at": "2026-08-11T00:00:00+00:00",
                "interval_seconds": 3600,
                "missed_run_policy": "latest",
            },
            "trigger": {"input": {}},
        }
    )
    dispatcher = RecurringScheduleDispatcher(
        state_dir,
        owner_id="backup-test-owner",
        lease_seconds=30,
    )
    dispatcher.try_acquire(now_epoch=100)
    second = dispatcher.dispatch_due("2026-08-11T00:00:00+00:00", now_epoch=101)
    dispatcher.release()
    published_workflow = control.get_workflow("workflow_backup", "0.1.0")
    return {
        "workflow": published_workflow,
        "run_ids": sorted([first["run_id"], second["runs"][0]["run_id"]]),
    }


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_backup",
            "name": "Backup round trip",
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


def _waiting_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_cancel_backup",
            "name": "Cancellation backup",
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
    build_backup_retention_plan,
