import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.storage import SqliteControlStore, SqliteRunStore


class StorageTests(TestCase):
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
