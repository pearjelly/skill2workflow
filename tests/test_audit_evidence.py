"""Tests for bounded, redacted local audit evidence exports."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.audit_evidence import export_audit_evidence
from skill2workflow.control_plane import LocalControlPlane


class AuditEvidenceExportTests(TestCase):
    def _seed(self, state_dir: Path) -> None:
        control = LocalControlPlane(state_dir, storage="sqlite")
        for event_type in ("run_started", "connector_failed", "run_completed"):
            control.store.append_audit(
                {
                    "type": event_type,
                    "workflow_id": "workflow_evidence",
                    "workflow_version": "1.0.0",
                    "run_id": "run_evidence",
                    "timestamp": "2026-08-31T00:00:00Z",
                    "error": "private provider diagnostic",
                    "connector_metadata": {"credential": "private connector value"},
                }
            )

    def test_exports_only_bounded_redacted_page_after_valid_chain(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "state"
            output = root / "evidence" / "audit.json"
            self._seed(state_dir)

            result = export_audit_evidence(
                state_dir,
                output,
                max_items=2,
                workflow_id="workflow_evidence",
            )

            exported = json.loads(output.read_text(encoding="utf-8"))
            permissions = os.stat(output).st_mode & 0o777

        serialized = json.dumps(exported, ensure_ascii=False)
        self.assertEqual(result["event_count"], 2)
        self.assertTrue(result["truncated"])
        self.assertEqual(exported["schema_version"], "skill2workflow-audit-evidence-0.1.0")
        self.assertEqual(exported["audit_page"]["window"]["max_items"], 2)
        self.assertTrue(exported["audit_page"]["window"]["truncated"])
        self.assertTrue(exported["audit_page"]["window"]["next_cursor"])
        self.assertEqual(exported["integrity"]["status"], "valid")
        self.assertNotIn("private provider diagnostic", serialized)
        self.assertNotIn("private connector value", serialized)
        self.assertEqual(permissions, 0o600)

    def test_rejects_json_storage_and_leaves_no_output(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "audit.json"
            LocalControlPlane(root / "state", storage="json").store.append_audit(
                {"type": "run_started", "timestamp": "2026-08-31T00:00:00Z"}
            )

            with self.assertRaisesRegex(ValueError, "SQLite"):
                export_audit_evidence(root / "state", output)

            self.assertFalse(output.exists())

    def test_preserves_exact_filters_in_the_exported_page(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "state"
            output = root / "audit.json"
            self._seed(state_dir)

            export_audit_evidence(
                state_dir,
                output,
                max_items=1,
                workflow_id="workflow_evidence",
                workflow_version="1.0.0",
                run_id="run_evidence",
                event_type="connector_failed",
            )
            page = json.loads(output.read_text(encoding="utf-8"))["audit_page"]

        self.assertEqual(
            page["filters"],
            {
                "workflow_id": "workflow_evidence",
                "workflow_version": "1.0.0",
                "run_id": "run_evidence",
                "event_type": "connector_failed",
            },
        )
        self.assertEqual(page["window"]["total"], 1)
        self.assertEqual(page["window"]["returned"], 1)
        self.assertFalse(page["window"]["truncated"])
        self.assertEqual(page["window"]["next_cursor"], "")

    def test_rejects_invalid_chain_and_leaves_no_output(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "state"
            output = root / "audit.json"
            self._seed(state_dir)
            database = state_dir / "control.sqlite3"
            import sqlite3
            with sqlite3.connect(database) as connection:
                connection.execute("UPDATE audit_events SET digest = 'tampered' WHERE sequence = 1")

            with self.assertRaisesRegex(ValueError, "integrity"):
                export_audit_evidence(state_dir, output)

            self.assertFalse(output.exists())

    def test_rejects_preexisting_or_symlink_output_without_touching_it(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "state"
            output = root / "audit.json"
            self._seed(state_dir)
            output.write_text("sentinel", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must not already exist"):
                export_audit_evidence(state_dir, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "sentinel")

            output.unlink()
            outside = root / "outside.json"
            outside.write_text("sentinel", encoding="utf-8")
            output.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                export_audit_evidence(state_dir, output)
            self.assertEqual(outside.read_text(encoding="utf-8"), "sentinel")
