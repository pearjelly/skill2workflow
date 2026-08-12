import json
import os
import stat
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock
from unittest.mock import patch

from skill2workflow.cli import main
from skill2workflow.service import load_service_config
from skill2workflow.service_bootstrap import initialize_service_workspace


class ServiceBootstrapTests(TestCase):
    def test_initialize_creates_a_complete_owner_only_workspace_without_exposing_token(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            token = "t" * 48

            result = initialize_service_workspace(
                root,
                host="127.0.0.1",
                port=0,
                token_factory=lambda: token,
            )
            config_path = root / "config" / "service.json"
            token_path = root / "secrets" / "ingress-token"
            credentials = root / "secrets" / "connectors"
            state_dir = root / "state"
            config = load_service_config(config_path)

            self.assertEqual(result["status"], "initialized")
            self.assertEqual(
                set(result),
                {
                    "schema_version",
                    "status",
                    "root",
                    "config_file",
                    "state_dir",
                    "token_file",
                    "credential_directory",
                },
            )
            self.assertNotIn(token, json.dumps(result))
            self.assertNotIn(token, config_path.read_text(encoding="utf-8"))
            self.assertEqual(token_path.read_text(encoding="utf-8"), token + "\n")
            self.assertEqual(config.host, "127.0.0.1")
            self.assertEqual(config.port, 0)
            self.assertEqual(config.state_dir, state_dir.resolve())
            self.assertEqual(config.auth_token_file, token_path.resolve())
            self.assertEqual(config.credential_dir, credentials.resolve())
            self.assertTrue(credentials.is_dir())
            self.assertTrue(state_dir.is_dir())
            if os.name != "nt":
                self.assertEqual(_mode(root), 0o700)
                self.assertEqual(_mode(root / "config"), 0o700)
                self.assertEqual(_mode(root / "secrets"), 0o700)
                self.assertEqual(_mode(credentials), 0o700)
                self.assertEqual(_mode(state_dir), 0o700)
                self.assertEqual(_mode(config_path), 0o600)
                self.assertEqual(_mode(token_path), 0o600)

    def test_initialize_rejects_relative_invalid_or_existing_targets_without_mutation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            root.mkdir()
            sentinel = root / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            token_factory = Mock(return_value="t" * 48)

            with self.assertRaisesRegex(ValueError, "must not already exist"):
                initialize_service_workspace(root, token_factory=token_factory)
            with self.assertRaisesRegex(ValueError, "absolute path"):
                initialize_service_workspace(Path("relative-runtime"))
            with self.assertRaisesRegex(ValueError, "loopback"):
                initialize_service_workspace(
                    Path(temporary) / "other", host="0.0.0.0"
                )
            with self.assertRaisesRegex(ValueError, "port"):
                initialize_service_workspace(Path(temporary) / "other", port=70000)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            token_factory.assert_not_called()

    def test_initialize_rejects_bad_generated_token_and_cleans_workspace(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"

            with self.assertRaisesRegex(ValueError, "at least 32"):
                initialize_service_workspace(root, token_factory=lambda: "short")

            self.assertFalse(root.exists())

    def test_initialize_cleans_partial_workspace_when_config_publication_fails(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"

            with patch(
                "skill2workflow.service_bootstrap.os.replace",
                side_effect=OSError("simulated publication failure"),
            ):
                with self.assertRaises(OSError):
                    initialize_service_workspace(
                        root, token_factory=lambda: "t" * 48
                    )

            self.assertFalse(root.exists())

    def test_service_init_cli_prints_only_compact_paths(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    ["service-init", "--root", str(root), "--port", "0"]
                )

            result = json.loads(stdout.getvalue())
            token = (root / "secrets" / "ingress-token").read_text(
                encoding="utf-8"
            ).strip()

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertGreaterEqual(len(token.encode("utf-8")), 32)
        self.assertNotIn(token, stdout.getvalue())
        self.assertEqual(result["status"], "initialized")

    def test_real_process_bootstrap_smoke_starts_an_authenticated_service(self):
        with TemporaryDirectory() as temporary:
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/service_bootstrap_smoke.py",
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
        self.assertNotIn("token", json.dumps(evidence).lower())


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)
