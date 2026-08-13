import json
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.backup import create_state_backup, restore_state_backup
from skill2workflow.cli import main
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.schedules import RecurringScheduleStore
from skill2workflow.storage import (
    _rebuild_audit_integrity_connection,
    _verify_audit_integrity_connection,
)


class AuditIntegrityTests(TestCase):
    def test_sqlite_audit_chain_is_valid_and_detects_payload_tampering(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            control.run_published_workflow("workflow_audit_integrity", "0.1.0")

            valid = control.verify_audit_integrity()
            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection, connection:
                payload = json.loads(
                    connection.execute(
                        "select payload_json from audit_events where sequence = 2"
                    ).fetchone()[0]
                )
                payload["tampered"] = True
                connection.execute(
                    "update audit_events set payload_json = ? where sequence = 2",
                    (json.dumps(payload),),
                )
            invalid = LocalControlPlane(state_dir, storage="sqlite").verify_audit_integrity()

        self.assertEqual(valid["status"], "valid")
        self.assertEqual(valid["algorithm"], "sha256-chain-v1")
        self.assertEqual(valid["event_count"], 3)
        self.assertEqual(len(valid["head_digest"]), 64)
        self.assertEqual(invalid["status"], "invalid")
        self.assertEqual(invalid["first_invalid_sequence"], 2)
        self.assertEqual(invalid["reason"], "digest_mismatch")
        self.assertNotIn("tampered", json.dumps(invalid))

    def test_audit_chain_survives_verified_backup_restore(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            control.run_published_workflow("workflow_audit_integrity", "0.1.0")
            RecurringScheduleStore(state_dir)
            backup_dir = root / "backup"
            restored_dir = root / "restored"

            create_state_backup(state_dir, backup_dir)
            restore_state_backup(backup_dir, restored_dir)
            result = LocalControlPlane(restored_dir, storage="sqlite").verify_audit_integrity()

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["event_count"], 3)

    def test_opening_legacy_sqlite_audit_rows_adds_integrity_columns(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection, connection:
                rows = connection.execute(
                    """
                    select sequence, event_type, workflow_id, workflow_version,
                           run_id, timestamp, payload_json
                    from audit_events order by sequence
                    """
                ).fetchall()
                connection.execute("alter table audit_events rename to audit_events_current")
                connection.execute(
                    """
                    create table audit_events (
                        sequence integer primary key autoincrement,
                        event_type text not null,
                        workflow_id text not null,
                        workflow_version text not null,
                        run_id text not null,
                        timestamp text not null,
                        payload_json text not null
                    )
                    """
                )
                connection.executemany(
                    "insert into audit_events values (?, ?, ?, ?, ?, ?, ?)", rows
                )
                connection.execute("drop table audit_events_current")
            migrated = LocalControlPlane(state_dir, storage="sqlite")
            result = migrated.verify_audit_integrity()
            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection:
                columns = {
                    row[1]
                    for row in connection.execute("pragma table_info(audit_events)").fetchall()
                }

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["event_count"], 1)
        self.assertIn("prev_digest", columns)
        self.assertIn("digest", columns)

    def test_audit_verify_cli_is_compact_and_fails_closed(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())

            from io import StringIO
            from unittest.mock import patch

            output = StringIO()
            with patch("sys.stdout", output):
                exit_code = main([
                    "audit-verify",
                    "--state-dir",
                    str(state_dir),
                    "--storage",
                    "sqlite",
                ])

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "valid")
        self.assertNotIn("workflow_audit_integrity", output.getvalue())

    def test_backup_rejects_a_tampered_current_audit_chain(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            RecurringScheduleStore(state_dir)
            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection, connection:
                connection.execute(
                    "update audit_events set payload_json = ? where sequence = 1",
                    (json.dumps({"type": "tampered"}),),
                )

            with self.assertRaisesRegex(ValueError, "audit integrity"):
                create_state_backup(state_dir, root / "backup")

    def test_audit_verification_detects_denormalized_column_tampering(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())
            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection, connection:
                connection.execute(
                    "update audit_events set event_type = 'tampered' where sequence = 1"
                )
            result = LocalControlPlane(state_dir, storage="sqlite").verify_audit_integrity()

        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["reason"], "column_mismatch")

    def test_audit_chain_verification_and_rebuild_stream_event_rows(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow())

            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as raw:
                connection = _NoAuditFetchAllConnection(raw)
                with raw:
                    _rebuild_audit_integrity_connection(connection)
                    result = _verify_audit_integrity_connection(connection)

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["event_count"], 1)


class _NoAuditFetchAllCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def __iter__(self):
        return iter(self._cursor)

    def fetchall(self):
        raise AssertionError("audit event rows must be streamed")

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _NoAuditFetchAllConnection:
    def __init__(self, connection):
        self._connection = connection

    def execute(self, query, parameters=()):
        cursor = self._connection.execute(query, parameters)
        normalized = " ".join(str(query).lower().split())
        if "from audit_events order by sequence" in normalized:
            return _NoAuditFetchAllCursor(cursor)
        return cursor


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_audit_integrity",
            "name": "Audit integrity",
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
