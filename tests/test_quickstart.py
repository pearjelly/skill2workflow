import json
import os
import shutil
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
    def test_quickstart_warns_when_cleanup_cannot_be_confirmed(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / 'private-path-canary'
            stdout, stderr = StringIO(), StringIO()
            with patch('skill2workflow.quickstart._pin_workspace', return_value=None), \
                 patch('skill2workflow.quickstart.LocalControlPlane.publish_workflow',
                       side_effect=OSError('private-error-canary')), \
                 redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(['quickstart', '--root', str(root)])
            self.assertEqual(status, 1)
            self.assertEqual(stdout.getvalue(), '')
            self.assertIn('quickstart operation failed', stderr.getvalue())
            self.assertIn('workspace cleanup could not be confirmed', stderr.getvalue())
            self.assertIn('ingress secret', stderr.getvalue())
            self.assertNotIn('private-path-canary', stderr.getvalue())
            self.assertNotIn('private-error-canary', stderr.getvalue())
            self.assertTrue((root / 'secrets' / 'ingress-token').is_file())

    def test_quickstart_reports_unconfirmed_bootstrap_cleanup(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / 'private-path-canary'
            stdout, stderr = StringIO(), StringIO()
            with patch('skill2workflow.service_bootstrap._pin_workspace', return_value=None), \
                 patch('skill2workflow.service_bootstrap.os.replace', side_effect=OSError('private-error-canary')), \
                 redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(['quickstart', '--root', str(root)])
            self.assertEqual(status, 1)
            self.assertIn('workspace cleanup could not be confirmed', stderr.getvalue())
            self.assertNotIn('private-path-canary', stderr.getvalue())
            self.assertNotIn('private-error-canary', stderr.getvalue())
            self.assertTrue((root / 'secrets' / 'ingress-token').exists())

    def test_quickstart_preinitialization_refusal_has_no_cleanup_warning(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / 'existing'
            root.mkdir()
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(['quickstart', '--root', str(root)])
            self.assertEqual(status, 1)
            self.assertNotIn('workspace cleanup could not be confirmed', stderr.getvalue())

    def test_quickstart_value_error_keeps_message_and_warns_about_residual_workspace(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / 'workspace'
            stdout, stderr = StringIO(), StringIO()
            with patch('skill2workflow.quickstart._pin_workspace', return_value=None), \
                 patch('skill2workflow.quickstart.LocalControlPlane.publish_workflow',
                       side_effect=ValueError('publication refused')), \
                 redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(['quickstart', '--root', str(root)])
            self.assertEqual(status, 1)
            self.assertTrue(stderr.getvalue().startswith('publication refused\n'))
            self.assertIn('workspace cleanup could not be confirmed', stderr.getvalue())

    def test_quickstart_closes_workspace_identity_on_success_and_failure(self):
        from skill2workflow.quickstart import _pin_workspace
        for fail in (False, True):
            with self.subTest(fail=fail), TemporaryDirectory() as temporary:
                root = Path(temporary) / 'quickstart'
                descriptors = []

                def pin(path):
                    descriptor = _pin_workspace(path)
                    descriptors.append(descriptor)
                    return descriptor

                with patch('skill2workflow.quickstart._pin_workspace', side_effect=pin):
                    if fail:
                        with patch('skill2workflow.quickstart.LocalControlPlane.publish_workflow',
                                   side_effect=ValueError('failure')):
                            with self.assertRaisesRegex(ValueError, 'failure'):
                                initialize_quickstart_workspace(root, token_factory=lambda: 'q' * 48)
                    else:
                        initialize_quickstart_workspace(root, token_factory=lambda: 'q' * 48)
                self.assertEqual(len(descriptors), 1)
                if descriptors[0] is not None:
                    with self.assertRaises(OSError):
                        os.fstat(descriptors[0])

    def test_failed_quickstart_does_not_delete_a_replacement_workspace(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / 'quickstart'
            moved = parent / 'original-quickstart'

            def replace_during_publication(*args):
                root.rename(moved)
                root.mkdir()
                (root / 'keep.txt').write_text('keep', encoding='utf-8')
                raise ValueError('simulated publication failure')

            with patch('skill2workflow.quickstart.LocalControlPlane.publish_workflow',
                       side_effect=replace_during_publication):
                with self.assertRaisesRegex(ValueError, 'simulated publication failure'):
                    initialize_quickstart_workspace(root, token_factory=lambda: 'q' * 48)
            self.assertEqual((root / 'keep.txt').read_text(encoding='utf-8'), 'keep')
            self.assertTrue(moved.is_dir())

    def test_failed_quickstart_preserves_workspace_if_identity_is_unavailable(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / 'quickstart'
            with patch('skill2workflow.quickstart._pin_workspace', return_value=None), \
                 patch('skill2workflow.quickstart.LocalControlPlane.publish_workflow',
                       side_effect=ValueError('simulated publication failure')):
                with self.assertRaisesRegex(ValueError, 'simulated publication failure'):
                    initialize_quickstart_workspace(root, token_factory=lambda: 'q' * 48)
            self.assertTrue((root / 'secrets' / 'ingress-token').is_file())

    def test_failed_quickstart_leaves_a_replacement_symlink_untouched(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / 'quickstart'
            moved = parent / 'original-quickstart'
            other = parent / 'other'
            other.mkdir()
            (other / 'keep.txt').write_text('keep', encoding='utf-8')

            def replace_during_publication(*args):
                root.rename(moved)
                root.symlink_to(other, target_is_directory=True)
                raise ValueError('simulated publication failure')

            with patch('skill2workflow.quickstart.LocalControlPlane.publish_workflow',
                       side_effect=replace_during_publication):
                with self.assertRaisesRegex(ValueError, 'simulated publication failure'):
                    initialize_quickstart_workspace(root, token_factory=lambda: 'q' * 48)
            self.assertTrue(root.is_symlink())
            self.assertEqual((other / 'keep.txt').read_text(encoding='utf-8'), 'keep')

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

            supports_cleanup = (hasattr(os, 'O_DIRECTORY') and hasattr(os, 'O_NOFOLLOW')
                                and getattr(shutil.rmtree, 'avoids_symlink_attacks', False))
            self.assertEqual(root.exists(), not supports_cleanup)

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
                # The drill builds an isolated wheel and starts a real service;
                # slower Linux hosts can exceed 30 seconds without a hang.
                timeout=90,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        evidence = json.loads(completed.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertTrue(all(evidence["checks"].values()))
        for check in ('custom_input_waiting', 'invalid_input_no_workspace',
                      'network_prefix_refused', 'custom_input_approved_http', 'custom_input_compact_result',
                      'quickstart_preview_no_workspace', 'required_mapping_no_workspace',
                      'custom_input_rejected_without_http', 'unconfigured_action_refused'):
            self.assertTrue(evidence['checks'][check])
        self.assertNotIn("secret", json.dumps(evidence).lower())
