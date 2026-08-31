"""CLI contract tests for local audit evidence export."""

from __future__ import annotations

import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.cli import main
from skill2workflow.control_plane import LocalControlPlane


class AuditEvidenceCliTests(TestCase):
    def test_cli_writes_compact_value_free_summary(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "state"
            output = root / "audit.json"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.store.append_audit(
                {
                    "type": "connector_failed",
                    "workflow_id": "workflow_evidence",
                    "workflow_version": "1.0.0",
                    "run_id": "run_evidence",
                    "timestamp": "2026-08-31T00:00:00Z",
                    "error": "private raw error",
                }
            )
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "audit-evidence",
                        "--state-dir", str(state_dir),
                        "--output", str(output),
                        "--max-items", "1",
                    ]
                )

        summary = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(summary["output"], str(output))
        self.assertEqual(summary["event_count"], 1)
        self.assertNotIn("private raw error", stdout.getvalue())
        self.assertNotIn("events", summary)

    def test_cli_verifies_private_export_without_printing_events(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "state"
            output = root / "audit.json"
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.store.append_audit(
                {
                    "type": "connector_failed",
                    "workflow_id": "workflow_evidence",
                    "workflow_version": "1.0.0",
                    "run_id": "run_evidence",
                    "timestamp": "2026-08-31T00:00:00Z",
                    "error": "private raw error",
                }
            )
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(
                    main(["audit-evidence", "--state-dir", str(state_dir), "--output", str(output)]),
                    0,
                )
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["audit-evidence-verify", str(output)])

        summary = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertTrue(summary["valid"])
        self.assertEqual(summary["event_count"], 1)
        self.assertNotIn("private raw error", stdout.getvalue())
        self.assertNotIn("events", summary)
