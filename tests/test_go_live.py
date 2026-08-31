import json
import threading
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main
from skill2workflow.go_live import assess_go_live
from skill2workflow.service import RuntimeService, load_service_config
from skill2workflow.service_bootstrap import initialize_service_workspace


class GoLiveTests(TestCase):
    def test_running_service_gate_uses_bind_skip_and_real_protected_checks(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            initialized = initialize_service_workspace(root, port=0)
            config_path = Path(initialized["config_file"])
            service = RuntimeService(load_service_config(config_path))
            ready = threading.Event()
            thread = threading.Thread(
                target=service.serve,
                kwargs={"ready_callback": lambda _service: ready.set()},
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(timeout=2))
            try:
                result = assess_go_live(
                    config_path,
                    "http://127.0.0.1:{}".format(service.server_address[1]),
                    Path(initialized["token_file"]),
                )
            finally:
                service.begin_shutdown()
                thread.join(timeout=2)

        self.assertFalse(thread.is_alive())
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["local_doctor"]["skipped_check_ids"], ["bind"])
        self.assertEqual(result["service_probe"]["status"], "ready")
        self.assertEqual(result["operational_readiness"]["status"], "ready")

    def test_local_doctor_failure_skips_network_and_token_use(self):
        doctor = {
            "status": "not_ready",
            "checks": [
                {"id": "config", "status": "failed", "code": "invalid"},
                {"id": "auth", "status": "skipped", "code": "blocked_by_config"},
            ],
        }
        with patch("skill2workflow.go_live.diagnose_service", return_value=doctor) as diagnose, patch(
            "skill2workflow.go_live.fetch_service_probe"
        ) as probe, patch("skill2workflow.go_live.fetch_operational_readiness") as operational:
            result = assess_go_live(Path("service.json"), "https://service.example", Path("token"))

        self.assertEqual(result["status"], "not_ready")
        self.assertEqual(result["local_doctor"]["failed_check_ids"], ["config"])
        self.assertEqual(result["local_doctor"]["skipped_check_ids"], ["auth"])
        self.assertEqual(result["service_probe"]["status"], "not_checked")
        self.assertEqual(result["operational_readiness"]["status"], "not_checked")
        diagnose.assert_called_once_with(Path("service.json"), check_bind=False)
        probe.assert_not_called()
        operational.assert_not_called()

    def test_ready_path_composes_only_fixed_safe_summaries(self):
        doctor = {"status": "ready", "checks": [{"id": "config", "status": "passed", "code": "valid"}]}
        probe = {
            "status": "ready",
            "health": {"status": "ok"},
            "readiness": {"status": "ready"},
        }
        operational = {
            "status": "ready",
            "blocking_reasons": [],
            "operator_notes": ["offline_backup_requires_stop"],
        }
        with patch("skill2workflow.go_live.diagnose_service", return_value=doctor), patch(
            "skill2workflow.go_live.fetch_service_probe", return_value=probe
        ), patch(
            "skill2workflow.go_live.fetch_operational_readiness", return_value=operational
        ) as fetch_operational:
            result = assess_go_live(Path("service.json"), "https://service.example", Path("token"))

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["service_probe"], {"status": "ready", "health": "ok", "readiness": "ready"})
        self.assertEqual(result["operational_readiness"], operational)
        fetch_operational.assert_called_once_with("https://service.example", Path("token"))

    def test_probe_or_operational_failure_stays_redacted_and_non_ready(self):
        doctor = {"status": "ready", "checks": [{"id": "config", "status": "passed", "code": "valid"}]}
        unavailable_probe = {"status": "not_ready", "health": {"status": "ok"}, "readiness": {"status": "not_ready"}}
        with patch("skill2workflow.go_live.diagnose_service", return_value=doctor), patch(
            "skill2workflow.go_live.fetch_service_probe", return_value=unavailable_probe
        ), patch("skill2workflow.go_live.fetch_operational_readiness") as operational:
            not_ready = assess_go_live(Path("service.json"), "https://service.example", Path("token"))
        self.assertEqual(not_ready["status"], "not_ready")
        self.assertEqual(not_ready["operational_readiness"]["status"], "not_checked")
        operational.assert_not_called()

        ready_probe = {"status": "ready", "health": {"status": "ok"}, "readiness": {"status": "ready"}}
        with patch("skill2workflow.go_live.diagnose_service", return_value=doctor), patch(
            "skill2workflow.go_live.fetch_service_probe", return_value=ready_probe
        ), patch("skill2workflow.go_live.fetch_operational_readiness", side_effect=ValueError("secret")):
            unavailable = assess_go_live(Path("service.json"), "https://service.example", Path("token"))
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertEqual(unavailable["operational_readiness"]["status"], "unavailable")
        self.assertNotIn("secret", json.dumps(unavailable))

    def test_cli_returns_nonzero_for_a_nonready_gate(self):
        report = {
            "schema_version": "skill2workflow-go-live-check-0.1.0",
            "status": "not_ready",
            "local_doctor": {},
            "service_probe": {},
            "operational_readiness": {},
        }
        stdout = StringIO()
        with patch("skill2workflow.cli.assess_go_live", return_value=report), redirect_stdout(stdout):
            exit_code = main(
                [
                    "service-go-live-check",
                    "--config", "service.json",
                    "--service-url", "https://service.example",
                    "--auth-token-file", "token",
                ]
            )
        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(stdout.getvalue()), report)
