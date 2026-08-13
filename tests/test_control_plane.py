import json
import importlib.util
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.connectors import ConnectorRuntime, ExternalConnector
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.credentials import StaticCredentialProvider
from skill2workflow.triggers import TriggerIdempotencyError


class ControlPlaneTests(TestCase):
    def test_timeout_terminal_audit_contains_fixed_error_code(self):
        clock = _TestClock()
        workflow = _connector_workflow("8.0.0", "https://unused.invalid")
        workflow["policies"] = {"default_timeout_ms": 5}

        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(workflow)
            control.executor._clock = clock
            control.executor.connector_runtime = _AdvancingConnectorRuntime(clock)
            state = control.run_published_workflow("workflow_connector", "8.0.0")
            events = control.list_audit_events(run_id=state["run_id"])

        self.assertEqual(state["status"], "failed")
        self.assertEqual(events[-1]["type"], "run_failed")
        self.assertEqual(events[-1]["error_code"], "execution_timeout")

    def test_ingress_authentication_audit_is_strictly_allowlisted(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")

            control.record_ingress_authentication(
                False,
                "POST secret-method",
                "secret-route",
                reason="secret-reason",
            )
            event = control.list_audit_events()[0]

        self.assertEqual(
            event,
            {
                "type": "ingress_authentication_denied",
                "method": "OTHER",
                "route": "unknown",
                "reason": "unspecified",
                "timestamp": event["timestamp"],
            },
        )

    def test_human_gate_resume_is_a_persisted_ingress_route_class(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.record_ingress_authentication(True, "POST", "run_resume")
            event = control.list_audit_events()[0]

        self.assertEqual(event["type"], "ingress_authenticated")
        self.assertEqual(event["method"], "POST")
        self.assertEqual(event["route"], "run_resume")

    def test_recurring_schedule_change_audit_is_bounded_and_allowlisted(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.record_recurring_schedule_change(
                "schedule_hourly_report",
                enabled=False,
                changed=True,
            )
            event = control.list_audit_events()[0]

        self.assertEqual(
            set(event), {"type", "schedule_id", "enabled", "changed", "timestamp"}
        )
        self.assertEqual(event["type"], "recurring_schedule_updated")
        self.assertEqual(event["schedule_id"], "schedule_hourly_report")
        self.assertFalse(event["enabled"])
        self.assertTrue(event["changed"])

    def test_publish_workflow_persists_immutable_version_and_audit(self):
        workflow = _workflow(version="1.0.0")

        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            record = control.publish_workflow(workflow)
            stored = control.get_workflow("workflow_control", "1.0.0")
            audit_events = control.list_audit_events()

            changed = _workflow(version="1.0.0")
            changed["nodes"][0]["title"] = "Changed Start"
            with self.assertRaisesRegex(ValueError, "immutable"):
                control.publish_workflow(changed)

        self.assertEqual(record["workflow_id"], "workflow_control")
        self.assertEqual(record["version"], "1.0.0")
        self.assertEqual(record["status"], "published")
        self.assertEqual(stored["workflow"]["status"], "published")
        self.assertEqual(audit_events[0]["type"], "workflow_published")
        self.assertEqual(audit_events[0]["workflow_id"], "workflow_control")
        self.assertIn("checksum", record)

    def test_sqlite_concurrent_publication_preserves_each_version_and_audit(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            bootstrap = LocalControlPlane(state_dir, storage="sqlite")
            bootstrap.publish_workflow(_workflow(version="1.0.0"))
            barrier = threading.Barrier(2)
            published_versions = []
            failures = []

            def publish(version):
                operator = LocalControlPlane(state_dir, storage="sqlite")
                barrier.wait()
                try:
                    operator.publish_workflow(_workflow(version=version))
                except BaseException as error:
                    failures.append(error)
                else:
                    published_versions.append(version)

            threads = [
                threading.Thread(target=publish, args=(version,))
                for version in ("2.0.0", "3.0.0")
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            records = {
                record["version"]: record for record in bootstrap.list_workflows()
            }
            audits = bootstrap.list_audit_events()

        self.assertEqual(sorted(published_versions), ["2.0.0", "3.0.0"])
        self.assertEqual(failures, [])
        self.assertEqual(
            sorted(records), ["1.0.0", "2.0.0", "3.0.0"]
        )
        self.assertEqual(
            [event["type"] for event in audits].count("workflow_published"),
            3,
        )

    def test_sqlite_concurrent_same_version_publication_is_idempotent(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            workflow = _workflow(version="1.0.0")
            barrier = threading.Barrier(2)
            results = []
            failures = []

            def publish():
                operator = LocalControlPlane(state_dir, storage="sqlite")
                barrier.wait()
                try:
                    results.append(operator.publish_workflow(workflow))
                except BaseException as error:
                    failures.append(error)

            threads = [threading.Thread(target=publish) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            records = LocalControlPlane(state_dir, storage="sqlite").list_workflows()
            audits = LocalControlPlane(state_dir, storage="sqlite").list_audit_events()

        self.assertEqual(len(results), 2)
        self.assertEqual(failures, [])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["version"], "1.0.0")
        self.assertEqual(
            [event["type"] for event in audits].count("workflow_published"),
            1,
        )

    def test_concurrent_different_content_same_version_fails_closed(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            LocalControlPlane(state_dir, storage="sqlite")
            first = _workflow(version="1.0.0")
            second = _workflow(version="1.0.0")
            second["nodes"][0]["title"] = "Different immutable release"
            barrier = threading.Barrier(2)
            successes = []
            failures = []

            def publish(workflow):
                operator = LocalControlPlane(state_dir, storage="sqlite")
                barrier.wait()
                try:
                    successes.append(operator.publish_workflow(workflow))
                except ValueError as error:
                    failures.append(str(error))

            threads = [
                threading.Thread(target=publish, args=(workflow,))
                for workflow in (first, second)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            control = LocalControlPlane(state_dir, storage="sqlite")
            record = control.list_workflows()[0]
            stored = control.get_workflow("workflow_control", "1.0.0")

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIn("published workflow version is immutable", failures[0])
        self.assertEqual(record["version"], "1.0.0")
        self.assertIn(
            stored["nodes"][0]["title"],
            {"Start", "Different immutable release"},
        )

    def test_sqlite_publication_rolls_back_registry_when_audit_append_fails(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            with patch(
                "skill2workflow.storage._append_audit_connection",
                side_effect=RuntimeError("audit append failed"),
            ):
                with self.assertRaisesRegex(RuntimeError, "audit append failed"):
                    control.publish_workflow(_workflow(version="1.0.0"))

            self.assertEqual(control.list_workflows(), [])
            self.assertEqual(control.list_audit_events(), [])
            self.assertFalse(
                (state_dir / "workflows" / "workflow_control" / "1.0.0.json").exists()
            )
            record = control.publish_workflow(_workflow(version="1.0.0"))

        self.assertEqual(record["version"], "1.0.0")

    def test_published_run_audit_batch_is_all_or_nothing(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0"))
            with patch(
                "skill2workflow.storage._append_audit_connection",
                side_effect=[None, RuntimeError("run audit append failed")],
            ):
                with self.assertRaisesRegex(RuntimeError, "run audit append failed"):
                    control.run_published_workflow("workflow_control", "1.0.0")

            runs = control.list_runs()
            audit_types = [event["type"] for event in control.list_audit_events()]

        self.assertEqual(runs[0]["status"], "completed")
        self.assertEqual(audit_types, ["workflow_published"])

    def test_run_audit_consistency_report_detects_missing_and_duplicate_events(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0"))
            state = control.run_published_workflow("workflow_control", "1.0.0")
            run_id = state["run_id"]

            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection, connection:
                connection.execute(
                    "delete from audit_events where run_id = ? and event_type = 'run_completed'",
                    (run_id,),
                )
            control.store.append_audit(
                {
                    "type": "run_started",
                    "run_id": run_id,
                    "workflow_id": "workflow_control",
                    "workflow_version": "1.0.0",
                    "timestamp": "synthetic-duplicate",
                }
            )

            report = control.inspect_run_audit(run_id=run_id)

        self.assertEqual(
            report["schema_version"],
            "skill2workflow-run-audit-report-0.1.0",
        )
        self.assertEqual(report["status"], "attention")
        self.assertEqual(report["summary"]["checked_runs"], 1)
        run_report = report["runs"][0]
        self.assertEqual(run_report["missing"], [{"type": "run_completed", "count": 1}])
        self.assertEqual(run_report["duplicate"], [{"type": "run_started", "count": 1}])
        self.assertEqual(run_report["unexpected"], [])
        self.assertNotIn("synthetic-duplicate", json.dumps(report))

    def test_run_audit_consistency_report_is_clean_for_waiting_and_resumed_run(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_approval_workflow(version="1.0.0"))
            waiting = control.run_published_workflow("workflow_control", "1.0.0")
            control.resume_published_run(waiting["run_id"], approved=True)

            report = control.inspect_run_audit()

        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["summary"]["checked_runs"], 1)
        self.assertEqual(report["summary"]["attention_runs"], 0)

    def test_run_audit_consistency_report_is_clean_for_waiting_run(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_approval_workflow(version="1.1.0"))
            waiting = control.run_published_workflow("workflow_control", "1.1.0")

            report = control.inspect_run_audit(run_id=waiting["run_id"])

        self.assertEqual(waiting["status"], "waiting")
        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["summary"]["attention_runs"], 0)

    def test_run_audit_consistency_report_is_clean_for_interrupted_run(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.2.0"))
            state = control.run_published_workflow("workflow_control", "1.2.0")
            state["status"] = "interrupted"
            state["events"] = [
                {
                    "type": "run_interrupted",
                    "node_id": "start",
                    "timestamp": "2026-08-14T00:00:01Z",
                }
            ]
            control.executor.store.save(state)
            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection:
                connection.execute(
                    "delete from audit_events where run_id = ?",
                    (state["run_id"],),
                )
                connection.commit()
            control.store.append_audit_batch(
                [
                    {
                        "type": "run_started",
                        "run_id": state["run_id"],
                        "workflow_id": "workflow_control",
                        "workflow_version": "1.2.0",
                        "timestamp": "2026-08-14T00:00:00Z",
                    },
                    {
                        "type": "run_interrupted",
                        "run_id": state["run_id"],
                        "workflow_id": "workflow_control",
                        "workflow_version": "1.2.0",
                        "timestamp": "2026-08-14T00:00:01Z",
                    },
                ]
            )

            report = control.inspect_run_audit(run_id=state["run_id"])

        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["summary"]["attention_runs"], 0)

    def test_workflow_artifact_report_is_bounded_and_finds_registry_and_orphan_gaps(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0"))
            control.publish_workflow(_workflow(version="2.0.0"))

            missing = state_dir / "workflows" / "workflow_control" / "1.0.0.json"
            missing.unlink()
            tampered = state_dir / "workflows" / "workflow_control" / "2.0.0.json"
            tampered.write_text("{}", encoding="utf-8")
            orphan = state_dir / "workflows" / "orphan" / "0.1.0.json"
            orphan.parent.mkdir(parents=True)
            orphan.write_text("{}", encoding="utf-8")

            report = control.inspect_workflow_artifacts()

        self.assertEqual(
            report["schema_version"],
            "skill2workflow-workflow-artifact-report-0.1.0",
        )
        self.assertEqual(report["status"], "attention")
        self.assertEqual(report["summary"]["registry_records"], 2)
        self.assertEqual(report["summary"]["filesystem_artifacts"], 2)
        self.assertEqual(report["summary"]["missing"], 1)
        self.assertEqual(report["summary"]["checksum_mismatch"], 1)
        self.assertEqual(report["summary"]["orphaned"], 1)
        self.assertFalse(report["summary"]["truncated"])
        self.assertEqual(
            [issue["kind"] for issue in report["issues"]],
            ["checksum_mismatch", "missing", "orphaned"],
        )

    def test_workflow_artifact_report_ignores_json_control_index_and_accepts_clean_state(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="json")
            control.publish_workflow(_workflow(version="1.0.0"))

            report = control.inspect_workflow_artifacts()

        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["summary"]["registry_records"], 1)
        self.assertEqual(report["summary"]["filesystem_artifacts"], 1)
        self.assertEqual(report["summary"]["healthy"], 1)
        self.assertEqual(report["issues"], [])

    def test_workflow_artifact_report_truncates_issue_records_without_values(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="json")
            orphan_dir = state_dir / "workflows" / "orphan"
            orphan_dir.mkdir(parents=True)
            for index in range(300):
                (orphan_dir / f"{index:03d}.json").write_text(
                    json.dumps({"secret": "do-not-print"}), encoding="utf-8"
                )

            report = control.inspect_workflow_artifacts()
            encoded = json.dumps(report, ensure_ascii=False)

        self.assertEqual(report["status"], "attention")
        self.assertEqual(report["summary"]["orphaned"], 300)
        self.assertEqual(report["summary"]["issue_count"], 300)
        self.assertTrue(report["summary"]["truncated"])
        self.assertEqual(len(report["issues"]), 256)
        self.assertNotIn("do-not-print", encoded)

    def test_workflow_artifact_report_redacts_unsafe_registry_path(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="json")
            control.publish_workflow(_workflow(version="1.0.0"))
            index_path = state_dir / "workflows" / "index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["workflow_control@1.0.0"]["artifact"] = "secret-token"
            index_path.write_text(json.dumps(index), encoding="utf-8")

            report = control.inspect_workflow_artifacts()

        unsafe = next(
            issue for issue in report["issues"] if issue["kind"] == "unsafe_reference"
        )
        self.assertEqual(unsafe["artifact"], "<invalid>")
        self.assertNotIn("secret-token", json.dumps(report))

    def test_sqlite_publish_rejects_symlinked_artifact_path(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symbolic links are unavailable")
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            target = state_dir / "outside.json"
            target.write_text(json.dumps(_workflow(version="1.0.0")), encoding="utf-8")
            artifact = state_dir / "workflows" / "workflow_control" / "1.0.0.json"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            try:
                artifact.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symbolic links cannot be created")

            with self.assertRaisesRegex(ValueError, "artifact unavailable"):
                control.publish_workflow(_workflow(version="1.0.0"))

            self.assertEqual(control.list_workflows(), [])

    def test_sqlite_known_failure_cleanup_never_removes_registered_artifact(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            record = control.publish_workflow(_workflow(version="1.0.0"))
            artifact = state_dir / record["artifact"]

            removed = control.store.cleanup_unregistered_artifact(
                "workflow_control@1.0.0",
                artifact,
                record["checksum"],
            )
            still_exists = artifact.exists()

        self.assertFalse(removed)
        self.assertTrue(still_exists)

    def test_sqlite_concurrent_publication_and_deprecation_preserve_both_mutations(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            bootstrap = LocalControlPlane(state_dir, storage="sqlite")
            bootstrap.publish_workflow(_workflow(version="1.0.0"))
            barrier = threading.Barrier(2)
            failures = []

            def publish_new_version():
                operator = LocalControlPlane(state_dir, storage="sqlite")
                barrier.wait()
                try:
                    operator.publish_workflow(_workflow(version="2.0.0"))
                except BaseException as error:
                    failures.append(error)

            def deprecate_old_version():
                operator = LocalControlPlane(state_dir, storage="sqlite")
                barrier.wait()
                try:
                    operator.deprecate_workflow("workflow_control", "1.0.0")
                except BaseException as error:
                    failures.append(error)

            threads = [
                threading.Thread(target=publish_new_version),
                threading.Thread(target=deprecate_old_version),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            records = {
                record["version"]: record for record in bootstrap.list_workflows()
            }

        self.assertEqual(failures, [])
        self.assertEqual(records["1.0.0"]["status"], "deprecated")
        self.assertEqual(records["2.0.0"]["status"], "published")

    def test_sqlite_deprecation_rolls_back_registry_when_audit_append_fails(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0"))
            with patch(
                "skill2workflow.storage._append_audit_connection",
                side_effect=RuntimeError("audit append failed"),
            ):
                with self.assertRaisesRegex(RuntimeError, "audit append failed"):
                    control.deprecate_workflow("workflow_control", "1.0.0")

            record = control.list_workflows()[0]
            audits = control.list_audit_events()

        self.assertEqual(record["status"], "published")
        self.assertEqual(
            [event["type"] for event in audits].count("workflow_deprecated"),
            0,
        )

    def test_tampered_published_artifact_is_rejected_before_execution(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            record = control.publish_workflow(_workflow(version="1.0.0"))
            artifact_path = state_dir / record["artifact"]
            tampered = json.loads(artifact_path.read_text(encoding="utf-8"))
            tampered["nodes"][0]["title"] = "Tampered start"
            artifact_path.write_text(
                json.dumps(tampered, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "published workflow artifact checksum mismatch"):
                control.get_workflow("workflow_control", "1.0.0")
            with self.assertRaisesRegex(ValueError, "published workflow artifact checksum mismatch"):
                control.run_published_workflow("workflow_control", "1.0.0")
            with self.assertRaisesRegex(ValueError, "published workflow artifact checksum mismatch"):
                control.trigger_workflow(
                    {
                        "workflow_id": "workflow_control",
                        "version": "1.0.0",
                        "idempotency_key": "tampered-001",
                        "input": {},
                    }
                )

            self.assertEqual(control.list_runs(), [])
            self.assertEqual(
                [event["type"] for event in control.list_audit_events()],
                ["workflow_published"],
            )

    def test_tampered_published_artifact_cannot_be_promoted(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            first = control.publish_workflow(_workflow(version="1.0.0"))
            second = control.publish_workflow(_workflow(version="2.0.0"))
            control.promote_workflow("workflow_control", "1.0.0", alias="production")
            artifact_path = state_dir / second["artifact"]
            tampered = json.loads(artifact_path.read_text(encoding="utf-8"))
            tampered["nodes"][0]["title"] = "Tampered release"
            artifact_path.write_text(
                json.dumps(tampered, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "published workflow artifact checksum mismatch"):
                control.promote_workflow("workflow_control", "2.0.0", alias="production")

            records = {record["version"]: record for record in control.list_workflows()}
            self.assertEqual(records["1.0.0"]["aliases"], ["production"])
            self.assertNotIn("aliases", records["2.0.0"])
            self.assertEqual(
                [event["type"] for event in control.list_audit_events()],
                ["workflow_published", "workflow_published", "workflow_promoted"],
            )

    def test_workflow_diff_is_structural_and_does_not_expose_node_values(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            first = _workflow(version="1.0.0")
            second = _workflow(version="2.0.0")
            second["workflow"]["name"] = "Changed customer workflow"
            second["nodes"][0]["title"] = "Private customer escalation text"
            second["policies"] = {"default_timeout_ms": 5000}
            control.publish_workflow(first)
            control.publish_workflow(second)

            diff = control.diff_workflow_versions(
                "workflow_control", "1.0.0", "2.0.0"
            )
            serialized = json.dumps(diff, ensure_ascii=False)

        self.assertEqual(diff["schema_version"], "skill2workflow-workflow-diff-0.1.0")
        self.assertEqual(diff["workflow_id"], "workflow_control")
        self.assertEqual(diff["from"]["version"], "1.0.0")
        self.assertEqual(diff["to"]["version"], "2.0.0")
        self.assertTrue(diff["changed"])
        self.assertEqual(diff["changes"]["sections"], ["workflow", "policies", "nodes"])
        self.assertEqual(diff["changes"]["nodes"]["changed"], ["start"])
        self.assertNotIn("Private customer escalation text", serialized)
        self.assertNotIn("Changed customer workflow", serialized)

    def test_promotion_expected_version_precondition_is_compare_and_swap(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0"))
            control.publish_workflow(_workflow(version="2.0.0"))
            control.promote_workflow("workflow_control", "1.0.0", alias="production")
            promoted = control.promote_workflow(
                "workflow_control",
                "2.0.0",
                alias="production",
                expected_current_version="1.0.0",
            )

            with self.assertRaisesRegex(ValueError, "workflow alias precondition failed"):
                control.promote_workflow(
                    "workflow_control",
                    "1.0.0",
                    alias="production",
                    expected_current_version="1.0.0",
                )

            records = {record["version"]: record for record in control.list_workflows()}
            audit_types = [event["type"] for event in control.list_audit_events()]

        self.assertEqual(promoted["aliases"], ["production"])
        self.assertNotIn("aliases", records["1.0.0"])
        self.assertEqual(records["2.0.0"]["aliases"], ["production"])
        self.assertEqual(audit_types.count("workflow_promoted"), 2)

    def test_repeating_same_promotion_is_a_noop_without_duplicate_audit(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0"))
            control.promote_workflow("workflow_control", "1.0.0", alias="production")
            first_audit_count = len(control.list_audit_events())
            repeated = control.promote_workflow(
                "workflow_control",
                "1.0.0",
                alias="production",
                expected_current_version="1.0.0",
            )
            second_audit_count = len(control.list_audit_events())
            with self.assertRaisesRegex(ValueError, "workflow alias precondition failed"):
                control.promote_workflow(
                    "workflow_control",
                    "1.0.0",
                    alias="production",
                    expected_current_version="0.9.0",
                )

        self.assertEqual(repeated["aliases"], ["production"])
        self.assertEqual(second_audit_count, first_audit_count)

    def test_sqlite_promotion_cas_is_atomic_across_concurrent_operators(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            bootstrap = LocalControlPlane(state_dir, storage="sqlite")
            for version in ("1.0.0", "2.0.0", "3.0.0"):
                bootstrap.publish_workflow(_workflow(version=version))
            bootstrap.promote_workflow(
                "workflow_control", "1.0.0", alias="production"
            )

            barrier = threading.Barrier(2)
            successes = []
            failures = []

            def promote(version):
                operator = LocalControlPlane(state_dir, storage="sqlite")
                barrier.wait()
                try:
                    operator.promote_workflow(
                        "workflow_control",
                        version,
                        alias="production",
                        expected_current_version="1.0.0",
                    )
                except ValueError as error:
                    failures.append(str(error))
                else:
                    successes.append(version)

            threads = [
                threading.Thread(target=promote, args=(version,))
                for version in ("2.0.0", "3.0.0")
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            records = {
                record["version"]: record for record in bootstrap.list_workflows()
            }
            audit_types = [event["type"] for event in bootstrap.list_audit_events()]
            integrity = bootstrap.verify_audit_integrity()

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIn("workflow alias precondition failed", failures[0])
        winning_version = successes[0]
        self.assertEqual(records[winning_version]["aliases"], ["production"])
        for version, record in records.items():
            if version != winning_version:
                self.assertNotIn("aliases", record)
        self.assertEqual(audit_types.count("workflow_promoted"), 2)
        self.assertEqual(integrity["status"], "valid")

    def test_publish_rejects_reserved_path_segments_in_workflow_identity(self):
        for field in ("id", "version"):
            with self.subTest(field=field), TemporaryDirectory() as tmp:
                state_dir = Path(tmp)
                workflow = _workflow(version="1.0.0")
                workflow["workflow"][field] = ".."
                control = LocalControlPlane(state_dir)

                with self.assertRaisesRegex(ValueError, "safe path segment"):
                    control.publish_workflow(workflow)

                self.assertEqual(
                    [path for path in state_dir.rglob("*.json") if path.is_file()],
                    [],
                )

    def test_unsafe_workflow_identity_characters_use_collision_resistant_artifacts(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir)
            first = _workflow(version="1.0.0")
            first["workflow"]["id"] = "workflow/a"
            second = _workflow(version="1.0.0")
            second["workflow"]["id"] = "workflow?a"

            first_record = control.publish_workflow(first)
            second_record = control.publish_workflow(second)

            first_stored = control.get_workflow("workflow/a", "1.0.0")
            second_stored = control.get_workflow("workflow?a", "1.0.0")

        self.assertNotEqual(first_record["artifact"], second_record["artifact"])
        self.assertEqual(first_stored["workflow"]["id"], "workflow/a")
        self.assertEqual(second_stored["workflow"]["id"], "workflow?a")

    def test_deprecate_updates_registry_without_mutating_published_artifact(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            control.publish_workflow(_workflow(version="1.0.0"))

            record = control.deprecate_workflow("workflow_control", "1.0.0")
            stored = control.get_workflow("workflow_control", "1.0.0")
            audit_types = [event["type"] for event in control.list_audit_events()]

        self.assertEqual(record["status"], "deprecated")
        self.assertEqual(stored["workflow"]["status"], "published")
        self.assertEqual(audit_types, ["workflow_published", "workflow_deprecated"])

    def test_workflow_alias_promotion_resolves_triggers_and_pins_replays(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0"))
            control.publish_workflow(_workflow(version="2.0.0"))

            promoted = control.promote_workflow(
                "workflow_control", "1.0.0", alias="production"
            )
            first_request = {
                "workflow_id": "workflow_control",
                "version": "production",
                "source": "partner",
                "idempotency_key": "production-event-001",
                "input": {"customer_id": "customer_123"},
            }
            first = control.trigger_workflow(first_request)

            control.promote_workflow("workflow_control", "2.0.0", alias="production")
            replay = control.trigger_workflow({**first_request, "trigger_id": "retry"})
            second = control.trigger_workflow(
                {**first_request, "idempotency_key": "production-event-002"}
            )
            run_count = len(control.list_runs())
            records = {record["version"]: record for record in control.list_workflows()}
            audit_types = [event["type"] for event in control.list_audit_events()]

            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection:
                idempotency_versions = [
                    row[0]
                    for row in connection.execute(
                        "select workflow_version from trigger_idempotency order by idempotency_key"
                    ).fetchall()
                ]

        self.assertEqual(promoted["aliases"], ["production"])
        self.assertEqual(first["workflow_version"], "1.0.0")
        self.assertEqual(replay, first)
        self.assertEqual(second["workflow_version"], "2.0.0")
        self.assertEqual(run_count, 2)
        self.assertNotIn("aliases", records["1.0.0"])
        self.assertEqual(records["2.0.0"]["aliases"], ["production"])
        self.assertEqual(idempotency_versions, ["production", "production"])
        self.assertEqual(
            audit_types,
            [
                "workflow_published",
                "workflow_published",
                "workflow_promoted",
                "run_started",
                "run_completed",
                "workflow_promoted",
                "run_started",
                "run_completed",
            ],
        )

    def test_workflow_alias_validation_and_deprecation_fail_closed(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            control.publish_workflow(_workflow(version="1.0.0"))

            for alias in ("", "1production", "prod/unsafe", "x" * 65):
                with self.subTest(alias=alias), self.assertRaisesRegex(
                    ValueError, "workflow alias"
                ):
                    control.promote_workflow("workflow_control", "1.0.0", alias=alias)

            with self.assertRaisesRegex(ValueError, "workflow version not found"):
                control.promote_workflow("workflow_control", "missing", alias="production")

            control.promote_workflow("workflow_control", "1.0.0", alias="production")
            deprecated = control.deprecate_workflow("workflow_control", "1.0.0")
            with self.assertRaisesRegex(ValueError, "workflow version not found"):
                control.trigger_workflow(
                    {
                        "workflow_id": "workflow_control",
                        "version": "production",
                    }
                )

        self.assertNotIn("aliases", deprecated)

    def test_exact_version_takes_precedence_over_same_named_alias(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="production"))
            control.publish_workflow(_workflow(version="1.0.0"))
            control.promote_workflow("workflow_control", "1.0.0", alias="production")

            result = control.trigger_workflow(
                {
                    "workflow_id": "workflow_control",
                    "version": "production",
                    "idempotency_key": "exact-version-001",
                }
            )

        self.assertEqual(result["workflow_version"], "production")

    def test_run_published_workflow_binds_run_to_immutable_version_and_audit(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            control.publish_workflow(_workflow(version="2.0.0"))

            run_state = control.run_published_workflow("workflow_control", "2.0.0")
            run_summary = control.list_runs()[0]
            audit_events = control.list_audit_events()
            audit_types = [event["type"] for event in audit_events]

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(run_state["workflow_id"], "workflow_control")
        self.assertEqual(run_state["workflow_version"], "2.0.0")
        self.assertEqual(run_summary["workflow_version"], "2.0.0")
        self.assertIn("run_started", audit_types)
        self.assertIn("run_completed", audit_types)
        self.assertEqual(audit_events[1]["run_id"], run_state["run_id"])

    def test_trigger_workflow_starts_published_run_with_trigger_metadata(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="10.0.0"))

            result = control.trigger_workflow(
                {
                    "workflow_id": "workflow_control",
                    "version": "10.0.0",
                    "source": "local-test",
                    "idempotency_key": "demo-1",
                    "input": {"customer_id": "customer_123"},
                }
            )
            detail = control.get_run(result["run_id"])
            audit_events = control.list_audit_events(run_id=result["run_id"])
            started_events = control.list_audit_events(run_id=result["run_id"], event_type="run_started")

        self.assertTrue(result["trigger_id"].startswith("trigger_"))
        self.assertEqual(result["workflow_id"], "workflow_control")
        self.assertEqual(result["workflow_version"], "10.0.0")
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["source"], "local-test")
        self.assertEqual(result["idempotency_key"], "demo-1")
        self.assertEqual(result["input_keys"], ["customer_id"])
        self.assertEqual(detail["context"]["input"], {"customer_id": "customer_123"})
        self.assertEqual(
            detail["context"]["trigger"],
            {
                "trigger_id": result["trigger_id"],
                "source": "local-test",
                "idempotency_key": "demo-1",
                "input_keys": ["customer_id"],
            },
        )
        self.assertEqual([event["type"] for event in audit_events], ["run_started", "run_completed"])
        self.assertEqual(started_events[0]["trigger_id"], result["trigger_id"])
        self.assertEqual(started_events[0]["trigger_source"], "local-test")
        self.assertEqual(started_events[0]["idempotency_key"], "demo-1")
        self.assertEqual(started_events[0]["input_keys"], ["customer_id"])
        self.assertNotIn("input", started_events[0])

    def test_sqlite_trigger_idempotency_replays_without_new_run_or_audit(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="10.1.0"))
            request = {
                "workflow_id": "workflow_control",
                "version": "10.1.0",
                "source": "partner",
                "idempotency_key": "event-001",
                "input": {"customer_id": "customer_123"},
            }

            first = control.trigger_workflow(request)
            audit_before_replay = control.list_audit_events()
            second = control.trigger_workflow({**request, "trigger_id": "trigger_retry"})
            runs = control.list_runs()
            audit_after_replay = control.list_audit_events()
            with closing(sqlite3.connect(Path(tmp) / "control.sqlite3")) as connection:
                idempotency_rows = connection.execute(
                    "select request_fingerprint, response_json from trigger_idempotency"
                ).fetchall()

        self.assertEqual(second, first)
        self.assertEqual(len(runs), 1)
        self.assertEqual(audit_after_replay, audit_before_replay)
        self.assertNotIn("customer_123", json.dumps(idempotency_rows))

    def test_sqlite_trigger_idempotency_conflicts_on_changed_request(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="10.2.0"))
            base = {
                "workflow_id": "workflow_control",
                "version": "10.2.0",
                "source": "partner",
                "idempotency_key": "event-002",
                "input": {"customer_id": "customer_123"},
            }
            control.trigger_workflow(base)

            with self.assertRaises(TriggerIdempotencyError) as raised:
                control.trigger_workflow({**base, "input": {"customer_id": "customer_456"}})

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(str(raised.exception), "idempotency key conflicts with an existing request")

    def test_sqlite_trigger_idempotency_keeps_unknown_outcome_fail_closed(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="10.3.0"))
            request = {
                "workflow_id": "workflow_control",
                "version": "10.3.0",
                "idempotency_key": "event-003",
                "input": {"customer_id": "customer_123"},
            }
            with patch.object(control, "run_published_workflow", side_effect=RuntimeError("private failure")):
                with self.assertRaisesRegex(RuntimeError, "private failure"):
                    control.trigger_workflow(request)
            with self.assertRaises(TriggerIdempotencyError) as raised:
                control.trigger_workflow(request)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(str(raised.exception), "idempotency key has an unresolved outcome; use a new key")

    def test_sqlite_trigger_idempotency_rejects_concurrent_claim_without_duplicate_run(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="10.4.0"))
            request = {
                "workflow_id": "workflow_control",
                "version": "10.4.0",
                "idempotency_key": "event-004",
            }
            entered = threading.Event()
            release = threading.Event()
            result = {}

            def slow_run(*args, **kwargs):
                entered.set()
                release.wait(timeout=2)
                return {
                    "run_id": "run_concurrent_001",
                    "status": "completed",
                    "workflow_id": "workflow_control",
                    "workflow_version": "10.4.0",
                }

            with patch.object(control, "run_published_workflow", side_effect=slow_run):
                first_thread = threading.Thread(
                    target=lambda: result.update(first=control.trigger_workflow(request)),
                    daemon=True,
                )
                first_thread.start()
                self.assertTrue(entered.wait(timeout=2))
                with self.assertRaises(TriggerIdempotencyError):
                    control.trigger_workflow(request)
                release.set()
                first_thread.join(timeout=2)

        self.assertFalse(first_thread.is_alive())
        self.assertEqual(result["first"]["run_id"], "run_concurrent_001")

    def test_run_published_workflow_can_use_sqlite_run_storage(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="2.0.0"))

            run_state = control.run_published_workflow("workflow_control", "2.0.0")
            run_summary = LocalControlPlane(state_dir, storage="sqlite").list_runs()[0]

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(run_summary["run_id"], run_state["run_id"])
        self.assertEqual(run_summary["workflow_id"], "workflow_control")

    def test_sqlite_storage_persists_workflow_registry_and_audit_events(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")

            record = control.publish_workflow(_workflow(version="3.0.0"))
            deprecated = control.deprecate_workflow("workflow_control", "3.0.0")
            records = LocalControlPlane(state_dir, storage="sqlite").list_workflows()
            audit_types = [event["type"] for event in control.list_audit_events()]

            with closing(sqlite3.connect(state_dir / "control.sqlite3")) as connection, connection:
                workflow_rows = connection.execute("select workflow_id, version, status from workflow_versions").fetchall()
                audit_rows = connection.execute("select event_type from audit_events order by sequence").fetchall()

        self.assertEqual(record["workflow_id"], "workflow_control")
        self.assertEqual(deprecated["status"], "deprecated")
        self.assertEqual(records[0]["status"], "deprecated")
        self.assertEqual(workflow_rows, [("workflow_control", "3.0.0", "deprecated")])
        self.assertEqual([row[0] for row in audit_rows], ["workflow_published", "workflow_deprecated"])
        self.assertEqual(audit_types, ["workflow_published", "workflow_deprecated"])

    def test_sqlite_storage_imports_existing_json_registry_and_audit(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            json_control = LocalControlPlane(state_dir)
            json_control.publish_workflow(_workflow(version="4.0.0"))

            sqlite_control = LocalControlPlane(state_dir, storage="sqlite")
            records = sqlite_control.list_workflows()
            audit_types_before_run = [event["type"] for event in sqlite_control.list_audit_events()]
            run_state = sqlite_control.run_published_workflow("workflow_control", "4.0.0")
            audit_types_after_run = [event["type"] for event in sqlite_control.list_audit_events()]

        self.assertEqual(records[0]["workflow_id"], "workflow_control")
        self.assertEqual(records[0]["version"], "4.0.0")
        self.assertEqual(audit_types_before_run, ["workflow_published"])
        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(audit_types_after_run, ["workflow_published", "run_started", "run_completed"])

    def test_resume_published_run_records_resume_and_terminal_audit(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_approval_workflow(version="5.0.0"))

            waiting = control.run_published_workflow("workflow_control", "5.0.0")
            completed = control.resume_published_run(waiting["run_id"], approved=True)
            detail = control.get_run(waiting["run_id"])
            audit_events = control.list_audit_events(run_id=waiting["run_id"])
            completed_events = control.list_audit_events(event_type="run_completed")

        self.assertEqual(waiting["status"], "waiting")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(detail["status"], "completed")
        self.assertEqual(
            [event["type"] for event in audit_events],
            ["run_started", "run_waiting", "run_resumed", "run_completed"],
        )
        self.assertLessEqual(
            datetime.fromisoformat(audit_events[2]["timestamp"]),
            datetime.fromisoformat(audit_events[3]["timestamp"]),
        )
        self.assertEqual(completed_events[0]["run_id"], waiting["run_id"])

    def test_resume_retry_reconciles_audit_after_run_state_commit(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_approval_workflow(version="5.1.0"))
            waiting = control.run_published_workflow("workflow_control", "5.1.0")

            with patch(
                "skill2workflow.storage._append_audit_connection",
                side_effect=RuntimeError("resume audit append failed"),
            ):
                with self.assertRaisesRegex(RuntimeError, "resume audit append failed"):
                    control.resume_published_run(waiting["run_id"], approved=True)

            retried = control.resume_published_run(waiting["run_id"], approved=True)
            events = control.list_audit_events(run_id=waiting["run_id"])
            report = control.inspect_run_audit(run_id=waiting["run_id"])

            with self.assertRaisesRegex(ValueError, "not waiting"):
                control.resume_published_run(waiting["run_id"], approved=True)

        self.assertEqual(retried["status"], "completed")
        self.assertEqual(
            [event["type"] for event in events],
            ["run_started", "run_waiting", "run_resumed", "run_completed"],
        )
        self.assertEqual(report["status"], "clean")

    def test_audit_events_can_filter_by_workflow_version_and_run_id(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="6.0.0"))
            control.publish_workflow(_workflow(version="7.0.0"))

            first = control.run_published_workflow("workflow_control", "6.0.0")
            second = control.run_published_workflow("workflow_control", "7.0.0")
            version_events = control.list_audit_events(workflow_id="workflow_control", version="6.0.0")
            run_events = control.list_audit_events(run_id=second["run_id"])

        self.assertTrue(all(event.get("workflow_version") == "6.0.0" for event in version_events))
        self.assertEqual([event["type"] for event in run_events], ["run_started", "run_completed"])
        self.assertEqual(run_events[0]["run_id"], second["run_id"])
        self.assertNotEqual(first["run_id"], second["run_id"])

    def test_connector_registry_returns_active_connector_manifests(self):
        with TemporaryDirectory() as tmp:
            connectors = LocalControlPlane(Path(tmp)).list_connectors()

        connector_ids = {connector["id"] for connector in connectors}
        http_connector = next(connector for connector in connectors if connector["id"] == "http")
        self.assertIn("manual", connector_ids)
        self.assertIn("http", connector_ids)
        self.assertTrue(all(connector["status"] == "active" for connector in connectors))
        self.assertTrue(all("node_types" in connector for connector in connectors))
        self.assertIn("input_mapping", http_connector["config_schema"]["properties"]["request"]["properties"])
        self.assertEqual(http_connector["manifest_version"], "skill2workflow-connector-0.1.0")
        self.assertEqual(http_connector["execution_contract"]["mode"], "built_in")
        self.assertEqual(http_connector["credential_contract"]["supports_handles"], True)
        self.assertEqual(http_connector["audit_contract"]["value_policy"], "compact_no_payload_values")

    def test_published_connector_run_records_connector_audit_events(self):
        server = _ConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                control = LocalControlPlane(Path(tmp), storage="sqlite")
                control.publish_workflow(_connector_workflow("8.0.0", server.url))

                run_state = control.run_published_workflow("workflow_connector", "8.0.0")
                started_events = control.list_audit_events(
                    run_id=run_state["run_id"],
                    event_type="connector_started",
                )
                completed_events = control.list_audit_events(
                    run_id=run_state["run_id"],
                    event_type="connector_completed",
                )
        finally:
            server.close()

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(started_events[0]["workflow_id"], "workflow_connector")
        self.assertEqual(started_events[0]["workflow_version"], "8.0.0")
        self.assertEqual(started_events[0]["node_id"], "call_api")
        self.assertEqual(started_events[0]["connector_id"], "http")
        self.assertEqual(completed_events[0]["connector_status"], "completed")
        self.assertEqual(completed_events[0]["node_id"], "call_api")

    def test_published_connector_run_resolves_credentials_without_audit_leakage(self):
        server = _ConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                control = LocalControlPlane(
                    Path(tmp),
                    storage="sqlite",
                    credential_provider=StaticCredentialProvider({"demo_api_token": "secret-token"}),
                )
                control.publish_workflow(_credential_connector_workflow("11.0.0", server.url))

                run_state = control.run_published_workflow("workflow_connector", "11.0.0")
                audit_events = control.list_audit_events(run_id=run_state["run_id"])
        finally:
            server.close()

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(server.requests[0]["headers"]["Authorization"], "Bearer secret-token")
        self.assertNotIn("secret-token", json.dumps(run_state["node_results"]))
        self.assertNotIn("secret-token", json.dumps(audit_events))

    def test_triggered_connector_mapping_promotes_compact_audit_metadata(self):
        server = _ConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                control = LocalControlPlane(Path(tmp), storage="sqlite")
                control.publish_workflow(_mapped_connector_workflow("12.0.0", server.url))

                result = control.trigger_workflow(
                    {
                        "workflow_id": "workflow_connector",
                        "version": "12.0.0",
                        "source": "local-test",
                        "input": {"customer_id": "customer_123"},
                    }
                )
                audit_events = control.list_audit_events(run_id=result["run_id"])
                completed_events = control.list_audit_events(
                    run_id=result["run_id"],
                    event_type="connector_completed",
                )
        finally:
            server.close()

        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(server.requests[0]["body"], {"approved": True, "customer_id": "customer_123"})
        self.assertEqual(completed_events[0]["input_mapping_status"], "applied")
        self.assertEqual(completed_events[0]["input_mapping_keys"], ["customer_id"])
        self.assertNotIn("customer_123", json.dumps(audit_events))

    def test_external_connector_runtime_promotes_compact_audit_metadata(self):
        fixture = _load_local_echo_fixture()
        runtime = ConnectorRuntime([ExternalConnector(fixture.MANIFEST, fixture.execute)])

        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(
                Path(tmp),
                storage="sqlite",
                credential_provider=StaticCredentialProvider({"demo_api_token": "secret-token"}),
                connector_runtime=runtime,
            )
            control.publish_workflow(_external_connector_workflow("13.0.0"))

            result = control.trigger_workflow(
                {
                    "workflow_id": "workflow_external_connector",
                    "version": "13.0.0",
                    "source": "local-test",
                    "input": {"customer_id": "customer_123"},
                }
            )
            detail = control.get_run(result["run_id"])
            audit_events = control.list_audit_events(run_id=result["run_id"])
            completed_events = control.list_audit_events(
                run_id=result["run_id"],
                event_type="connector_completed",
            )

        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(detail["node_results"]["call_echo"]["connector"], {"id": "local_echo", "kind": "local_echo"})
        self.assertEqual(
            detail["node_results"]["call_echo"]["credentials"],
            {"status": "resolved", "handles": ["demo_api_token"]},
        )
        self.assertEqual(completed_events[0]["connector_id"], "local_echo")
        self.assertEqual(completed_events[0]["credential_status"], "resolved")
        self.assertEqual(completed_events[0]["credential_handles"], ["demo_api_token"])
        self.assertEqual(completed_events[0]["input_mapping_status"], "applied")
        self.assertEqual(completed_events[0]["input_mapping_keys"], ["customer_id"])
        self.assertNotIn("secret-token", json.dumps(detail))
        self.assertNotIn("secret-token", json.dumps(audit_events))
        self.assertNotIn("customer_123", json.dumps(audit_events))

    def test_published_retry_policy_promotes_policy_events_to_audit(self):
        server = _FlakyConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                control = LocalControlPlane(Path(tmp), storage="sqlite")
                workflow = _connector_workflow("9.0.0", server.url)
                workflow["nodes"][1]["retry"] = {"max_attempts": 1}
                control.publish_workflow(workflow)

                run_state = control.run_published_workflow("workflow_connector", "9.0.0")
                retry_events = control.list_audit_events(
                    run_id=run_state["run_id"],
                    event_type="node_retrying",
                )
                recovered_events = control.list_audit_events(
                    run_id=run_state["run_id"],
                    event_type="node_recovered",
                )
        finally:
            server.close()

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(retry_events[0]["node_id"], "call_api")
        self.assertEqual(retry_events[0]["attempt"], 1)
        self.assertEqual(retry_events[0]["max_attempts"], 1)
        self.assertIn("HTTP 503", retry_events[0]["error"])
        self.assertEqual(recovered_events[0]["node_id"], "call_api")
        self.assertEqual(recovered_events[0]["attempt"], 2)

    def test_published_fallback_promotes_fixed_route_evidence_to_audit(self):
        workflow = _connector_workflow("9.1.0", "https://unused.invalid")
        workflow["nodes"][1]["on_fallback"] = "fallback"
        workflow["nodes"].insert(
            2,
            {
                "id": "fallback",
                "type": "step",
                "title": "Fallback handling",
                "on_success": "end",
                "on_failure": "failure",
            },
        )
        workflow["edges"].extend(
            [
                {"id": "edge_call_fallback", "from": "call_api", "to": "fallback", "label": "fallback"},
                {"id": "edge_fallback_end", "from": "fallback", "to": "end", "label": "next"},
                {"id": "edge_fallback_failure", "from": "fallback", "to": "failure", "label": "failure"},
            ]
        )

        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(workflow)
            control.executor.connector_runtime = _FailingConnectorRuntime()
            state = control.run_published_workflow("workflow_connector", "9.1.0")
            fallback_events = control.list_audit_events(
                run_id=state["run_id"], event_type="node_fallback"
            )

        self.assertEqual(state["status"], "completed")
        self.assertEqual(fallback_events[0]["node_id"], "call_api")
        self.assertEqual(fallback_events[0]["target"], "fallback")


def _workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_control",
            "name": "control",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }


class _TestClock:
    def __init__(self):
        self.current = datetime(2026, 8, 13, tzinfo=timezone.utc)

    def __call__(self):
        return self.current.isoformat()

    def advance(self, milliseconds):
        self.current += timedelta(milliseconds=milliseconds)


class _AdvancingConnectorRuntime:
    def __init__(self, clock):
        self.clock = clock

    def execute_connector(self, node, credential_provider=None, context=None):
        self.clock.advance(10)
        return {
            "status": "completed",
            "connector": {"id": "http", "kind": "http"},
            "output": {"ok": True},
        }


class _FailingConnectorRuntime:
    def execute_connector(self, node, credential_provider=None, context=None):
        return {
            "status": "failed",
            "connector": {"id": "http", "kind": "http"},
            "error": "provider unavailable",
            "output": {},
        }


def _approval_workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_control",
            "name": "control",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "review"},
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
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
            {"id": "edge_review_end", "from": "review", "to": "end", "label": "next"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "failure"},
        ],
    }


def _connector_workflow(version: str, url: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_connector",
            "name": "connector",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "call_api"},
            {
                "id": "call_api",
                "type": "tool_call",
                "title": "Call API",
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {
                        "method": "POST",
                        "url": url,
                        "headers": {"Content-Type": "application/json"},
                        "body": {"approved": True},
                        "timeout_ms": 2000,
                    },
                },
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_call", "from": "start", "to": "call_api", "label": "next"},
            {"id": "edge_call_end", "from": "call_api", "to": "end", "label": "next"},
            {"id": "edge_call_failure", "from": "call_api", "to": "failure", "label": "failure"},
        ],
    }


def _credential_connector_workflow(version: str, url: str):
    workflow = _connector_workflow(version, url)
    workflow["nodes"][1]["connector"]["credentials"] = [
        {
            "target": "header",
            "name": "Authorization",
            "handle": "demo_api_token",
            "prefix": "Bearer ",
        }
    ]
    return workflow


def _mapped_connector_workflow(version: str, url: str):
    workflow = _connector_workflow(version, url)
    workflow["nodes"][1]["connector"]["request"]["input_mapping"] = [
        {"from": "/input/customer_id", "to": "/body/customer_id", "required": True},
    ]
    return workflow


def _external_connector_workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_external_connector",
            "name": "external-connector",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "call_echo"},
            {
                "id": "call_echo",
                "type": "tool_call",
                "title": "Call external echo",
                "connector": {
                    "id": "local_echo",
                    "kind": "local_echo",
                    "request": {
                        "body": {"source": "control-plane-test"},
                        "input_mapping": [
                            {"from": "/input/customer_id", "to": "/body/customer_id", "required": True},
                        ],
                    },
                    "credentials": [
                        {
                            "target": "header",
                            "name": "Authorization",
                            "handle": "demo_api_token",
                            "prefix": "Bearer ",
                        }
                    ],
                },
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_call", "from": "start", "to": "call_echo", "label": "next"},
            {"id": "edge_call_end", "from": "call_echo", "to": "end", "label": "next"},
            {"id": "edge_call_failure", "from": "call_echo", "to": "failure", "label": "failure"},
        ],
    }


def _load_local_echo_fixture():
    path = Path(__file__).resolve().parents[1] / "examples" / "connectors" / "local_echo_connector.py"
    spec = importlib.util.spec_from_file_location("local_echo_connector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw_body) if raw_body else None
        self.server.requests.append({"path": self.path, "headers": dict(self.headers.items()), "body": body})
        payload = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


class _FlakyConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw_body) if raw_body else None
        self.server.requests.append({"path": self.path, "headers": dict(self.headers.items()), "body": body})

        if len(self.server.requests) == 1:
            payload = json.dumps({"error": "temporary"}).encode("utf-8")
            self.send_response(503)
        else:
            payload = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


class _ConnectorTestServer:
    def __init__(self):
        self._server = HTTPServer(("127.0.0.1", 0), _ConnectorRequestHandler)
        self._server.requests = []
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/connector"

    @property
    def requests(self):
        return self._server.requests

    def close(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class _FlakyConnectorTestServer(_ConnectorTestServer):
    def __init__(self):
        self._server = HTTPServer(("127.0.0.1", 0), _FlakyConnectorRequestHandler)
        self._server.requests = []
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
