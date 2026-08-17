import os
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.storage import (
    JsonControlStore,
    JsonRunStore,
    SqliteControlStore,
    SqliteRunStore,
    _iter_foreign_active_execution_rows,
    _iter_interrupted_run_rows,
    _iter_workflow_records_for_id,
)


class StorageTests(TestCase):
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
