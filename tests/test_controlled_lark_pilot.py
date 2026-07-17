import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.controlled_lark_pilot import (
    initialize_pilot,
    load_pilot_charter,
    load_private_case,
)


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)


def _valid_charter():
    return {
        "schema_version": "controlled-lark-pilot-0.1.0",
        "scenario_id": "sales_renewal_risk_followup",
        "workflow_id": "workflow_controlled_lark_pilot",
        "workflow_version": "0.1.0",
        "support_model": "assisted",
        "timezone": "Asia/Shanghai",
        "starts_on": "2026-07-18",
        "expires_on": "2026-08-15",
        "team_consent_confirmed": True,
        "assignee_consent_confirmed": True,
        "commercial_engagement_confirmed": True,
        "required_approved_runs": 5,
        "required_distinct_days": 5,
        "required_distinct_cases": 2,
    }


class ControlledLarkPilotTests(TestCase):
    def test_initialize_pilot_creates_owner_only_private_workspace(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "controlled-pilot"
            result = initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

            self.assertEqual(result["status"], "initialized")
            self.assertEqual(result["workflow_id"], "workflow_controlled_lark_pilot")
            self.assertEqual(work_dir.stat().st_mode & 0o077, 0)
            self.assertEqual(
                (work_dir / "private" / "charter.json").stat().st_mode & 0o077,
                0,
            )
            self.assertTrue((work_dir / "state").is_dir())
            self.assertTrue((work_dir / "evidence").is_dir())

    def test_initialize_pilot_rejects_repository_work_dir(self):
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            initialize_pilot(ROOT, ROOT / ".pilot-private", _valid_charter(), now=NOW)

    def test_charter_requires_consent_commercial_status_thresholds_and_active_dates(self):
        invalid_values = [
            ("team_consent_confirmed", False),
            ("assignee_consent_confirmed", False),
            ("commercial_engagement_confirmed", False),
            ("required_approved_runs", 4),
            ("required_distinct_days", 4),
            ("required_distinct_cases", 1),
            ("timezone", "UTC"),
        ]
        for key, value in invalid_values:
            charter = _valid_charter()
            charter[key] = value
            with self.subTest(key=key), TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    initialize_pilot(ROOT, Path(tmp) / "pilot", charter, now=NOW)

    def test_charter_rejects_unknown_fields(self):
        charter = _valid_charter()
        charter["account_name"] = "must stay private"
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "only the approved fields"):
                initialize_pilot(ROOT, Path(tmp) / "pilot", charter, now=NOW)

    def test_load_pilot_charter_rejects_expired_charter(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            with self.assertRaisesRegex(ValueError, "expired"):
                load_pilot_charter(
                    work_dir,
                    now=datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc),
                )

    def test_load_private_case_requires_external_owner_only_exact_shape(self):
        payload = {
            "pilot_case_id": "case-001",
            "account_name": "Private Account",
            "renewal_risk": "Private Risk",
            "owner_open_id": "ou_private",
            "due_at": "2026-08-15T09:00:00Z",
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            os.chmod(path, 0o600)
            self.assertEqual(load_private_case(ROOT, path), payload)

            os.chmod(path, 0o644)
            with self.assertRaisesRegex(ValueError, "owner-only"):
                load_private_case(ROOT, path)
