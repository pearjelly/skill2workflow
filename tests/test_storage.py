import os
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.storage import (
    JsonControlStore,
    JsonRunStore,
    MAX_AUDIT_EVENT_BYTES,
    MAX_JSON_CONTROL_INDEX_BYTES,
    MAX_JSON_RUN_STATE_BYTES,
    MAX_SQLITE_WORKFLOW_RECORD_BYTES,
    MAX_SQLITE_RUN_STATE_BYTES,
    SqliteControlStore,
    SqliteRunStore,
    _iter_foreign_active_execution_rows,
    _iter_interrupted_run_rows,
    _iter_workflow_records_for_id,
)


class StorageTests(TestCase):
    def test_audit_event_writes_reject_oversized_payloads_before_commit(self):
        event = {
            "type": "connector_failed",
            "workflow_id": "workflow_storage",
            "payload": "x" * MAX_AUDIT_EVENT_BYTES,
        }
        with TemporaryDirectory() as tmp:
            json_store = JsonControlStore(Path(tmp) / "json")
            sqlite_store = SqliteControlStore(Path(tmp) / "sqlite")
            for store in (json_store, sqlite_store):
                with self.assertRaisesRegex(
                    ValueError,
                    f"audit event exceeds {MAX_AUDIT_EVENT_BYTES} bytes",
                ):
                    store.append_audit(event)
            self.assertFalse((Path(tmp) / "json" / "audit.log.jsonl").exists())
            self.assertEqual(sqlite_store.list_audit_events(), [])

    def test_audit_event_batch_validates_before_partial_write(self):
        valid = {"type": "run_started", "run_id": "run_batch"}
        oversized = {
            "type": "connector_failed",
            "payload": "x" * MAX_AUDIT_EVENT_BYTES,
        }
        with TemporaryDirectory() as tmp:
            json_store = JsonControlStore(Path(tmp) / "json")
            sqlite_store = SqliteControlStore(Path(tmp) / "sqlite")
            for store in (json_store, sqlite_store):
                with self.assertRaisesRegex(ValueError, "audit event exceeds"):
                    store.append_audit_batch([valid, oversized])
            self.assertEqual(json_store.list_audit_events(), [])
            self.assertEqual(sqlite_store.list_audit_events(), [])

    def test_json_audit_read_rejects_oversized_event_before_decode(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "json" / "audit.log.jsonl"
            path.parent.mkdir(parents=True)
            path.write_bytes(
                b'{"type":"oversized","payload":"'
                + b"x" * MAX_AUDIT_EVENT_BYTES
                + b'"}\n'
            )
            store = JsonControlStore(Path(tmp) / "json")
            with self.assertRaisesRegex(
                ValueError,
                f"audit event exceeds {MAX_AUDIT_EVENT_BYTES} bytes",
            ):
                store.list_audit_events()

    def test_sqlite_audit_read_rejects_oversized_event_before_decode(self):
        with TemporaryDirectory() as tmp:
            store = SqliteControlStore(Path(tmp) / "sqlite")
            store.append_audit({"type": "run_started", "run_id": "run_read"})
            with store._connection() as connection:
                connection.execute(
                    "update audit_events set payload_json = ? where sequence = 1",
                    ("x" * (MAX_AUDIT_EVENT_BYTES + 1),),
                )
            with self.assertRaisesRegex(
                ValueError,
                f"audit event exceeds {MAX_AUDIT_EVENT_BYTES} bytes",
            ):
                store.list_audit_events()

    def test_json_run_state_save_rejects_oversized_payload(self):
        with TemporaryDirectory() as tmp:
            store = JsonRunStore(Path(tmp) / "json")
            with self.assertRaisesRegex(
                ValueError,
                f"JSON run state exceeds {MAX_JSON_RUN_STATE_BYTES} bytes",
            ):
                store.save(
                    {
                        "run_id": "run_oversized_state",
                        "payload": "x" * MAX_JSON_RUN_STATE_BYTES,
                    }
                )
            self.assertFalse(
                (Path(tmp) / "json" / "runs" / "run_oversized_state.json").exists()
            )

    def test_json_run_state_load_rejects_oversized_before_opening(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "json" / "runs" / "run_oversized_load.json"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"x" * (MAX_JSON_RUN_STATE_BYTES + 1))
            store = JsonRunStore(Path(tmp) / "json")

            with patch("skill2workflow.storage.os.open") as open_file:
                with self.assertRaisesRegex(
                    ValueError,
                    f"JSON run state exceeds {MAX_JSON_RUN_STATE_BYTES} bytes",
                ):
                    store.load("run_oversized_load")
            open_file.assert_not_called()

    def test_json_run_state_load_rejects_symlink_and_path_replacement(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "json" / "runs"
            root.mkdir(parents=True)
            path = root / "run_link.json"
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            path.symlink_to(outside)
            store = JsonRunStore(Path(tmp) / "json")

            with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                store.load("run_link")

            path.unlink()
            path.write_text("{}", encoding="utf-8")
            replacement = root / "replacement.json"
            replacement.write_text("{}", encoding="utf-8")
            real_open = os.open
            replaced = False

            def replace_before_open(open_path, flags, *args, **kwargs):
                nonlocal replaced
                if Path(open_path) == path and not replaced:
                    replaced = True
                    replacement.replace(path)
                return real_open(open_path, flags, *args, **kwargs)

            with patch(
                "skill2workflow.storage.os.open",
                side_effect=replace_before_open,
            ):
                with self.assertRaisesRegex(
                    ValueError, "JSON run state changed while being read"
                ):
                    store.load("run_link")

    def test_json_run_state_load_rejects_read_growth_past_bound(self):
        with TemporaryDirectory() as tmp:
            store = JsonRunStore(Path(tmp) / "json")
            path = Path(tmp) / "json" / "runs" / "run_growth.json"
            path.write_text("{}", encoding="utf-8")

            with patch(
                "skill2workflow.storage.os.read",
                return_value=b"x" * (MAX_JSON_RUN_STATE_BYTES + 1),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    f"JSON run state exceeds {MAX_JSON_RUN_STATE_BYTES} bytes",
                ):
                    store.load("run_growth")

    def test_sqlite_run_state_save_rejects_oversized_payload(self):
        with TemporaryDirectory() as tmp:
            store = SqliteRunStore(Path(tmp) / "sqlite")
            with self.assertRaisesRegex(
                ValueError,
                f"SQLite run state exceeds {MAX_SQLITE_RUN_STATE_BYTES} bytes",
            ):
                store.save(
                    {
                        "run_id": "run_oversized_sqlite_state",
                        "payload": "x" * MAX_SQLITE_RUN_STATE_BYTES,
                    }
                )
            self.assertEqual(store.count(), 0)

    def test_sqlite_run_state_load_rejects_oversized_document(self):
        with TemporaryDirectory() as tmp:
            store = SqliteRunStore(Path(tmp) / "sqlite")
            store.save(
                {
                    "run_id": "run_oversized_sqlite_load",
                    "status": "completed",
                    "events": [],
                }
            )
            with store._connection() as connection:
                connection.execute(
                    "update runs set state_json = ? where run_id = ?",
                    ("x" * (MAX_SQLITE_RUN_STATE_BYTES + 1), "run_oversized_sqlite_load"),
                )

            with self.assertRaisesRegex(
                ValueError,
                f"SQLite run state exceeds {MAX_SQLITE_RUN_STATE_BYTES} bytes",
            ):
                store.load("run_oversized_sqlite_load")

    def test_sqlite_run_state_load_rejects_malformed_or_non_object_document(self):
        with TemporaryDirectory() as tmp:
            store = SqliteRunStore(Path(tmp) / "sqlite")
            store.save(
                {
                    "run_id": "run_malformed_sqlite_state",
                    "status": "completed",
                    "events": [],
                }
            )
            with store._connection() as connection:
                connection.execute(
                    "update runs set state_json = ? where run_id = ?",
                    ("not-json", "run_malformed_sqlite_state"),
                )
            with self.assertRaisesRegex(ValueError, "SQLite run state is not valid JSON"):
                store.load("run_malformed_sqlite_state")

            with store._connection() as connection:
                connection.execute(
                    "update runs set state_json = ? where run_id = ?",
                    ("[]", "run_malformed_sqlite_state"),
                )
            with self.assertRaisesRegex(ValueError, "SQLite run state must be an object"):
                store.load("run_malformed_sqlite_state")

    def test_json_control_index_save_rejects_oversized_payload(self):
        with TemporaryDirectory() as tmp:
            store = JsonControlStore(Path(tmp) / "json")
            with self.assertRaisesRegex(
                ValueError,
                f"workflow index exceeds {MAX_JSON_CONTROL_INDEX_BYTES} bytes",
            ):
                store.save_index(
                    {
                        "workflow@1.0.0": {
                            "workflow_id": "workflow",
                            "version": "1.0.0",
                            "description": "x" * MAX_JSON_CONTROL_INDEX_BYTES,
                        }
                    }
                )
            self.assertFalse(
                (Path(tmp) / "json" / "workflows" / "index.json").exists()
            )

    def test_json_control_index_load_rejects_oversized_before_opening(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "json" / "workflows" / "index.json"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"x" * (MAX_JSON_CONTROL_INDEX_BYTES + 1))
            store = JsonControlStore(Path(tmp) / "json")

            with patch("skill2workflow.storage.os.open") as open_file:
                with self.assertRaisesRegex(
                    ValueError,
                    f"workflow index exceeds {MAX_JSON_CONTROL_INDEX_BYTES} bytes",
                ):
                    store.load_index()
            open_file.assert_not_called()

    def test_json_control_index_load_rejects_symlink_and_path_replacement(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "json" / "workflows"
            root.mkdir(parents=True)
            path = root / "index.json"
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            path.symlink_to(outside)
            store = JsonControlStore(Path(tmp) / "json")

            with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                store.load_index()

            path.unlink()
            path.write_text("{}", encoding="utf-8")
            replacement = root / "replacement.json"
            replacement.write_text("{}", encoding="utf-8")
            real_open = os.open
            replaced = False

            def replace_before_open(open_path, flags, *args, **kwargs):
                nonlocal replaced
                if Path(open_path) == path and not replaced:
                    replaced = True
                    replacement.replace(path)
                return real_open(open_path, flags, *args, **kwargs)

            with patch(
                "skill2workflow.storage.os.open",
                side_effect=replace_before_open,
            ):
                with self.assertRaisesRegex(
                    ValueError, "workflow index changed while being read"
                ):
                    store.load_index()

    def test_json_control_index_load_rejects_read_growth_past_bound(self):
        with TemporaryDirectory() as tmp:
            store = JsonControlStore(Path(tmp) / "json")
            path = Path(tmp) / "json" / "workflows" / "index.json"
            path.write_text("{}", encoding="utf-8")

            with patch(
                "skill2workflow.storage.os.read",
                return_value=b"x" * (MAX_JSON_CONTROL_INDEX_BYTES + 1),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    f"workflow index exceeds {MAX_JSON_CONTROL_INDEX_BYTES} bytes",
                    ):
                    store.load_index()

    def test_sqlite_workflow_record_writes_reject_oversized_payloads_before_commit(self):
        oversized = {
            "workflow_id": "workflow_registry",
            "name": "registry",
            "version": "1.0.0",
            "status": "published",
            "checksum": "abc",
            "artifact": "workflows/workflow_registry/1.0.0.json",
            "published_at": "2026-08-17T00:00:00Z",
            "description": "x" * MAX_SQLITE_WORKFLOW_RECORD_BYTES,
        }
        with TemporaryDirectory() as tmp:
            store = SqliteControlStore(Path(tmp) / "sqlite")
            with self.assertRaisesRegex(
                ValueError,
                f"SQLite workflow record exceeds {MAX_SQLITE_WORKFLOW_RECORD_BYTES} bytes",
            ):
                store.save_index({"workflow_registry@1.0.0": oversized})
            self.assertEqual(store.load_index(), {})

    def test_sqlite_workflow_record_batch_validates_before_replacing_index(self):
        existing = {
            "workflow_id": "workflow_registry",
            "name": "registry",
            "version": "1.0.0",
            "status": "published",
            "checksum": "abc",
            "artifact": "workflows/workflow_registry/1.0.0.json",
            "published_at": "2026-08-17T00:00:00Z",
        }
        oversized = dict(existing)
        oversized["version"] = "2.0.0"
        oversized["description"] = "x" * MAX_SQLITE_WORKFLOW_RECORD_BYTES
        with TemporaryDirectory() as tmp:
            store = SqliteControlStore(Path(tmp) / "sqlite")
            store.save_index({"workflow_registry@1.0.0": existing})
            with self.assertRaisesRegex(ValueError, "SQLite workflow record exceeds"):
                store.save_index(
                    {
                        "workflow_registry@1.0.0": existing,
                        "workflow_registry@2.0.0": oversized,
                    }
                )
            self.assertEqual(
                store.load_index(), {"workflow_registry@1.0.0": existing}
            )

    def test_sqlite_workflow_record_reads_reject_oversized_before_decode(self):
        with TemporaryDirectory() as tmp:
            store = SqliteControlStore(Path(tmp) / "sqlite")
            store.save_index(
                {
                    "workflow_registry@1.0.0": {
                        "workflow_id": "workflow_registry",
                        "name": "registry",
                        "version": "1.0.0",
                        "status": "published",
                        "checksum": "abc",
                        "artifact": "workflows/workflow_registry/1.0.0.json",
                        "published_at": "2026-08-17T00:00:00Z",
                    }
                }
            )
            with store._connection() as connection:
                connection.execute(
                    "update workflow_versions set record_json = ? where record_key = ?",
                    ("x" * (MAX_SQLITE_WORKFLOW_RECORD_BYTES + 1), "workflow_registry@1.0.0"),
                )
            with self.assertRaisesRegex(
                ValueError,
                f"SQLite workflow record exceeds {MAX_SQLITE_WORKFLOW_RECORD_BYTES} bytes",
            ):
                store.load_index()

    def test_sqlite_workflow_record_reads_reject_malformed_or_non_object_documents(self):
        with TemporaryDirectory() as tmp:
            store = SqliteControlStore(Path(tmp) / "sqlite")
            store.save_index(
                {
                    "workflow_registry@1.0.0": {
                        "workflow_id": "workflow_registry",
                        "name": "registry",
                        "version": "1.0.0",
                        "status": "published",
                        "checksum": "abc",
                        "artifact": "workflows/workflow_registry/1.0.0.json",
                        "published_at": "2026-08-17T00:00:00Z",
                    }
                }
            )
            with store._connection() as connection:
                connection.execute(
                    "update workflow_versions set record_json = ? where record_key = ?",
                    ("not-json", "workflow_registry@1.0.0"),
                )
            with self.assertRaisesRegex(
                ValueError, "SQLite workflow record is not valid JSON"
            ):
                store.load_index()

            with store._connection() as connection:
                connection.execute(
                    "update workflow_versions set record_json = ? where record_key = ?",
                    ("[]", "workflow_registry@1.0.0"),
                )
            with self.assertRaisesRegex(
                ValueError, "SQLite workflow record must be an object"
            ):
                store.load_index()

    def test_interrupted_execution_rows_stream_without_fetchall(self):
        with TemporaryDirectory() as tmp:
            store = SqliteRunStore(Path(tmp) / "sqlite")
            store.start_execution(
                {
                    "run_id": "run_stream_interrupted",
                    "workflow_id": "workflow_storage",
                    "workflow_version": "0.1.0",
                    "status": "running",
                    "current_node": "node",
                    "events": [],
                },
                owner_id="owner-a",
                execution_id="execution-a",
            )

            with closing(sqlite3.connect(store.db_path)) as raw:
                connection = _NoInterruptedFetchAllConnection(raw)
                with raw:
                    rows = list(_iter_foreign_active_execution_rows(connection, "owner-b"))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "run_stream_interrupted")

    def test_workflow_records_for_id_stream_without_fetchall(self):
        with TemporaryDirectory() as tmp:
            store = SqliteControlStore(Path(tmp) / "control")
            with store._connection() as connection:
                connection.execute(
                    """
                    insert into workflow_versions (
                        record_key, workflow_id, name, version, status, checksum,
                        artifact, published_at, deprecated_at, record_json
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "workflow_stream@1.0.0",
                        "workflow_stream",
                        "stream",
                        "1.0.0",
                        "published",
                        "checksum",
                        "workflows/workflow_stream/1.0.0.json",
                        "2026-08-14T00:00:00Z",
                        "",
                        '{"workflow_id":"workflow_stream","version":"1.0.0"}',
                    ),
                )
            with closing(sqlite3.connect(store.db_path)) as raw:
                connection = _NoRegistryFetchAllConnection(raw)
                with raw:
                    rows = list(_iter_workflow_records_for_id(connection, "workflow_stream"))

        self.assertEqual(rows[0][0], "workflow_stream@1.0.0")

    def test_interrupted_run_states_stream_without_fetchall(self):
        with TemporaryDirectory() as tmp:
            store = SqliteRunStore(Path(tmp) / "sqlite")
            store.save(
                {
                    "run_id": "run_stream_interrupted_state",
                    "workflow_id": "workflow_storage",
                    "workflow_version": "0.1.0",
                    "status": "interrupted",
                    "current_node": "node",
                    "events": [{"type": "run_interrupted"}],
                }
            )
            with closing(sqlite3.connect(store.db_path)) as raw:
                connection = _NoInterruptedStateFetchAllConnection(raw)
                with raw:
                    rows = list(_iter_interrupted_run_rows(connection))

        self.assertEqual(len(rows), 1)

    def test_run_count_does_not_load_all_states(self):
        with TemporaryDirectory() as tmp:
            stores = [JsonRunStore(Path(tmp) / "json"), SqliteRunStore(Path(tmp) / "sqlite")]
            for store in stores:
                store.save(
                    {
                        "run_id": "run_count",
                        "workflow_id": "workflow_storage",
                        "workflow_version": "0.1.0",
                        "status": "completed",
                        "events": [],
                    }
                )
                original_list = store.list
                store.list = lambda: (_ for _ in ()).throw(
                    AssertionError("unbounded run read")
                )
                try:
                    self.assertEqual(store.count(), 1)
                finally:
                    store.list = original_list

    def test_run_windows_are_bounded_and_ordered_by_latest_state_timestamp(self):
        states = [
            {
                "run_id": "run_zeta",
                "status": "completed",
                "events": [{"type": "run_completed", "timestamp": "2026-08-14T00:00:02Z"}],
            },
            {
                "run_id": "run_alpha",
                "status": "failed",
                "events": [{"type": "run_failed", "timestamp": "2026-08-14T00:00:03Z"}],
            },
            {
                "run_id": "run_middle",
                "status": "waiting",
                "events": [{"type": "run_waiting", "timestamp": "2026-08-14T00:00:01Z"}],
            },
        ]

        with TemporaryDirectory() as tmp:
            json_store = JsonRunStore(Path(tmp) / "json")
            sqlite_store = SqliteRunStore(Path(tmp) / "sqlite")
            for state in states:
                json_store.save(state)
                sqlite_store.save(state)
            with sqlite_store._connection() as connection:
                for state in states:
                    timestamp = next(iter(state["events"]))["timestamp"]
                    connection.execute(
                        "update runs set updated_at = ? where run_id = ?",
                        (timestamp, state["run_id"]),
                    )

            json_window = json_store.snapshot_window(2)
            json_list = json_store.list_bounded(2)
            sqlite_window = sqlite_store.snapshot_window(2)
            sqlite_list = sqlite_store.list_bounded(2)

        expected = ["run_zeta", "run_alpha"]
        self.assertEqual([item["run_id"] for item in json_window["items"]], expected)
        self.assertEqual([item["run_id"] for item in json_list], expected)
        self.assertEqual([item["run_id"] for item in sqlite_window["items"]], expected)
        self.assertEqual([item["run_id"] for item in sqlite_list], expected)
        self.assertEqual(json_window["total"], 3)
        self.assertEqual(sqlite_window["total"], 3)

    def test_run_list_window_rejects_invalid_limits(self):
        with TemporaryDirectory() as tmp:
            stores = [JsonRunStore(Path(tmp) / "json"), SqliteRunStore(Path(tmp) / "sqlite")]
            for store in stores:
                for limit in (0, -1, 1001, True, "2"):
                    with self.assertRaisesRegex(ValueError, "run list limit"):
                        store.list_bounded(limit)

    def test_sqlite_bounded_run_reads_use_compact_summary_projection(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            store = SqliteRunStore(state_dir)
            store.save(
                {
                    "run_id": "run_compact_summary",
                    "workflow_id": "workflow_storage",
                    "workflow_version": "1.0.0",
                    "status": "completed",
                    "current_node": "end",
                    "context": {"large": "payload"},
                    "node_results": {"start": {"status": "completed"}},
                    "events": [
                        {"type": "run_started", "timestamp": "2026-08-14T00:00:00Z"},
                        {"type": "run_completed", "timestamp": "2026-08-14T00:00:01Z"},
                    ],
                }
            )
            with store._connection() as connection:
                connection.execute(
                    "update runs set state_json = ? where run_id = ?",
                    ("not-json", "run_compact_summary"),
                )

            bounded = store.list_bounded(1)[0]
            window = store.snapshot_window(1)["items"][0]
            page = store.run_page(1)["items"][0]

        for summary in (bounded, window, page):
            self.assertEqual(summary["run_id"], "run_compact_summary")
            self.assertEqual(summary["event_count"], 2)
            self.assertEqual(summary["node_result_count"], 1)
            self.assertNotIn("context", summary)

    def test_audit_tail_limit_filters_before_bounding_for_json_and_sqlite(self):
        events = [
            {
                "type": event_type,
                "workflow_id": "workflow_audit" if index < 4 else "workflow_other",
                "workflow_version": "0.1.0",
                "run_id": "run_audit",
                "timestamp": f"2026-08-14T00:00:{index:02d}Z",
            }
            for index, event_type in enumerate(
                ("run_started", "connector_started", "connector_failed", "run_completed", "run_started")
            )
        ]

        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            json_store = JsonControlStore(state_dir / "json")
            sqlite_store = SqliteControlStore(state_dir / "sqlite")
            for event in events:
                json_store.append_audit(event)
                sqlite_store.append_audit(event)

            json_tail = json_store.list_audit_events(
                workflow_id="workflow_audit", limit=2
            )
            sqlite_tail = sqlite_store.list_audit_events(
                workflow_id="workflow_audit", limit=2
            )

        expected = ["connector_failed", "run_completed"]
        self.assertEqual([event["type"] for event in json_tail], expected)
        self.assertEqual([event["type"] for event in sqlite_tail], expected)

    def test_audit_tail_limit_rejects_non_positive_or_oversized_values(self):
        with TemporaryDirectory() as tmp:
            store = SqliteControlStore(Path(tmp))
            for limit in (0, -1, 1001, True, "2"):
                with self.assertRaisesRegex(ValueError, "audit event limit"):
                    store.list_audit_events(limit=limit)

    def test_sqlite_run_page_filters_and_returns_stable_cursor_window(self):
        with TemporaryDirectory() as tmp:
            store = SqliteRunStore(Path(tmp))
            for index, status in enumerate(("completed", "failed", "failed")):
                store.save(
                    {
                        "run_id": f"run_page_{index}",
                        "workflow_id": "workflow_page" if index < 2 else "workflow_other",
                        "workflow_version": "0.1.0",
                        "status": status,
                        "current_node": "end",
                        "events": [],
                    }
                )
            page = store.run_page(
                1,
                status="failed",
                workflow_id="workflow_page",
            )

        self.assertEqual(page["total"], 1)
        self.assertEqual(page["status_counts"], {"failed": 1})
        self.assertFalse(page["has_more"])
        self.assertEqual([item["run_id"] for item in page["items"]], ["run_page_1"])
        self.assertEqual(page["next_cursor"], None)

    def test_sqlite_run_page_cursor_continues_without_loading_all_runs(self):
        with TemporaryDirectory() as tmp:
            store = SqliteRunStore(Path(tmp))
            for index in range(3):
                store.save(
                    {
                        "run_id": f"run_cursor_{index}",
                        "workflow_id": "workflow_cursor",
                        "workflow_version": "0.1.0",
                        "status": "failed",
                        "current_node": "end",
                        "events": [],
                    }
                )
            first = store.run_page(2, workflow_id="workflow_cursor")
            cursor = first["next_cursor"]
            second = store.run_page(
                2,
                workflow_id="workflow_cursor",
                before_updated_at=cursor["updated_at"],
                before_run_id=cursor["run_id"],
            )

        self.assertEqual(first["total"], 3)
        self.assertTrue(first["has_more"])
        self.assertEqual([item["run_id"] for item in first["items"]], ["run_cursor_1", "run_cursor_2"])
        self.assertEqual([item["run_id"] for item in second["items"]], ["run_cursor_0"])
        self.assertFalse(second["has_more"])

    def test_sqlite_audit_page_filters_and_continues_with_sequence_cursor(self):
        with TemporaryDirectory() as tmp:
            store = SqliteControlStore(Path(tmp))
            for index, event_type in enumerate(("run_started", "connector_failed", "run_completed"), 1):
                store.append_audit(
                    {
                        "type": event_type,
                        "workflow_id": "workflow_audit_page",
                        "workflow_version": "0.1.0",
                        "run_id": "run_audit_page",
                        "timestamp": f"2026-08-17T00:00:0{index}Z",
                        "error": "private provider detail" if event_type == "connector_failed" else "",
                    }
                )
            first = store.audit_page(2, workflow_id="workflow_audit_page")
            second = store.audit_page(
                2,
                before_sequence=first["next_cursor"],
                workflow_id="workflow_audit_page",
            )
            failed = store.audit_page(2, event_type="connector_failed")

        self.assertEqual(first["total"], 3)
        self.assertTrue(first["has_more"])
        self.assertEqual([item["sequence"] for item in first["items"]], [2, 3])
        self.assertEqual([item["sequence"] for item in second["items"]], [1])
        self.assertFalse(second["has_more"])
        self.assertEqual(failed["total"], 1)
        self.assertEqual(failed["items"][0]["event"]["type"], "connector_failed")

    def test_sqlite_idempotent_audit_repair_is_atomic_across_concurrent_retries(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            stores = [SqliteControlStore(state_dir) for _ in range(2)]
            event = {
                "type": "run_cancel_requested",
                "run_id": "run_atomic_repair",
                "workflow_id": "workflow_storage",
                "workflow_version": "0.1.0",
                "timestamp": "2026-08-14T00:00:00Z",
            }
            threads = [
                threading.Thread(
                    target=store.append_audit_batch_if_missing,
                    args=([event],),
                )
                for store in stores
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2)
            persisted = stores[0].list_audit_events()
            integrity = stores[0].verify_audit_integrity()

        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0], event)
        self.assertEqual(integrity["status"], "valid")

    def test_sqlite_stores_close_operation_connections(self):
        fd_dir = _fd_dir()
        if fd_dir is None:
            self.skipTest("open file descriptor directory is unavailable")

        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            run_store = SqliteRunStore(state_dir)
            control_store = SqliteControlStore(state_dir)
            baseline = len(os.listdir(fd_dir))

            for index in range(20):
                run_id = f"run_{index}"
                run_store.save(
                    {
                        "run_id": run_id,
                        "workflow_id": "workflow_storage",
                        "workflow_version": "0.1.0",
                        "status": "completed",
                        "current_node": "end",
                        "events": [
                            {
                                "type": "run_completed",
                                "node_id": "end",
                                "timestamp": f"2026-07-07T00:00:{index:02d}Z",
                            }
                        ],
                    }
                )
                run_store.load(run_id)
                run_store.list()
                control_store.save_index(
                    {
                        f"workflow_storage@{index}": {
                            "workflow_id": "workflow_storage",
                            "name": "storage",
                            "version": str(index),
                            "status": "published",
                            "checksum": "abc",
                            "artifact": f"workflows/workflow_storage/{index}.json",
                            "published_at": "2026-07-07T00:00:00Z",
                            "deprecated_at": "",
                        }
                    }
                )
                control_store.load_index()
                control_store.append_audit(
                    {
                        "type": "workflow_published",
                        "workflow_id": "workflow_storage",
                        "workflow_version": str(index),
                        "timestamp": "2026-07-07T00:00:00Z",
                    }
                )
                control_store.list_audit_events()

            after = len(os.listdir(fd_dir))

        self.assertLessEqual(after - baseline, 2)


class _NoInterruptedFetchAllCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def __iter__(self):
        return iter(self._cursor)

    def fetchall(self):
        raise AssertionError("interrupted execution rows must be streamed")

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _NoInterruptedFetchAllConnection:
    def __init__(self, connection):
        self._connection = connection

    def execute(self, query, parameters=()):
        cursor = self._connection.execute(query, parameters)
        normalized = " ".join(str(query).lower().split())
        if "select e.run_id, r.state_json from run_executions" in normalized:
            return _NoInterruptedFetchAllCursor(cursor)
        return cursor


class _NoRegistryFetchAllCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def __iter__(self):
        return iter(self._cursor)

    def fetchall(self):
        raise AssertionError("workflow registry rows must be streamed")

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _NoRegistryFetchAllConnection:
    def __init__(self, connection):
        self._connection = connection

    def execute(self, query, parameters=()):
        cursor = self._connection.execute(query, parameters)
        normalized = " ".join(str(query).lower().split())
        if "select record_key, record_json from workflow_versions" in normalized:
            return _NoRegistryFetchAllCursor(cursor)
        return cursor


class _NoInterruptedStateFetchAllCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def __iter__(self):
        return iter(self._cursor)

    def fetchall(self):
        raise AssertionError("interrupted run states must be streamed")

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _NoInterruptedStateFetchAllConnection:
    def __init__(self, connection):
        self._connection = connection

    def execute(self, query, parameters=()):
        cursor = self._connection.execute(query, parameters)
        normalized = " ".join(str(query).lower().split())
        if "select state_json from runs where status = 'interrupted'" in normalized:
            return _NoInterruptedStateFetchAllCursor(cursor)
        return cursor


def _fd_dir():
    for path in ("/proc/self/fd", "/dev/fd"):
        if os.path.isdir(path):
            return path
    return None
