import json
from unittest import TestCase

from skill2workflow.credentials import (
    CredentialResolutionError,
    LarkTenantAccessTokenCredentialProvider,
    StaticCredentialProvider,
)


class _Response:
    def __init__(self, payload):
        self.payload = payload
        self.closed = False

    def read(self, amount=None):
        if amount is None:
            return self.payload
        return self.payload[:amount]

    def close(self):
        self.closed = True


class LarkTenantAccessTokenCredentialProviderTests(TestCase):
    def test_exchanges_only_target_handle_and_reserves_app_secret(self):
        observed = []

        def transport(request, timeout):
            observed.append((request, timeout))
            return _Response(
                json.dumps(
                    {"code": 0, "tenant_access_token": "short-lived-private-token"}
                ).encode("utf-8")
            )

        provider = LarkTenantAccessTokenCredentialProvider(
            StaticCredentialProvider(
                {"lark_app_secret": "private-app-secret", "other": "ordinary"}
            ),
            handle="lark_bot_access_token",
            app_id="cli_example",
            app_secret_handle="lark_app_secret",
            token_transport=transport,
        )

        self.assertEqual(provider.resolve("other"), "ordinary")
        self.assertEqual(observed, [])
        with self.assertRaisesRegex(
            CredentialResolutionError,
            "credential handle not found: lark_app_secret",
        ):
            provider.resolve("lark_app_secret")
        self.assertEqual(observed, [])

        self.assertEqual(provider.resolve("lark_bot_access_token"), "short-lived-private-token")
        self.assertEqual(len(observed), 1)
        request, timeout = observed[0]
        self.assertEqual(timeout, 5.0)
        self.assertEqual(request.full_url, "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"app_id": "cli_example", "app_secret": "private-app-secret"},
        )

    def test_exchange_failure_is_redacted_as_missing_target_credential(self):
        provider = LarkTenantAccessTokenCredentialProvider(
            StaticCredentialProvider({"lark_app_secret": "private-app-secret"}),
            handle="lark_bot_access_token",
            app_id="cli_example",
            app_secret_handle="lark_app_secret",
            token_transport=lambda request, timeout: _Response(b'{"code":999,"msg":"private provider detail"}'),
        )

        with self.assertRaisesRegex(
            CredentialResolutionError,
            "credential handle not found: lark_bot_access_token",
        ) as raised:
            provider.resolve("lark_bot_access_token")
        self.assertNotIn("private-app-secret", str(raised.exception))
        self.assertNotIn("private provider detail", str(raised.exception))

    def test_oversized_exchange_response_is_rejected_without_provider_detail(self):
        provider = LarkTenantAccessTokenCredentialProvider(
            StaticCredentialProvider({"lark_app_secret": "private-app-secret"}),
            handle="lark_bot_access_token",
            app_id="cli_example",
            app_secret_handle="lark_app_secret",
            token_transport=lambda request, timeout: _Response(b"x" * (64 * 1024 + 2)),
        )

        with self.assertRaisesRegex(
            CredentialResolutionError,
            "credential handle not found: lark_bot_access_token",
        ) as raised:
            provider.resolve("lark_bot_access_token")
        self.assertNotIn("private-app-secret", str(raised.exception))

    def test_rejects_unsafe_configuration_before_source_read(self):
        with self.assertRaisesRegex(ValueError, "must differ"):
            LarkTenantAccessTokenCredentialProvider(
                StaticCredentialProvider({"lark_app_secret": "private-app-secret"}),
                handle="lark_bot_access_token",
                app_id="cli_example",
                app_secret_handle="lark_bot_access_token",
            )
