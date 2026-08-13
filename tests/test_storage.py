import os
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.storage import SqliteControlStore, SqliteRunStore


class StorageTests(TestCase):
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


def _fd_dir():
    for path in ("/proc/self/fd", "/dev/fd"):
        if os.path.isdir(path):
            return path
    return None
