import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from scripts.service_soak_smoke import (
    MAX_TOTAL_TRIGGERS,
    SOAK_EVIDENCE_SCHEMA_VERSION,
    WORK_DIR_MARKER,
    _reset_work_dir,
    _validate_options,
    _workflow,
    _write_evidence,
)


class ServiceSoakSmokeTests(TestCase):
    def test_options_are_bounded_and_total_work_is_capped(self):
        _validate_options(1, 1)
        _validate_options(8, 16)
        with self.assertRaises(ValueError):
            _validate_options(0, 1)
        with self.assertRaises(ValueError):
            _validate_options(1, 33)
        with self.assertRaises(ValueError):
            _validate_options(8, 17)
        self.assertEqual(MAX_TOTAL_TRIGGERS, 128)

    def test_workflow_fixture_is_minimal_and_stable(self):
        workflow = _workflow()
        self.assertEqual(workflow["schema_version"], "0.1.0")
        self.assertEqual(workflow["entry"], "start")
        self.assertEqual([node["id"] for node in workflow["nodes"]], ["start", "end"])
        self.assertEqual(workflow["edges"][0]["to"], "end")

    def test_evidence_writer_is_public_and_json_only(self):
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "nested" / "service-soak-smoke.json"
            evidence = {
                "schema_version": SOAK_EVIDENCE_SCHEMA_VERSION,
                "status": "passed",
                "checks": {"all_runs_completed": True},
            }
            _write_evidence(output, evidence)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), evidence)
            self.assertEqual(output.stat().st_mode & 0o777, 0o644)

    def test_work_dir_reset_refuses_repository_and_filesystem_root(self):
        with self.assertRaises(ValueError):
            _reset_work_dir(Path(__file__).resolve().parents[1])
        with self.assertRaises(ValueError):
            _reset_work_dir(Path(Path(__file__).anchor))

    def test_work_dir_reset_requires_a_dedicated_marker(self):
        with TemporaryDirectory() as temporary:
            work_dir = Path(temporary) / "existing"
            work_dir.mkdir()
            with self.assertRaises(ValueError):
                _reset_work_dir(work_dir)
            (work_dir / WORK_DIR_MARKER).write_text(
                "skill2workflow service soak work directory\n", encoding="utf-8"
            )
            _reset_work_dir(work_dir)
            self.assertFalse(work_dir.exists())
