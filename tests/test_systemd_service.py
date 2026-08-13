import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.service_bootstrap import initialize_service_workspace
from skill2workflow.systemd_service import write_systemd_service_unit
from scripts.systemd_service_smoke import _verify_systemd_unit


class SystemdServiceUnitTests(TestCase):
    def test_writes_one_hardened_non_overwriting_unit_without_secret_value(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            initialized = initialize_service_workspace(
                workspace,
                token_factory=lambda: "t" * 48,
            )
            executable = root / "bin" / "skill2workflow"
            executable.parent.mkdir()
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o700)
            output = root / "skill2workflow-team-a.service"

            result = write_systemd_service_unit(
                Path(initialized["config_file"]),
                output,
                service_user="workflow",
                service_group="operators",
                executable=executable,
            )

            content = output.read_text(encoding="utf-8")
            output_mode = output.stat().st_mode & 0o777

        self.assertEqual(
            result["schema_version"],
            "skill2workflow-systemd-service-unit-result-0.1.0",
        )
        self.assertEqual(result["status"], "written")
        self.assertEqual(result["unit_name"], "skill2workflow-team-a.service")
        self.assertEqual(output_mode, 0o644)
        self.assertIn("[Unit]", content)
        self.assertIn("[Service]", content)
        self.assertIn("[Install]", content)
        self.assertIn("User=workflow", content)
        self.assertIn("Group=operators", content)
        executable_path = executable.resolve()
        config_path = Path(initialized["config_file"]).resolve()
        state_path = Path(initialized["state_dir"]).resolve()
        self.assertIn(f"ExecStart={executable_path} service --config {config_path}", content)
        self.assertIn(f"ReadWritePaths={state_path}", content)
        self.assertIn(f"ReadOnlyPaths={config_path}", content)
        self.assertIn("UMask=0077", content)
        self.assertIn("StandardOutput=journal", content)
        self.assertIn("StandardError=journal", content)
        self.assertIn("NoNewPrivileges=yes", content)
        self.assertIn("ProtectSystem=strict", content)
        self.assertIn("ProtectHome=read-only", content)
        self.assertIn("PrivateTmp=yes", content)
        self.assertIn("RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6", content)
        self.assertIn("SendSIGKILL=no", content)
        self.assertIn("WantedBy=multi-user.target", content)
        self.assertNotIn("t" * 48, content)
        self.assertNotIn("Environment=", content)

    @patch("scripts.systemd_service_smoke.shutil.which", return_value="/usr/bin/systemd-analyze")
    @patch("scripts.systemd_service_smoke.subprocess.run")
    def test_optional_systemd_verify_returns_only_bounded_status(self, run, _which):
        run.return_value.returncode = 0

        result = _verify_systemd_unit(Path("/tmp/example.service"))

        self.assertEqual(result, {"status": "passed", "code": "verified"})
        run.assert_called_once_with(
            ["/usr/bin/systemd-analyze", "verify", "/tmp/example.service"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    @patch("scripts.systemd_service_smoke.shutil.which", return_value=None)
    def test_optional_systemd_verify_fails_closed_when_analyzer_is_missing(self, _which):
        self.assertEqual(
            _verify_systemd_unit(Path("/tmp/example.service")),
            {"status": "failed", "code": "systemd_analyze_missing"},
        )

    def test_rejects_existing_output_and_unsafe_service_identity_or_path(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialized = initialize_service_workspace(
                root / "workspace",
                token_factory=lambda: "t" * 48,
            )
            executable = root / "skill2workflow"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o700)
            output = root / "skill2workflow.service"
            output.write_text("existing", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must not already exist"):
                write_systemd_service_unit(
                    Path(initialized["config_file"]),
                    output,
                    service_user="workflow",
                    executable=executable,
                )
            with self.assertRaisesRegex(ValueError, "service user"):
                write_systemd_service_unit(
                    Path(initialized["config_file"]),
                    root / "fresh.service",
                    service_user="workflow\nExecStart=/bin/false",
                    executable=executable,
                )
            with self.assertRaisesRegex(ValueError, "service executable"):
                write_systemd_service_unit(
                    Path(initialized["config_file"]),
                    root / "another.service",
                    service_user="workflow",
                    executable=Path("/unsafe path/skill2workflow"),
                )

    def test_requires_an_absolute_service_unit_name_and_a_regular_executable(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialized = initialize_service_workspace(
                root / "workspace",
                token_factory=lambda: "t" * 48,
            )
            executable = root / "skill2workflow"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o700)

            with self.assertRaisesRegex(ValueError, "absolute"):
                write_systemd_service_unit(
                    Path(initialized["config_file"]),
                    Path("skill2workflow.service"),
                    service_user="workflow",
                    executable=executable,
                )
            with self.assertRaisesRegex(ValueError, "name"):
                write_systemd_service_unit(
                    Path(initialized["config_file"]),
                    root / "skill2workflow.timer",
                    service_user="workflow",
                    executable=executable,
                )
            os.unlink(executable)
            executable.mkdir()
            with self.assertRaisesRegex(ValueError, "regular executable"):
                write_systemd_service_unit(
                    Path(initialized["config_file"]),
                    root / "missing-command.service",
                    service_user="workflow",
                    executable=executable,
                )

    def test_rejects_ephemeral_listener_configurations(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialized = initialize_service_workspace(
                root / "workspace",
                port=0,
                token_factory=lambda: "t" * 48,
            )
            executable = root / "skill2workflow"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o700)

            with self.assertRaisesRegex(ValueError, "port must be nonzero"):
                write_systemd_service_unit(
                    Path(initialized["config_file"]),
                    root / "skill2workflow.service",
                    service_user="workflow",
                    executable=executable,
                )

    def test_rejects_an_unsafe_credential_directory_before_writing_output(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialized = initialize_service_workspace(
                root / "workspace",
                token_factory=lambda: "t" * 48,
            )
            credential_dir = Path(initialized["credential_directory"])
            credential_dir.chmod(0o755)
            executable = root / "skill2workflow"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o700)
            output = root / "skill2workflow.service"

            with self.assertRaisesRegex(ValueError, "credential directory.*group or others"):
                write_systemd_service_unit(
                    Path(initialized["config_file"]),
                    output,
                    service_user="workflow",
                    executable=executable,
                )

            self.assertFalse(output.exists())

    def test_rejects_an_executable_inside_writable_state_before_writing_output(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialized = initialize_service_workspace(
                root / "workspace",
                token_factory=lambda: "t" * 48,
            )
            executable = Path(initialized["state_dir"]) / "skill2workflow"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o700)
            output = root / "skill2workflow.service"

            with self.assertRaisesRegex(ValueError, "executable.*writable service state"):
                write_systemd_service_unit(
                    Path(initialized["config_file"]),
                    output,
                    service_user="workflow",
                    executable=executable,
                )

            self.assertFalse(output.exists())

    def test_rejects_oversized_or_invalid_config_before_writing_output(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialized = initialize_service_workspace(
                root / "workspace",
                token_factory=lambda: "t" * 48,
            )
            config = Path(initialized["config_file"])
            executable = root / "skill2workflow"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o700)
            oversized_output = root / "oversized.service"
            config.write_bytes(config.read_bytes() + b" " * (64 * 1024))
            config.chmod(0o600)

            with self.assertRaisesRegex(ValueError, "exceeds the size limit"):
                write_systemd_service_unit(
                    config,
                    oversized_output,
                    service_user="workflow",
                    executable=executable,
                )

            self.assertFalse(oversized_output.exists())
            config.write_bytes(b"\xff")
            config.chmod(0o600)
            invalid_output = root / "invalid.service"
            with self.assertRaisesRegex(ValueError, "service config is unavailable"):
                write_systemd_service_unit(
                    config,
                    invalid_output,
                    service_user="workflow",
                    executable=executable,
                )

            self.assertFalse(invalid_output.exists())

    def test_public_output_mode_is_set_on_the_open_descriptor(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialized = initialize_service_workspace(
                root / "workspace",
                token_factory=lambda: "t" * 48,
            )
            executable = root / "skill2workflow"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o700)
            output = root / "skill2workflow.service"

            with patch("skill2workflow.systemd_service.os.chmod") as chmod:
                write_systemd_service_unit(
                    Path(initialized["config_file"]),
                    output,
                    service_user="workflow",
                    executable=executable,
                )

            self.assertEqual(output.stat().st_mode & 0o777, 0o644)
            chmod.assert_not_called()

    def test_portable_cli_smoke_emits_redacted_evidence(self):
        with TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/systemd_service_smoke.py",
                    "--work-dir",
                    str(Path(tmp) / "smoke"),
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=20,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        evidence = json.loads(completed.stdout)
        self.assertEqual(evidence["status"], "passed")
        self.assertTrue(all(evidence["checks"].values()))
        self.assertNotIn("token", json.dumps(evidence).lower())
