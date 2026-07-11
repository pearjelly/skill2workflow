import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.credentials import CredentialResolutionError, StaticCredentialProvider, load_credential_file


class CredentialTests(TestCase):
    def test_static_provider_resolves_string_handles(self):
        provider = StaticCredentialProvider({"demo_api_token": "secret-token"})

        self.assertEqual(provider.resolve("demo_api_token"), "secret-token")

    def test_static_provider_rejects_missing_handles_without_secret_values(self):
        provider = StaticCredentialProvider({"demo_api_token": "secret-token"})

        with self.assertRaisesRegex(CredentialResolutionError, "credential handle not found: missing_token") as context:
            provider.resolve("missing_token")

        self.assertNotIn("secret-token", str(context.exception))

    def test_load_credential_file_reads_credentials_object(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "credentials.json"
            path.write_text(json.dumps({"credentials": {"demo_api_token": "secret-token"}}), encoding="utf-8")

            provider = load_credential_file(path)

        self.assertEqual(provider.resolve("demo_api_token"), "secret-token")

    def test_load_credential_file_rejects_invalid_credentials_shape(self):
        cases = [
            (["not", "an", "object"], "credential file must be a JSON object"),
            ({"credentials": ["bad"]}, "credentials must be an object"),
            ({"credentials": {"demo_api_token": 123}}, "credential values must be strings"),
            ({"credentials": {"": "secret-token"}}, "credential handles must be non-empty strings"),
        ]

        with TemporaryDirectory() as tmp:
            for index, (payload, pattern) in enumerate(cases):
                with self.subTest(payload=payload):
                    path = Path(tmp) / f"credentials-{index}.json"
                    path.write_text(json.dumps(payload), encoding="utf-8")

                    with self.assertRaisesRegex(ValueError, pattern):
                        load_credential_file(path)
