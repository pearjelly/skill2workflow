import json
import socket
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main
from skill2workflow.service import RuntimeService, load_service_config
from skill2workflow.service_bootstrap import initialize_service_workspace
from skill2workflow.service_doctor import diagnose_service


class ServiceDoctorTests(TestCase):
    def test_running_service_mode_skips_only_the_bind_check(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            initialized = initialize_service_workspace(root, port=0)

            result = diagnose_service(
                Path(initialized["config_file"]), check_bind=False
            )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["checks"][-1], {
            "id": "bind",
            "status": "skipped",
            "code": "running_service",
        })
        self.assertTrue(
            all(check["status"] == "passed" for check in result["checks"][:-1])
        )

    def test_ready_workspace_has_fixed_secret_free_checks_without_mutation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            token = "doctor-secret-value-0123456789abcdef"
            initialized = initialize_service_workspace(
                root,
                port=0,
                token_factory=lambda: token,
            )
            before = _workspace_snapshot(root)

            result = diagnose_service(Path(initialized["config_file"]))

            after = _workspace_snapshot(root)

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["schema_version"], "skill2workflow-service-doctor-result-0.1.0")
        self.assertEqual(
            [check["id"] for check in result["checks"]],
            ["config", "auth", "credentials", "state", "bind"],
        )
        self.assertTrue(all(check["status"] == "passed" for check in result["checks"]))
        self.assertNotIn(token, json.dumps(result))
        self.assertEqual(before, after)

    def test_unsafe_credential_directory_and_busy_port_fail_independently(self):
        with TemporaryDirectory() as temporary:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            root = Path(temporary) / "runtime"
            initialized = initialize_service_workspace(root, port=port)
            (root / "secrets" / "connectors").chmod(0o755)
            try:
                result = diagnose_service(Path(initialized["config_file"]))
            finally:
                listener.close()

        checks = {check["id"]: check for check in result["checks"]}
        self.assertEqual(result["status"], "not_ready")
        self.assertEqual(checks["credentials"], {
            "id": "credentials",
            "status": "failed",
            "code": "unsafe_permissions",
        })
        self.assertEqual(checks["bind"], {
            "id": "bind",
            "status": "failed",
            "code": "address_unavailable",
        })
        self.assertEqual(checks["auth"]["status"], "passed")
        self.assertEqual(checks["state"]["status"], "passed")

    def test_invalid_config_returns_machine_readable_failure_and_skips_dependents(self):
        with TemporaryDirectory() as temporary:
            config = Path(temporary) / "service.json"
            config.write_text("{}", encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["service-doctor", "--config", str(config)])

        result = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(result["status"], "not_ready")
        self.assertEqual(result["checks"][0], {
            "id": "config",
            "status": "failed",
            "code": "invalid",
        })
        self.assertTrue(
            all(check["status"] == "skipped" for check in result["checks"][1:])
        )
        self.assertNotIn(str(config), stdout.getvalue())

    def test_corrupt_initialized_state_and_socket_creation_return_fixed_failures(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            initialized = initialize_service_workspace(root, port=0)
            config_file = Path(initialized["config_file"])
            service = RuntimeService(load_service_config(config_file))
            service._server.server_close()
            (root / "state" / "control.sqlite3").write_bytes(b"not sqlite")

            corrupt = diagnose_service(config_file)
            with patch(
                "skill2workflow.service_doctor.socket.socket",
                side_effect=OSError("socket unavailable"),
            ):
                no_socket = diagnose_service(config_file)

        corrupt_checks = {check["id"]: check for check in corrupt["checks"]}
        socket_checks = {check["id"]: check for check in no_socket["checks"]}
        self.assertEqual(corrupt["status"], "not_ready")
        self.assertEqual(corrupt_checks["state"], {
            "id": "state",
            "status": "failed",
            "code": "invalid",
        })
        self.assertEqual(socket_checks["bind"], {
            "id": "bind",
            "status": "failed",
            "code": "address_unavailable",
        })

    def test_real_process_smoke_proves_read_only_failure_diagnostics(self):
        with TemporaryDirectory() as temporary:
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/service_doctor_smoke.py",
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


def _workspace_snapshot(root: Path):
    snapshot = []
    for path in sorted([root, *root.rglob("*")], key=lambda item: str(item)):
        details = path.lstat()
        snapshot.append(
            (
                str(path.relative_to(root)),
                details.st_mode,
                details.st_size,
                details.st_mtime_ns,
                path.read_bytes() if path.is_file() else None,
            )
        )
    return snapshot
