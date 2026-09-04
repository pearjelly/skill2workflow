from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main
from skill2workflow.lark_tenant_credential_check import check_lark_tenant_credential
from skill2workflow.service_bootstrap import initialize_service_workspace


class LarkTenantCredentialCheckTests(TestCase):
    def test_cli_reports_fixed_ready_result_and_exit_code(self):
        with TemporaryDirectory() as temporary:
            initialized = initialize_service_workspace(
                Path(temporary) / "runtime",
                lark_app_id="cli_example",
                lark_app_secret_handle="lark_app_secret",
            )
            stdout = StringIO()
            with patch(
                "skill2workflow.cli.check_lark_tenant_credential",
                return_value={
                    "schema_version": "skill2workflow-lark-tenant-credential-check-0.1.0",
                    "status": "ready",
                    "provider": "lark_tenant_access_token",
                    "reason": "validated",
                },
            ):
                with redirect_stdout(stdout):
                    exit_code = main([
                        "service-lark-tenant-credential-check",
                        "--config",
                        str(initialized["config_file"]),
                    ])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "ready")

    def test_ready_check_is_value_free_and_resolves_only_configured_target(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            initialized = initialize_service_workspace(
                root,
                lark_app_id="cli_example",
                lark_app_secret_handle="lark_app_secret",
            )
            secret = root / "secrets" / "connectors" / "lark_app_secret"
            secret.write_text("private-app-secret", encoding="utf-8")
            secret.chmod(0o600)
            with patch(
                "skill2workflow.lark_tenant_credential_check.LarkTenantAccessTokenCredentialProvider.resolve",
                return_value="private-tenant-token",
            ) as resolve:
                result = check_lark_tenant_credential(Path(initialized["config_file"]))

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["reason"], "validated")
        self.assertNotIn("private", str(result))
        resolve.assert_called_once_with("lark_bot_access_token")

    def test_refuses_unconfigured_credential_without_network_provider(self):
        with TemporaryDirectory() as temporary:
            initialized = initialize_service_workspace(Path(temporary) / "runtime")
            with patch("skill2workflow.lark_tenant_credential_check.LarkTenantAccessTokenCredentialProvider") as provider:
                result = check_lark_tenant_credential(Path(initialized["config_file"]))

        self.assertEqual(result["status"], "not_ready")
        self.assertEqual(result["reason"], "not_configured")
        provider.assert_not_called()
import json
from contextlib import redirect_stdout
from io import StringIO
