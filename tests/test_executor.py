import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.executor import LocalExecutor


class ExecutorTests(TestCase):
    def test_run_pauses_at_human_gate_and_resume_completes(self):
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {
                "id": "workflow_approval",
                "name": "approval",
                "version": "0.1.0",
                "status": "published",
            },
            "entry": "start",
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "title": "Start",
                    "on_success": "review",
                },
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
            "edges": [],
        }

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            self.assertEqual(waiting["status"], "waiting")
            self.assertEqual(waiting["current_node"], "review")

            completed = executor.resume(waiting["run_id"], approved=True)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["current_node"], "end")

    def test_resume_records_human_gate_result_and_terminal_result(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            completed = executor.resume(waiting["run_id"], approved=True)

        review_result = completed["node_results"]["review"]
        self.assertEqual(review_result["status"], "approved")
        self.assertEqual(review_result["title"], "Review")
        self.assertEqual(review_result["approved"], True)
        self.assertIn("timestamp", review_result)
        self.assertEqual(completed["node_results"]["end"]["status"], "completed")
        self.assertEqual(completed["node_results"]["end"]["title"], "End")

    def test_resume_rejection_records_human_gate_result_and_fails(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            failed = executor.resume(waiting["run_id"], approved=False)

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["current_node"], "failure")
        review_result = failed["node_results"]["review"]
        self.assertEqual(review_result["status"], "rejected")
        self.assertEqual(review_result["title"], "Review")
        self.assertEqual(review_result["approved"], False)
        self.assertIn("timestamp", review_result)
        self.assertEqual(failed["node_results"]["failure"]["status"], "failed")

    def test_list_runs_returns_control_plane_summaries(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            summary = executor.list_runs()[0]
            detail = executor.get_run(waiting["run_id"])

        self.assertEqual(
            summary,
            {
                "run_id": waiting["run_id"],
                "workflow_id": "workflow_approval",
                "workflow_version": "0.1.0",
                "status": "waiting",
                "current_node": "review",
                "event_count": 3,
                "node_result_count": 1,
            },
        )
        self.assertEqual(detail["run_id"], waiting["run_id"])
        self.assertIn("workflow", detail)
        self.assertIn("events", detail)
        self.assertIn("node_results", detail)

    def test_sqlite_storage_persists_run_state_and_event_rows_across_instances(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            waiting = LocalExecutor(state_dir, storage="sqlite").run(workflow)

            restarted = LocalExecutor(state_dir, storage="sqlite")
            detail = restarted.get_run(waiting["run_id"])
            completed = restarted.resume(waiting["run_id"], approved=True)
            summary = restarted.list_runs()[0]

            db_path = state_dir / "runs.sqlite3"
            with sqlite3.connect(db_path) as connection:
                event_rows = connection.execute(
                    "select event_type, node_id from run_events where run_id = ? order by sequence",
                    (waiting["run_id"],),
                ).fetchall()

        self.assertEqual(detail["status"], "waiting")
        self.assertEqual(detail["current_node"], "review")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["event_count"], len(event_rows))
        self.assertEqual(
            [row[0] for row in event_rows],
            [
                "node_started",
                "node_completed",
                "human_gate_waiting",
                "human_gate_resumed",
                "run_completed",
            ],
        )


def _approval_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_approval",
            "name": "approval",
            "version": "0.1.0",
            "status": "published",
        },
        "entry": "start",
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "title": "Start",
                "on_success": "review",
            },
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
        "edges": [],
    }
