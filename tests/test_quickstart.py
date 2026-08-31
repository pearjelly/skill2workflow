import json
import os
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.quickstart import initialize_quickstart_workspace


class InstalledQuickstartTests(TestCase):
    def test_quickstart_compiles_publishes_and_waits_at_a_real_human_gate(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "quickstart"
            secret = "q" * 48

            result = initialize_quickstart_workspace(
                root,
                port=0,
                token_factory=lambda: secret,
            )
            skill_path = root / "example" / "SKILL.md"
            workflow_path = root / "example" / "workflow.json"
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            control = LocalControlPlane(root / "state", storage="sqlite")
            waiting = control.get_run(str(result["run_id"]))
            completed = control.resume_published_run(
                str(result["run_id"]), approved=True
            )
            skill_exists = skill_path.is_file()
            skill_mode = skill_path.stat().st_mode & 0o077
            workflow_mode = workflow_path.stat().st_mode & 0o077

        self.assertEqual(result["status"], "ready_for_review")
        self.assertEqual(result["run_status"], "waiting")
        self.assertEqual(result["workflow_id"], "workflow_controlled_quickstart")
        self.assertEqual(result["workflow_version"], "0.1.0")
        self.assertEqual(
            result["operator_commands"]["inspect_run"][:2],
            ["skill2workflow", "control-run"],
        )
        self.assertEqual(
            result["operator_commands"]["approve_run"][:2],
            ["skill2workflow", "resume-published"],
        )
        self.assertNotIn(secret, json.dumps(result))
        self.assertTrue(skill_exists)
        self.assertEqual(workflow["workflow"]["id"], result["workflow_id"])
        self.assertEqual(waiting["status"], "waiting")
        self.assertEqual(completed["status"], "completed")
        self.assertIn("human_gate_waiting", [event["type"] for event in waiting["events"]])
        if os.name != "nt":
            self.assertEqual(skill_mode, 0)
            self.assertEqual(workflow_mode, 0)

    def test_quickstart_refuses_existing_root_without_mutation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "quickstart"
            root.mkdir()
            sentinel = root / "keep"
            sentinel.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must not already exist"):
                initialize_quickstart_workspace(root)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_quickstart_accepts_a_custom_controlled_skill_without_source_path_leakage(
        self,
    ):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            source = parent / "customer-skill.md"
            source_text = """---
name: customer-controlled-review
description: A customer-owned review path.
---

<HARD-GATE>
Do not execute before a designated reviewer approves.
</HARD-GATE>

## Checklist

1. Prepare the customer review
2. Ask the designated reviewer for approval
3. Record completion
"""
            source.write_text(source_text, encoding="utf-8")
            root = parent / "quickstart"

            result = initialize_quickstart_workspace(
                root,
                port=0,
                skill_path=source,
                token_factory=lambda: "q" * 48,
            )
            copied = (root / "example" / "SKILL.md").read_text(encoding="utf-8")
            workflow = json.loads(
                (root / "example" / "workflow.json").read_text(encoding="utf-8")
            )
            waiting = LocalControlPlane(root / "state", storage="sqlite").get_run(
                str(result["run_id"])
            )

        self.assertEqual(result["workflow_id"], "workflow_customer_controlled_review")
        self.assertEqual(result["run_status"], "waiting")
        self.assertEqual(copied, source_text)
        self.assertNotIn(str(source), json.dumps(result))
        self.assertNotIn(str(source), json.dumps(workflow))
        self.assertEqual(waiting["status"], "waiting")

    def test_custom_quickstart_refuses_skill_without_a_human_gate_before_workspace_creation(
        self,
    ):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            source = parent / "uncontrolled-skill.md"
            source.write_text(
                "## Checklist\n\n1. Perform an uncontrolled action\n",
                encoding="utf-8",
            )
            root = parent / "quickstart"

            with self.assertRaisesRegex(ValueError, "human gate"):
                initialize_quickstart_workspace(root, port=0, skill_path=source)

            self.assertFalse(root.exists())

    def test_quickstart_removes_owned_workspace_when_publication_fails(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "quickstart"

            with patch(
                "skill2workflow.quickstart.LocalControlPlane.publish_workflow",
                side_effect=ValueError("simulated publish failure"),
            ):
                with self.assertRaisesRegex(ValueError, "simulated publish failure"):
                    initialize_quickstart_workspace(
                        root, token_factory=lambda: "q" * 48
                    )

            self.assertFalse(root.exists())

    def test_quickstart_cli_output_is_compact_and_secret_free(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "quickstart"
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    ["quickstart", "--root", str(root), "--port", "0"]
                )
            result = json.loads(stdout.getvalue())
            secret = (root / "secrets" / "ingress-token").read_text(
                encoding="utf-8"
            ).strip()

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(result["status"], "ready_for_review")
        self.assertIn("operator_commands", result)
        self.assertNotIn(secret, stdout.getvalue())

    def test_quickstart_cli_accepts_custom_skill(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            source = parent / "custom.SKILL.md"
            source.write_text(
                """## Checklist

1. Prepare the review
2. Ask for approval
""",
                encoding="utf-8",
            )
            root = parent / "quickstart"
            stdout, stderr = StringIO(), StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "quickstart",
                        "--root",
                        str(root),
                        "--port",
                        "0",
                        "--skill",
                        str(source),
                    ]
                )

        result = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(result["run_status"], "waiting")
        self.assertNotIn(str(source), stdout.getvalue())

    def test_real_process_quickstart_smoke_proves_installed_user_journey(self):
        with TemporaryDirectory() as temporary:
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/quickstart_smoke.py",
                    "--work-dir",
                    str(Path(temporary) / "smoke"),
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        evidence = json.loads(completed.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertTrue(all(evidence["checks"].values()))
        self.assertNotIn("secret", json.dumps(evidence).lower())
