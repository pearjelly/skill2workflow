import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

from skill2workflow.secret_hygiene import (
    MAX_JSON_BYTES,
    scan_json_paths,
    scan_json_value,
    scan_repository_paths,
)


ROOT = Path(__file__).resolve().parents[1]


class SecretHygieneTests(TestCase):
    def test_scan_json_value_flags_obvious_secret_headers(self):
        workflow = {
            "connector": {
                "request": {
                    "headers": {
                        "Authorization": "Bearer sk-live-secret-value",
                    }
                }
            }
        }

        findings = scan_json_value(workflow, source="workflow.json")

        self.assertEqual(
            findings,
            [
                {
                    "source": "workflow.json",
                    "path": "$.connector.request.headers.Authorization",
                    "reason": "secret-like key and value",
                    "value_preview": "<redacted>",
                }
            ],
        )

    def test_repository_scan_rejects_private_paths_and_unapproved_binary_locations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            safe_image = root / "docs" / "assets" / "public.jpg"
            safe_image.parent.mkdir(parents=True)
            safe_image.write_bytes(b"public")
            unsafe_link = root / "linked-public.jpg"
            unsafe_link.symlink_to(safe_image)
            unsafe_paths = (
                root / "customer-auth.png",
                root / "private" / "case.json",
                root / "credentials.json",
                root / "runtime.sqlite3",
                root / "operator-export.jsonl",
                root / "signing-key.pem",
            )
            for path in unsafe_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"private")

            findings = scan_repository_paths(
                root,
                [safe_image, unsafe_link, *unsafe_paths],
            )

        self.assertEqual(
            {Path(finding["source"]).name for finding in findings},
            {unsafe_link.name, *(path.name for path in unsafe_paths)},
        )
        self.assertTrue(
            all(finding["value_preview"] == "<not-read>" for finding in findings)
        )

    def test_repository_mode_respects_gitignore_and_rejects_unignored_root_media(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            subprocess.run(
                ["git", "init", "--quiet", str(root)],
                check=True,
                capture_output=True,
                text=True,
            )
            (root / ".gitignore").write_text("/*-auth.png\n", encoding="utf-8")
            (root / "ignored-auth.png").write_bytes(b"ignored")
            (root / "customer-export.png").write_bytes(b"unsafe")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "secret_hygiene.py"),
                    "--repository-root",
                    str(root),
                ],
                text=True,
                capture_output=True,
            )

        self.assertEqual(completed.returncode, 1)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["ok"], False)
        sources = [finding["source"] for finding in payload["findings"]]
        self.assertTrue(any(source.endswith("customer-export.png") for source in sources))
        self.assertFalse(any(source.endswith("ignored-auth.png") for source in sources))

    def test_scan_json_value_allows_documented_placeholders(self):
        workflow = {
            "connector": {
                "request": {
                    "url": "http://127.0.0.1:8080/example",
                    "headers": {
                        "Authorization": "Bearer <redacted>",
                        "X-API-Key": "example-token",
                    },
                    "body": {
                        "password": "placeholder",
                        "client_secret": "REDACTED",
                    },
                }
            }
        }

        findings = scan_json_value(workflow, source="workflow.json")

        self.assertEqual(findings, [])

    def test_json_path_scan_fails_closed_without_following_or_echoing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            valid = root / "valid.json"
            valid.write_text('{"value": "placeholder"}', encoding="utf-8")
            linked = root / "linked.json"
            linked.symlink_to(valid)
            oversized = root / "oversized.json"
            oversized.write_bytes(b" " * (MAX_JSON_BYTES + 1))
            invalid_utf8 = root / "invalid-utf8.json"
            invalid_utf8.write_bytes(b"{\"value\": \xff}")
            invalid_json = root / "invalid.json"
            invalid_json.write_text('{"value":', encoding="utf-8")
            missing = root / "missing.json"

            findings = scan_json_paths(
                [linked, oversized, invalid_utf8, invalid_json, missing]
            )

        by_name = {
            Path(finding["source"]).name: finding for finding in findings
        }
        self.assertEqual(
            {name: finding["reason"] for name, finding in by_name.items()},
            {
                "linked.json": "symbolic JSON path is not allowed",
                "oversized.json": "JSON file exceeds scan size limit",
                "invalid-utf8.json": "JSON file is not valid UTF-8",
                "invalid.json": "invalid JSON",
                "missing.json": "JSON file is unavailable",
            },
        )
        self.assertTrue(
            all(
                finding["value_preview"] in ("<redacted>", "<not-read>")
                for finding in findings
            )
        )

    def test_committed_workflow_examples_do_not_contain_obvious_secrets(self):
        workflow_paths = sorted((ROOT / "examples" / "workflows").glob("*.json"))

        findings = scan_json_paths(workflow_paths)

        self.assertEqual(findings, [])

    def test_secret_hygiene_script_exits_nonzero_for_secret_like_fixture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workflow_path = Path(temp_dir) / "unsafe.workflow.json"
            workflow_path.write_text(
                json.dumps(
                    {
                        "connector": {
                            "request": {
                                "headers": {
                                    "Authorization": "Bearer sk-live-secret-value",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "secret_hygiene.py"), str(workflow_path)],
                text=True,
                capture_output=True,
            )

        self.assertEqual(completed.returncode, 1)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["findings"][0]["path"], "$.connector.request.headers.Authorization")
        self.assertEqual(payload["findings"][0]["value_preview"], "<redacted>")
