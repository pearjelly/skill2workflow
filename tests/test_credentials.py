import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.credentials import (
    CredentialResolutionError,
    DirectoryCredentialProvider,
    MAX_DIRECTORY_CREDENTIAL_BYTES,
    StaticCredentialProvider,
    load_credential_file,
)


class CredentialTests(TestCase):
    def test_directory_provider_reads_each_value_at_resolution_time(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / "credentials"
            directory.mkdir()
            directory.chmod(0o700)
            token_path = directory / "demo_api_token"
            token_path.write_text("first-secret", encoding="utf-8")
            token_path.chmod(0o600)
            provider = DirectoryCredentialProvider(directory)

            first = provider.resolve("demo_api_token")
            token_path.write_text("rotated-secret", encoding="utf-8")
            second = provider.resolve("demo_api_token")

        self.assertEqual(first, "first-secret")
        self.assertEqual(second, "rotated-secret")

    def test_directory_provider_rejects_unsafe_missing_or_escaping_handles(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "credentials"
            directory.mkdir()
            directory.chmod(0o700)
            outside = root / "outside"
            outside.write_text("outside-secret", encoding="utf-8")
            (directory / "escape").symlink_to(outside)
            provider = DirectoryCredentialProvider(directory)

            for handle in ("../outside", "missing", "escape", "bad/name"):
                with self.subTest(handle=handle):
                    with self.assertRaises(CredentialResolutionError) as context:
                        provider.resolve(handle)
                    self.assertNotIn("outside-secret", str(context.exception))

    def test_directory_provider_rejects_unsafe_permissions_and_non_regular_values(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "credentials"
            directory.mkdir(mode=0o700)
            value = directory / "demo_api_token"
            value.write_text("private-value", encoding="utf-8")
            value.chmod(0o644)
            provider = DirectoryCredentialProvider(directory)

            with self.assertRaisesRegex(CredentialResolutionError, "not found"):
                provider.resolve("demo_api_token")

            value.chmod(0o600)
            directory.chmod(0o755)
            self.assertFalse(provider.is_ready())
            with self.assertRaisesRegex(ValueError, "private non-symlink"):
                DirectoryCredentialProvider(directory)
            with self.assertRaisesRegex(CredentialResolutionError, "not found"):
                provider.resolve("demo_api_token")

    def test_directory_provider_rejects_oversized_and_invalid_utf8_values(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / "credentials"
            directory.mkdir(mode=0o700)
            value = directory / "demo_api_token"
            value.write_bytes(b"x" * (MAX_DIRECTORY_CREDENTIAL_BYTES + 1))
            value.chmod(0o600)
            provider = DirectoryCredentialProvider(directory)

            with self.assertRaisesRegex(CredentialResolutionError, "not found"):
                provider.resolve("demo_api_token")

            value.write_bytes(b"\xff\xfe")
            value.chmod(0o600)
            with self.assertRaisesRegex(CredentialResolutionError, "not found"):
                provider.resolve("demo_api_token")

            value.write_text("\n", encoding="utf-8")
            value.chmod(0o600)
            with self.assertRaisesRegex(CredentialResolutionError, "not found"):
                provider.resolve("demo_api_token")

    def test_directory_provider_binds_read_to_the_inspected_file_identity(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / "credentials"
            directory.mkdir(mode=0o700)
            value = directory / "demo_api_token"
            replacement = directory / "replacement"
            value.write_text("first-private-value", encoding="utf-8")
            replacement.write_text("replacement-private-value", encoding="utf-8")
            value.chmod(0o600)
            replacement.chmod(0o600)
            provider = DirectoryCredentialProvider(directory)
            real_open = os.open
            replaced = False

            def replace_before_open(path, flags, *args, **kwargs):
                nonlocal replaced
                if Path(path) == value and not replaced:
                    replaced = True
                    replacement.replace(value)
                return real_open(path, flags, *args, **kwargs)

            with patch(
                "skill2workflow.credentials.os.open",
                side_effect=replace_before_open,
            ):
                with self.assertRaisesRegex(CredentialResolutionError, "not found"):
                    provider.resolve("demo_api_token")

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
