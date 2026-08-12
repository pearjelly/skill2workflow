import json
import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.backup import create_state_backup, restore_state_backup, verify_state_backup
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.migration import inspect_state_upgrade, upgrade_state
from skill2workflow.state_layout import (
    CURRENT_STATE_LAYOUT_VERSION,
    LEGACY_STATE_LAYOUT_VERSION,
    MAX_STATE_LAYOUT_MARKER_BYTES,
    STATE_LAYOUT_MARKER,
    ensure_service_state_layout,
    mark_service_state_initialized,
    validate_current_state_marker,
)


class StateMigrationTests(TestCase):
    def test_fresh_sqlite_state_is_explicitly_versioned(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            LocalControlPlane(state_dir, storage="sqlite")

            marker = json.loads((state_dir / STATE_LAYOUT_MARKER).read_text(encoding="utf-8"))
            state_mode = state_dir.stat().st_mode & 0o777

        self.assertEqual(marker["state_layout_version"], CURRENT_STATE_LAYOUT_VERSION)
        self.assertEqual(state_mode, 0o700)

    def test_runtime_rejects_legacy_and_future_state_without_mutating_it(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "legacy"
            _populate_state(legacy)
            (legacy / STATE_LAYOUT_MARKER).unlink()
            before = _database_bytes(legacy)

            with self.assertRaisesRegex(ValueError, "state-upgrade"):
                LocalControlPlane(legacy, storage="sqlite")
            self.assertEqual(_database_bytes(legacy), before)

            future = root / "future"
            _populate_state(future)
            marker_path = future / STATE_LAYOUT_MARKER
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            marker["state_layout_version"] = "skill2workflow-sqlite-layout-99.0.0"
            marker_path.write_text(json.dumps(marker), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported state layout"):
                LocalControlPlane(future, storage="sqlite")

    def test_inspect_and_upgrade_copy_legacy_state_with_required_backup(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "legacy"
            expected = _populate_state(source)
            (source / STATE_LAYOUT_MARKER).unlink()
            before = _database_bytes(source)
            output = root / "upgraded"
            backup = root / "pre-upgrade-backup"

            plan = inspect_state_upgrade(source)
            result = upgrade_state(source, output, backup)

            self.assertEqual(plan["status"], "upgrade_required")
            self.assertEqual(plan["source_layout_version"], LEGACY_STATE_LAYOUT_VERSION)
            self.assertEqual(plan["target_layout_version"], CURRENT_STATE_LAYOUT_VERSION)
            self.assertEqual(result["status"], "upgraded")
            self.assertEqual(_database_bytes(source), before)
            self.assertFalse((source / STATE_LAYOUT_MARKER).exists())
            self.assertTrue((output / STATE_LAYOUT_MARKER).is_file())
            self.assertEqual(verify_state_backup(backup)["status"], "valid")
            self.assertEqual(
                verify_state_backup(backup)["state_layout_version"],
                LEGACY_STATE_LAYOUT_VERSION,
            )
            restored = LocalControlPlane(output, storage="sqlite")
            self.assertEqual(restored.get_workflow("workflow_upgrade", "0.1.0"), expected)
            self.assertEqual(len(restored.list_runs()), 1)

    def test_upgrade_refuses_current_state_existing_outputs_and_active_lease(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "current"
            _populate_state(current)
            with self.assertRaisesRegex(ValueError, "already current"):
                upgrade_state(current, root / "unused", root / "unused-backup")

            legacy = root / "legacy"
            _populate_state(legacy)
            (legacy / STATE_LAYOUT_MARKER).unlink()
            existing = root / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(ValueError, "must not already exist"):
                upgrade_state(legacy, existing, root / "backup-a")
            with self.assertRaisesRegex(ValueError, "must not already exist"):
                upgrade_state(legacy, root / "output-a", existing)

            with closing(sqlite3.connect(legacy / "scheduler.sqlite3")) as connection, connection:
                connection.execute(
                    "insert into scheduler_leases (lease_name, owner_id, expires_at) values (?, ?, ?)",
                    ("recurring-dispatcher", "active", 4_000_000_000),
                )
                connection.commit()
            with self.assertRaisesRegex(ValueError, "active scheduler lease"):
                inspect_state_upgrade(legacy)
            with self.assertRaisesRegex(ValueError, "active scheduler lease"):
                upgrade_state(legacy, root / "output-b", root / "backup-b")

        self.assertFalse((root / "output-b").exists())
        self.assertFalse((root / "backup-b").exists())

    def test_preflight_rejects_incomplete_or_incompatible_legacy_state(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            incomplete = root / "incomplete"
            _populate_state(incomplete)
            (incomplete / STATE_LAYOUT_MARKER).unlink()
            (incomplete / "control.sqlite3").unlink()
            with self.assertRaisesRegex(ValueError, "SQLite database is missing"):
                inspect_state_upgrade(incomplete)

            incompatible = root / "incompatible"
            _populate_state(incompatible)
            (incompatible / STATE_LAYOUT_MARKER).unlink()
            with closing(sqlite3.connect(incompatible / "runs.sqlite3")) as connection, connection:
                connection.execute("alter table runs add column unexpected text")
                connection.commit()
            with self.assertRaisesRegex(ValueError, "incompatible layout"):
                inspect_state_upgrade(incompatible)

    def test_upgrade_synthesizes_scheduler_for_released_legacy_two_database_state(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "legacy-v0.1.0"
            expected = _populate_state(source)
            (source / STATE_LAYOUT_MARKER).unlink()
            (source / "scheduler.sqlite3").unlink()
            output = root / "upgraded"
            backup = root / "pre-upgrade-backup"

            plan = inspect_state_upgrade(source)
            result = upgrade_state(source, output, backup)
            manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))

            self.assertTrue(plan["scheduler_database_synthesized"])
            self.assertTrue(result["scheduler_database_synthesized"])
            self.assertTrue(manifest["scheduler_database_synthesized"])
            self.assertFalse((source / "scheduler.sqlite3").exists())
            self.assertTrue((output / "scheduler.sqlite3").is_file())
            restored = LocalControlPlane(output, storage="sqlite")
            self.assertEqual(restored.get_workflow("workflow_upgrade", "0.1.0"), expected)
            from skill2workflow.schedules import RecurringScheduleStore

            self.assertEqual(RecurringScheduleStore(output).list(), [])

    def test_current_marker_must_remain_owner_only(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            _populate_state(state_dir)
            (state_dir / STATE_LAYOUT_MARKER).chmod(0o644)

            with self.assertRaisesRegex(ValueError, "group or others"):
                LocalControlPlane(state_dir, storage="sqlite")

    def test_marker_read_is_descriptor_bound_against_path_replacement(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            marker_path = state_dir / STATE_LAYOUT_MARKER
            replacement = root / "replacement.json"
            replacement.write_bytes(marker_path.read_bytes())
            replacement.chmod(0o600)
            real_open = os.open
            swapped = False

            def swap_before_open(path, flags, *args):
                nonlocal swapped
                if Path(path) == marker_path and not swapped:
                    swapped = True
                    marker_path.unlink()
                    marker_path.symlink_to(replacement)
                return real_open(path, flags, *args)

            with patch(
                "skill2workflow.state_layout.os.open",
                side_effect=swap_before_open,
            ):
                with self.assertRaisesRegex(ValueError, "opened safely"):
                    validate_current_state_marker(state_dir)

        self.assertTrue(swapped)

    def test_marker_read_rejects_regular_file_identity_replacement(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            _populate_state(state_dir)
            marker_path = state_dir / STATE_LAYOUT_MARKER
            replacement = root / "replacement.json"
            replacement.write_bytes(marker_path.read_bytes())
            replacement.chmod(0o600)
            real_open = os.open
            swapped = False

            def replace_before_open(path, flags, *args):
                nonlocal swapped
                if Path(path) == marker_path and not swapped:
                    swapped = True
                    os.replace(replacement, marker_path)
                return real_open(path, flags, *args)

            with patch(
                "skill2workflow.state_layout.os.open",
                side_effect=replace_before_open,
            ):
                with self.assertRaisesRegex(ValueError, "opened safely"):
                    validate_current_state_marker(state_dir)

        self.assertTrue(swapped)

    def test_marker_read_rejects_oversized_document_before_json_decode(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            _populate_state(state_dir)
            marker_path = state_dir / STATE_LAYOUT_MARKER
            marker_path.write_bytes(b" " * (MAX_STATE_LAYOUT_MARKER_BYTES + 1))
            marker_path.chmod(0o600)

            with self.assertRaisesRegex(ValueError, "size limit"):
                validate_current_state_marker(state_dir)

    def test_service_layout_preflight_rejects_partial_marked_state(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            _populate_state(state_dir)
            mark_service_state_initialized(state_dir)
            (state_dir / "scheduler.sqlite3").unlink()

            with self.assertRaisesRegex(ValueError, "incomplete current state"):
                ensure_service_state_layout(state_dir)

    def test_upgrade_failure_leaves_source_and_destination_atomic_with_backup(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "legacy"
            _populate_state(source)
            (source / STATE_LAYOUT_MARKER).unlink()
            before = _database_bytes(source)
            output = root / "upgraded"
            backup = root / "pre-upgrade-backup"

            with patch(
                "skill2workflow.migration.write_state_layout_marker",
                side_effect=OSError("injected failure"),
            ):
                with self.assertRaisesRegex(OSError, "injected failure"):
                    upgrade_state(source, output, backup)
            self.assertEqual(_database_bytes(source), before)
            self.assertFalse(output.exists())
            self.assertTrue(backup.exists())

    def test_upgrade_rechecks_source_layout_at_backup_boundary(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "legacy"
            _populate_state(source)
            (source / STATE_LAYOUT_MARKER).unlink()
            output = root / "upgraded"
            backup = root / "pre-upgrade-backup"

            with patch(
                "skill2workflow.migration.create_state_backup",
                return_value={"state_layout_version": CURRENT_STATE_LAYOUT_VERSION},
            ):
                with self.assertRaisesRegex(ValueError, "source layout changed"):
                    upgrade_state(source, output, backup)

            self.assertFalse(output.exists())

    def test_post_commit_cleanup_failure_does_not_turn_published_upgrade_into_failure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "legacy"
            _populate_state(source)
            (source / STATE_LAYOUT_MARKER).unlink()
            output = root / "upgraded"
            backup = root / "pre-upgrade-backup"
            real_rmtree = shutil.rmtree

            def fail_only_after_publish(path, *args, **kwargs):
                candidate = Path(path)
                if output.exists() and candidate.name.startswith(".upgraded.upgrade-"):
                    raise OSError("post-commit cleanup unavailable")
                return real_rmtree(path, *args, **kwargs)

            with patch(
                "skill2workflow.migration.shutil.rmtree",
                side_effect=fail_only_after_publish,
            ):
                result = upgrade_state(source, output, backup)

            self.assertEqual(result["status"], "upgraded")
            self.assertTrue(output.is_dir())
            self.assertEqual(
                len(LocalControlPlane(output, storage="sqlite").list_runs()),
                1,
            )

    def test_backup_round_trip_preserves_current_or_legacy_layout_identity(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "current"
            _populate_state(current)
            current_backup = root / "current-backup"
            current_restored = root / "current-restored"
            current_created = create_state_backup(current, current_backup)
            restore_state_backup(current_backup, current_restored)

            legacy = root / "legacy"
            _populate_state(legacy)
            (legacy / STATE_LAYOUT_MARKER).unlink()
            legacy_backup = root / "legacy-backup"
            legacy_restored = root / "legacy-restored"
            legacy_created = create_state_backup(legacy, legacy_backup)
            restore_state_backup(legacy_backup, legacy_restored)
            self.assertEqual(
                current_created["state_layout_version"], CURRENT_STATE_LAYOUT_VERSION
            )
            self.assertTrue((current_restored / STATE_LAYOUT_MARKER).is_file())
            self.assertEqual(
                legacy_created["state_layout_version"], LEGACY_STATE_LAYOUT_VERSION
            )
            self.assertFalse((legacy_restored / STATE_LAYOUT_MARKER).exists())

    def test_real_process_upgrade_smoke_proves_service_and_rollback_boundary(self):
        with TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/state_upgrade_smoke.py",
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
        self.assertTrue(evidence["checks"]["preflight_detected_legacy"])
        self.assertTrue(evidence["checks"]["preupgrade_backup_verified"])
        self.assertTrue(evidence["checks"]["legacy_scheduler_synthesized"])
        self.assertTrue(evidence["checks"]["source_unchanged"])
        self.assertTrue(evidence["checks"]["upgraded_service_ready"])
        self.assertTrue(evidence["checks"]["upgraded_service_trigger"])
        self.assertTrue(evidence["checks"]["future_layout_rejected"])


def _populate_state(state_dir: Path):
    control = LocalControlPlane(state_dir, storage="sqlite")
    workflow = {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_upgrade",
            "name": "Upgrade state",
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
    control.publish_workflow(workflow)
    control.trigger_workflow(
        {
            "workflow_id": "workflow_upgrade",
            "version": "0.1.0",
            "source": "upgrade-test",
            "idempotency_key": "before-upgrade",
            "input": {"record": "preserved"},
        }
    )
    from skill2workflow.schedules import RecurringScheduleStore

    RecurringScheduleStore(state_dir)
    return control.get_workflow("workflow_upgrade", "0.1.0")


def _database_bytes(state_dir: Path):
    return {
        name: (state_dir / name).read_bytes()
        for name in ("control.sqlite3", "runs.sqlite3", "scheduler.sqlite3")
    }
