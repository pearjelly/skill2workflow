import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

from skill2workflow.secret_hygiene import scan_json_paths, scan_json_value


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
                    "value_preview": "Bearer sk-li...",
                }
            ],
        )

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
