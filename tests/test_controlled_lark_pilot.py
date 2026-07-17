import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.controlled_lark_pilot import (
    initialize_pilot,
    load_pilot_charter,
    load_private_case,
    start_pilot_run,
)
from skill2workflow.credentials import StaticCredentialProvider


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


def _valid_case():
    return {
        "pilot_case_id": "case-001",
        "account_name": "Private Account",
        "renewal_risk": "Private Risk",
        "owner_open_id": "ou_private",
        "due_at": "2026-08-15T09:00:00Z",
    }


def _write_private_case(path: Path, case_id: str = "case-001") -> None:
    path.write_text(
        json.dumps(
            {
                "pilot_case_id": case_id,
                "account_name": "Private Account",
                "renewal_risk": "Private Risk",
                "owner_open_id": "ou_private",
                "due_at": "2026-08-15T09:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def _start_waiting_pilot(tmp: str, case_id: str = "case-001"):
    root = Path(tmp)
    work_dir = root / "pilot"
    input_path = root / "case.json"
    initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
    _write_private_case(input_path, case_id=case_id)
    started = start_pilot_run(ROOT, work_dir, input_path, now=NOW)
    return work_dir, started


class ControlledLarkPilotTests(TestCase):
    def test_start_pilot_run_publishes_live_workflow_and_stops_at_gate(self):
        with TemporaryDirectory() as tmp:
            work_dir, result = _start_waiting_pilot(tmp)
            control = LocalControlPlane(work_dir / "state", storage="sqlite")
            run = control.get_run(result["run_id"])
            workflow = control.get_workflow(
                "workflow_controlled_lark_pilot",
                "0.1.0",
            )
            node = next(
                item for item in workflow["nodes"] if item["id"] == "create_lark_task"
            )
            non_sqlite_state = b"".join(
                path.read_bytes()
                for path in (work_dir / "state").rglob("*")
                if path.is_file() and path.suffix != ".sqlite3"
            )
            runs_sqlite_exists = (work_dir / "state" / "runs.sqlite3").is_file()
            runs_dir_exists = (work_dir / "state" / "runs").exists()

        self.assertEqual(
            set(result),
            {
                "current_node",
                "input_keys",
                "run_id",
                "run_status",
                "workflow_id",
                "workflow_version",
            },
        )
        self.assertEqual(result["run_status"], "waiting")
        self.assertEqual(result["current_node"], "review_renewal_risk")
        self.assertEqual(
            result["input_keys"],
            [
                "account_name",
                "due_at",
                "owner_open_id",
                "pilot_case_id",
                "renewal_risk",
            ],
        )
        self.assertEqual(run["status"], "waiting")
        self.assertEqual(run["context"]["input"], _valid_case())
        self.assertTrue(runs_sqlite_exists)
        self.assertFalse(runs_dir_exists)
        self.assertEqual(node["connector"]["mode"], "live")
        self.assertNotIn("Private Account", json.dumps(result))
        self.assertNotIn(b"Private Account", non_sqlite_state)

    def test_start_pilot_run_does_not_resolve_credentials_or_call_transport(self):
        transport_calls = []

        def forbidden_transport(*args, **kwargs):
            transport_calls.append((args, kwargs))
            raise AssertionError("start must not call live transport")

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            work_dir = root / "pilot"
            input_path = root / "case.json"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            _write_private_case(input_path)
            with patch.dict(
                os.environ,
                {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"},
            ), patch.object(
                StaticCredentialProvider,
                "resolve",
                side_effect=AssertionError("start must not resolve credentials"),
            ) as resolve_credential:
                result = start_pilot_run(
                    ROOT,
                    work_dir,
                    input_path,
                    now=NOW,
                    transport=forbidden_transport,
                )

        self.assertEqual(result["run_status"], "waiting")
        resolve_credential.assert_not_called()
        self.assertEqual(transport_calls, [])

    def test_start_pilot_run_rechecks_external_work_dir_before_creating_state(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "repo"
            work_dir = repo_root / "forged-pilot"
            private_dir = work_dir / "private"
            private_dir.mkdir(parents=True)
            (private_dir / "charter.json").write_text(
                json.dumps(_valid_charter()),
                encoding="utf-8",
            )
            input_path = root / "case.json"
            _write_private_case(input_path)

            with self.assertRaisesRegex(ValueError, "outside the repository"):
                start_pilot_run(repo_root, work_dir, input_path, now=NOW)

            self.assertFalse((work_dir / "state").exists())

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

    def test_initialize_pilot_rejects_private_subdirectory_symlinks(self):
        for child_name in ("private", "state", "evidence"):
            with self.subTest(child_name=child_name), TemporaryDirectory() as tmp:
                work_dir = Path(tmp) / "pilot"
                work_dir.mkdir()
                target = Path(tmp) / "symlink-target"
                target.mkdir()
                os.chmod(target, 0o755)
                (work_dir / child_name).symlink_to(
                    target,
                    target_is_directory=True,
                )

                with self.assertRaisesRegex(ValueError, "symbolic link"):
                    initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

                self.assertEqual(target.stat().st_mode & 0o777, 0o755)
                self.assertEqual(list(target.iterdir()), [])

    def test_initialize_pilot_rejects_charter_symlink_without_changing_target(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            private_dir = work_dir / "private"
            private_dir.mkdir(parents=True)
            target = Path(tmp) / "charter-target.json"
            target.write_text("sentinel", encoding="utf-8")
            os.chmod(target, 0o640)
            (private_dir / "charter.json").symlink_to(target)

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)

    def test_initialize_pilot_rejects_non_directory_workspace_nodes(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            work_dir.mkdir()
            state_path = work_dir / "state"
            state_path.write_text("sentinel", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "directory"):
                initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

            self.assertEqual(state_path.read_text(encoding="utf-8"), "sentinel")

    def test_initialize_pilot_uses_private_temp_and_cleans_up_replace_failure(self):
        observed = {}

        def fail_replace(source, destination):
            observed["mode"] = Path(source).stat().st_mode & 0o777
            observed["destination"] = Path(destination).name
            raise OSError("replace failed")

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            with patch(
                "skill2workflow.controlled_lark_pilot.os.replace",
                side_effect=fail_replace,
            ):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

            self.assertEqual(
                observed,
                {"mode": 0o600, "destination": "charter.json"},
            )
            self.assertEqual(list((work_dir / "private").iterdir()), [])

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
        payload = _valid_case()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            os.chmod(path, 0o600)
            self.assertEqual(load_private_case(ROOT, path), payload)

            os.chmod(path, 0o644)
            with self.assertRaisesRegex(ValueError, "owner-only"):
                load_private_case(ROOT, path)

    def test_load_private_case_rejects_extra_fields(self):
        payload = _valid_case()
        payload["lark_token"] = "must-not-enter-case"
        self._assert_private_case_rejected(payload, "only the approved fields")

    def test_load_private_case_rejects_missing_fields(self):
        for key in _valid_case():
            payload = _valid_case()
            del payload[key]
            with self.subTest(key=key):
                self._assert_private_case_rejected(
                    payload,
                    "only the approved fields",
                )

    def test_load_private_case_rejects_empty_fields(self):
        for key in _valid_case():
            payload = _valid_case()
            payload[key] = " "
            with self.subTest(key=key):
                self._assert_private_case_rejected(payload, "non-empty strings")

    def test_load_private_case_rejects_non_opaque_case_ids(self):
        for pilot_case_id in (
            "account-001",
            "customer-001",
            "owner@example.com",
            "case 001",
        ):
            payload = _valid_case()
            payload["pilot_case_id"] = pilot_case_id
            with self.subTest(pilot_case_id=pilot_case_id):
                self._assert_private_case_rejected(payload, "opaque identifier")

    def _assert_private_case_rejected(self, payload, message):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            os.chmod(path, 0o600)
            with self.assertRaisesRegex(ValueError, message):
                load_private_case(ROOT, path)
